import os
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.db import transaction
from accounts.permissions import IsUniversityScopedAccess
from courses.models import Course, Subject
from .models import Document, DocumentChunk
from .utils import extract_text_from_file, chunk_text
from ai_engine.rag import add_document_to_rag, delete_document_from_rag


def get_university_id(user):
    profile = getattr(user, "profile", None)
    if profile and profile.university:
        return profile.university.id
    return None


def get_university(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "university", None)


def _parse_optional_int(raw_value, field_name):
    if raw_value in (None, ""):
        return None, None
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be an integer"
    if parsed <= 0:
        return None, f"{field_name} must be a positive integer"
    return parsed, None


def _visible_documents_queryset(user):
    profile = getattr(user, "profile", None)
    if profile and profile.role == "professor":
        return Document.objects.filter(uploaded_by=user).order_by("-created_at")
    if profile and profile.university:
        return Document.objects.filter(
            uploaded_by__profile__university=profile.university
        ).order_by("-created_at")
    return Document.objects.filter(uploaded_by=user).order_by("-created_at")


def _is_admin_context(user):
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", "")
    return role == "admin" or user.is_staff or user.is_superuser


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def upload_document(request):
    """Professor uploads doc → stored in university RAG collection"""
    if "file" not in request.FILES:
        return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

    file = request.FILES["file"]
    title = request.data.get("title", file.name)
    description = request.data.get("description", "")
    tags = request.data.get("tags", "")
    raw_course_id = request.data.get("course_id")
    raw_subject_id = request.data.get("subject_id")
    knowledge_base = request.data.get("knowledge_base", "academic")
    visibility = request.data.get("visibility", "private")
    university = get_university(request.user)
    if not university:
        return Response(
            {"error": "You must be affiliated with a university to upload documents"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    valid_knowledge_bases = {choice[0] for choice in Document.KNOWLEDGE_BASE_CHOICES}
    if knowledge_base not in valid_knowledge_bases:
        return Response(
            {"error": f"knowledge_base must be one of: {', '.join(sorted(valid_knowledge_bases))}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    valid_visibility = {choice[0] for choice in Document.VISIBILITY_CHOICES}
    if visibility not in valid_visibility:
        return Response(
            {"error": f"visibility must be one of: {', '.join(sorted(valid_visibility))}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
        return Response({"error": f"File type {ext} not allowed"}, status=status.HTTP_400_BAD_REQUEST)

    if file.size > settings.MAX_UPLOAD_SIZE:
        return Response({"error": "File too large. Max 10MB"}, status=status.HTTP_400_BAD_REQUEST)

    course_id, course_error = _parse_optional_int(raw_course_id, "course_id")
    if course_error:
        return Response({"error": course_error}, status=status.HTTP_400_BAD_REQUEST)
    subject_id, subject_error = _parse_optional_int(raw_subject_id, "subject_id")
    if subject_error:
        return Response({"error": subject_error}, status=status.HTTP_400_BAD_REQUEST)

    if knowledge_base == "university_info" and (course_id or subject_id):
        return Response(
            {"error": "course_id and subject_id are only supported for academic documents"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    course = None
    if course_id:
        course = Course.objects.filter(id=course_id, university=university).first()
        if not course:
            return Response(
                {"error": "course_id is invalid for your university"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    subject = None
    if subject_id:
        subject = Subject.objects.select_related("course").filter(id=subject_id).first()
        if not subject or subject.course.university_id != university.id:
            return Response(
                {"error": "subject_id is invalid for your university"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if course and subject.course_id != course.id:
            return Response(
                {"error": "subject_id does not belong to the provided course_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if course is None:
            course = subject.course
            course_id = course.id

    doc = Document.objects.create(
        uploaded_by=request.user,
        course=course,
        subject=subject,
        title=title,
        description=description,
        tags=tags,
        knowledge_base=knowledge_base,
        visibility=visibility,
        file=file,
        file_type=ext.replace(".", ""),
        file_size=file.size,
        status="processing",
    )

    try:
        extracted_text = extract_text_from_file(doc.file.path)
        if not extracted_text.strip():
            raise ValueError(
                "Could not extract text from document. "
                "Use a text-based PDF/DOCX/TXT/PPTX file (not scanned images)."
            )

        chunks = chunk_text(extracted_text)
        if not chunks:
            raise ValueError("Could not split extracted text into chunks for indexing.")

        doc.extracted_text = extracted_text
        doc.page_count = len(chunks)
        doc.save(update_fields=["extracted_text", "page_count", "updated_at"])

        chunk_objects = [
            DocumentChunk(
                document=doc,
                content=chunk,
                chunk_index=i,
            )
            for i, chunk in enumerate(chunks)
        ]
        with transaction.atomic():
            DocumentChunk.objects.bulk_create(chunk_objects)

        # Store in RAG (university-isolated)
        university_id = university.id
        rag_chunks = 0
        try:
            rag_chunks = add_document_to_rag(
                doc,
                chunk_objects,
                university_id,
                course_id=course_id,
                knowledge_base=knowledge_base,
                visibility=visibility,
            )
        except Exception:
            # Best-effort cleanup for partial RAG writes and chunk records.
            delete_document_from_rag(
                doc.id,
                university_id,
                course_id=course_id,
                knowledge_base=knowledge_base,
            )
            DocumentChunk.objects.filter(document=doc).delete()
            raise

        doc.status = "completed"
        doc.is_processed = True
        doc.save(update_fields=["status", "is_processed", "updated_at"])

        return Response({
            "id": doc.id,
            "title": doc.title,
            "status": doc.status,
            "file_type": doc.file_type,
            "course_id": doc.course_id,
            "subject_id": doc.subject_id,
            "knowledge_base": doc.knowledge_base,
            "visibility": doc.visibility,
            "page_count": doc.page_count,
            "chunks_created": len(chunks),
            "rag_indexed": rag_chunks,
            "university_isolated": university_id is not None,
            "message": "Document uploaded and indexed in university RAG!"
        }, status=status.HTTP_201_CREATED)

    except ValueError as e:
        doc.status = "failed"
        doc.is_processed = False
        doc.page_count = 0
        doc.save(update_fields=["status", "is_processed", "page_count", "updated_at"])
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        doc.status = "failed"
        doc.is_processed = False
        doc.page_count = 0
        doc.save(update_fields=["status", "is_processed", "page_count", "updated_at"])
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def list_documents(request):
    """List documents - professors see their uploads, students see university docs"""
    documents = _visible_documents_queryset(request.user)

    data = [{
        "id": doc.id,
        "title": doc.title,
        "description": doc.description,
        "tags": doc.tags,
        "file_type": doc.file_type,
        "course_id": doc.course_id,
        "subject_id": doc.subject_id,
        "knowledge_base": doc.knowledge_base,
        "visibility": doc.visibility,
        "status": doc.status,
        "is_processed": doc.is_processed,
        "page_count": doc.page_count,
        "uploaded_by": doc.uploaded_by.username,
        "created_at": doc.created_at,
    } for doc in documents]
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def document_detail(request, doc_id):
    doc = _visible_documents_queryset(request.user).filter(id=doc_id).first()
    if not doc:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "id": doc.id,
        "title": doc.title,
        "description": doc.description,
        "tags": doc.tags,
        "file_type": doc.file_type,
        "course_id": doc.course_id,
        "subject_id": doc.subject_id,
        "knowledge_base": doc.knowledge_base,
        "visibility": doc.visibility,
        "status": doc.status,
        "is_processed": doc.is_processed,
        "page_count": doc.page_count,
        "text_length": len(doc.extracted_text),
        "chunks": doc.chunks.count(),
        "uploaded_by": doc.uploaded_by.username,
        "created_at": doc.created_at,
    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def delete_document(request, doc_id):
    if _is_admin_context(request.user):
        doc = _visible_documents_queryset(request.user).filter(id=doc_id).first()
    else:
        doc = Document.objects.filter(id=doc_id, uploaded_by=request.user).first()

    if not doc:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

    university_id = get_university_id(doc.uploaded_by)
    if university_id:
        delete_document_from_rag(
            doc.id,
            university_id,
            course_id=doc.course_id,
            knowledge_base=doc.knowledge_base,
        )
    doc.file.delete()
    doc.delete()
    return Response({"message": "Document deleted from system and RAG"})

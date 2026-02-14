import os
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from .models import Document, DocumentChunk
from .utils import extract_text_from_file, chunk_text
from ai_engine.rag import add_document_to_rag, delete_document_from_rag


def get_university_id(user):
    profile = getattr(user, "profile", None)
    if profile and profile.university:
        return profile.university.id
    return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_document(request):
    """Professor uploads doc → stored in university RAG collection"""
    if "file" not in request.FILES:
        return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

    file = request.FILES["file"]
    title = request.data.get("title", file.name)
    course_id = request.data.get("course_id")

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in settings.ALLOWED_DOCUMENT_EXTENSIONS:
        return Response({"error": f"File type {ext} not allowed"}, status=status.HTTP_400_BAD_REQUEST)

    if file.size > settings.MAX_UPLOAD_SIZE:
        return Response({"error": "File too large. Max 10MB"}, status=status.HTTP_400_BAD_REQUEST)

    doc = Document.objects.create(
        uploaded_by=request.user,
        title=title,
        file=file,
        file_type=ext.replace(".", ""),
        file_size=file.size,
        status="processing",
    )

    try:
        extracted_text = extract_text_from_file(doc.file.path)
        doc.extracted_text = extracted_text
        doc.status = "completed"
        doc.is_processed = True
        doc.save()

        chunks = chunk_text(extracted_text)
        chunk_objects = []
        for i, chunk in enumerate(chunks):
            chunk_obj = DocumentChunk.objects.create(
                document=doc,
                content=chunk,
                chunk_index=i,
            )
            chunk_objects.append(chunk_obj)

        # Store in RAG (university-isolated)
        university_id = get_university_id(request.user)
        rag_chunks = 0
        if university_id:
            rag_chunks = add_document_to_rag(doc, chunk_objects, university_id, course_id)

        return Response({
            "id": doc.id,
            "title": doc.title,
            "status": doc.status,
            "file_type": doc.file_type,
            "chunks_created": len(chunks),
            "rag_indexed": rag_chunks,
            "university_isolated": university_id is not None,
            "message": "Document uploaded and indexed in university RAG!"
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        doc.status = "failed"
        doc.save()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_documents(request):
    """List documents - professors see their uploads, students see university docs"""
    profile = getattr(request.user, "profile", None)
    if profile and profile.role == "professor":
        documents = Document.objects.filter(uploaded_by=request.user).order_by("-created_at")
    else:
        if profile and profile.university:
            documents = Document.objects.filter(
                uploaded_by__profile__university=profile.university
            ).order_by("-created_at")
        else:
            documents = Document.objects.filter(uploaded_by=request.user).order_by("-created_at")

    data = [{
        "id": doc.id,
        "title": doc.title,
        "file_type": doc.file_type,
        "status": doc.status,
        "is_processed": doc.is_processed,
        "uploaded_by": doc.uploaded_by.username,
        "created_at": doc.created_at,
    } for doc in documents]
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def document_detail(request, doc_id):
    try:
        doc = Document.objects.get(id=doc_id)
        return Response({
            "id": doc.id,
            "title": doc.title,
            "file_type": doc.file_type,
            "status": doc.status,
            "is_processed": doc.is_processed,
            "text_length": len(doc.extracted_text),
            "chunks": doc.chunks.count(),
            "uploaded_by": doc.uploaded_by.username,
            "created_at": doc.created_at,
        })
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_document(request, doc_id):
    try:
        doc = Document.objects.get(id=doc_id, uploaded_by=request.user)
        university_id = get_university_id(request.user)
        if university_id:
            delete_document_from_rag(doc.id, university_id)
        doc.file.delete()
        doc.delete()
        return Response({"message": "Document deleted from system and RAG"})
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

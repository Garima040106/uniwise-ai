import os
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from .models import Document, DocumentChunk
from .utils import extract_text_from_file, chunk_text


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_document(request):
    """Upload and process a document"""
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
        file_path = doc.file.path
        extracted_text = extract_text_from_file(file_path)
        doc.extracted_text = extracted_text
        doc.status = "completed"
        doc.is_processed = True
        doc.save()

        chunks = chunk_text(extracted_text)
        for i, chunk in enumerate(chunks):
            DocumentChunk.objects.create(
                document=doc,
                content=chunk,
                chunk_index=i,
            )

        return Response({
            "id": doc.id,
            "title": doc.title,
            "status": doc.status,
            "file_type": doc.file_type,
            "chunks_created": len(chunks),
            "text_length": len(extracted_text),
            "message": "Document uploaded and processed successfully!"
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        doc.status = "failed"
        doc.save()
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_documents(request):
    """List all documents for current user"""
    documents = Document.objects.filter(uploaded_by=request.user).order_by("-created_at")
    data = [{
        "id": doc.id,
        "title": doc.title,
        "file_type": doc.file_type,
        "status": doc.status,
        "is_processed": doc.is_processed,
        "created_at": doc.created_at,
    } for doc in documents]
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def document_detail(request, doc_id):
    """Get document details"""
    try:
        doc = Document.objects.get(id=doc_id, uploaded_by=request.user)
        return Response({
            "id": doc.id,
            "title": doc.title,
            "file_type": doc.file_type,
            "status": doc.status,
            "is_processed": doc.is_processed,
            "text_length": len(doc.extracted_text),
            "chunks": doc.chunks.count(),
            "created_at": doc.created_at,
        })
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_document(request, doc_id):
    """Delete a document"""
    try:
        doc = Document.objects.get(id=doc_id, uploaded_by=request.user)
        doc.file.delete()
        doc.delete()
        return Response({"message": "Document deleted successfully"})
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
# Create your views here.

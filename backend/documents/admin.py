from django.contrib import admin
from .models import Document, DocumentChunk

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "uploaded_by",
        "file_type",
        "knowledge_base",
        "visibility",
        "status",
        "is_processed",
        "created_at",
    ]
    search_fields = ["title", "description", "tags", "uploaded_by__username"]
    list_filter = ["status", "file_type", "knowledge_base", "visibility", "is_processed"]

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ["document", "chunk_index", "created_at"]
    search_fields = ["document__title"]
# Register your models here.

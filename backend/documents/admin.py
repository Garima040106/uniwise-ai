from django.contrib import admin
from .models import Document, DocumentChunk

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["title", "uploaded_by", "file_type", "status", "is_processed", "created_at"]
    search_fields = ["title"]
    list_filter = ["status", "file_type", "is_processed"]

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ["document", "chunk_index", "created_at"]
    search_fields = ["document__title"]
# Register your models here.

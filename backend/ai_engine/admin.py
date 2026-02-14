from django.contrib import admin
from .models import AIRequest, ExamPrepSlide, ConceptFact

@admin.register(AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    list_display = ["request_type", "requested_by", "status", "model_used", "processing_time_seconds", "created_at"]
    search_fields = ["requested_by__username"]
    list_filter = ["request_type", "status"]

@admin.register(ExamPrepSlide)
class ExamPrepSlideAdmin(admin.ModelAdmin):
    list_display = ["title", "document", "slide_order", "created_at"]
    search_fields = ["title"]

@admin.register(ConceptFact)
class ConceptFactAdmin(admin.ModelAdmin):
    list_display = ["concept", "document", "source_page", "created_at"]
    search_fields = ["concept", "fact"]
# Register your models here.

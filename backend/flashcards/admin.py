from django.contrib import admin
from .models import Flashcard, FlashcardReview

@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ["question", "difficulty", "is_ai_generated", "created_by", "created_at"]
    search_fields = ["question", "answer"]
    list_filter = ["difficulty", "is_ai_generated"]

@admin.register(FlashcardReview)
class FlashcardReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "flashcard", "rating", "next_review_date", "review_count"]
    list_filter = ["rating"]
# Register your models here.

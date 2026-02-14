from django.contrib import admin
from .models import Quiz, Question, QuizAttempt, QuestionResponse

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["title", "difficulty", "created_by", "time_limit_minutes", "created_at"]
    search_fields = ["title"]
    list_filter = ["difficulty", "is_ai_generated"]

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["question_text", "quiz", "question_type", "marks"]
    search_fields = ["question_text"]
    list_filter = ["question_type"]

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ["user", "quiz", "score", "percentage", "completed", "started_at"]
    list_filter = ["completed"]

@admin.register(QuestionResponse)
class QuestionResponseAdmin(admin.ModelAdmin):
    list_display = ["attempt", "question", "user_answer", "is_correct", "marks_awarded"]
    list_filter = ["is_correct"]
# Register your models here.

from django.contrib import admin
from .models import LearningProgress, StudySession, SkillSnapshot

@admin.register(LearningProgress)
class LearningProgressAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "skill_level", "quizzes_completed", "study_streak_days"]
    search_fields = ["user__username", "course__name"]

@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "duration_minutes", "flashcards_reviewed", "started_at"]
    list_filter = ["course"]

@admin.register(SkillSnapshot)
class SkillSnapshotAdmin(admin.ModelAdmin):
    list_display = ["user", "course", "skill_level", "recorded_at"]
    list_filter = ["course"]
# Register your models here.

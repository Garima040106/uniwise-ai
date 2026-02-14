from django.db import models
from django.contrib.auth.models import User
from courses.models import Course, Subject


class LearningProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progress")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="progress")
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    skill_level = models.FloatField(default=0.0)
    flashcards_completed = models.IntegerField(default=0)
    quizzes_completed = models.IntegerField(default=0)
    average_quiz_score = models.FloatField(default=0.0)
    study_streak_days = models.IntegerField(default=0)
    total_study_minutes = models.IntegerField(default=0)
    last_studied = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.course.name} - {self.skill_level}%"

    class Meta:
        unique_together = ["user", "course", "subject"]


class StudySession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="study_sessions")
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    duration_minutes = models.IntegerField(default=0)
    flashcards_reviewed = models.IntegerField(default=0)
    quizzes_taken = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.duration_minutes} mins"

    class Meta:
        ordering = ["-started_at"]


class SkillSnapshot(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_snapshots")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    skill_level = models.FloatField(default=0.0)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.skill_level}% on {self.recorded_at.date()}"

    class Meta:
        ordering = ["recorded_at"]
# Create your models here.

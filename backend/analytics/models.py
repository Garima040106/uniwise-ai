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


class CognitiveLoadSnapshot(models.Model):
    """Tracks a student's cognitive load at a point in time."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cognitive_load_snapshots")
    cognitive_load = models.FloatField(
        help_text="Cognitive load score from 0.0 to 1.0",
    )
    time_of_day = models.IntegerField(
        help_text="Hour of day (0-23)",
    )
    day_of_week = models.IntegerField(
        help_text="Day of week (0=Monday, 6=Sunday)",
    )
    session_duration_minutes = models.IntegerField(
        help_text="Duration of current study session in minutes",
    )
    recent_quiz_avg = models.FloatField(
        null=True,
        blank=True,
        help_text="Average score from recent quizzes",
    )
    frustration_score = models.FloatField(
        help_text="Frustration level score",
    )
    recommended_mode = models.CharField(
        max_length=50,
        help_text="Recommended learning mode based on cognitive load",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - Load: {self.cognitive_load:.2f} at {self.created_at}"

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["time_of_day"]),
            models.Index(fields=["day_of_week"]),
        ]


class BreakSession(models.Model):
    """Tracks break sessions and their impact on cognitive load."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="break_sessions")
    duration_minutes = models.IntegerField(
        help_text="Duration of the break in minutes",
    )
    started_at = models.DateTimeField(
        help_text="When the break started",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the break ended",
    )
    break_type = models.CharField(
        max_length=50,
        help_text="Type of break (e.g., walk, snack, meditation)",
    )
    cognitive_load_before = models.FloatField(
        help_text="Cognitive load before the break",
    )
    cognitive_load_after = models.FloatField(
        null=True,
        blank=True,
        help_text="Cognitive load after the break",
    )

    def __str__(self):
        return f"{self.user.username} - {self.break_type} break on {self.started_at.date()}"

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["user", "-started_at"]),
            models.Index(fields=["break_type"]),
        ]

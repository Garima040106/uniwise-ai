from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import hashlib
import uuid


class University(models.Model):
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    erp_system = models.CharField(max_length=100, blank=True)
    erp_integration_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Universities"


class UserProfile(models.Model):
    YEAR_CHOICES = [(i, f"Year {i}") for i in range(1, 6)]
    PACE_CHOICES = [
        ("slow", "Slow"),
        ("medium", "Medium"),
        ("fast", "Fast"),
    ]
    ROLE_CHOICES = [
        ("student", "Student"),
        ("professor", "Professor"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    student_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    year_of_study = models.IntegerField(choices=YEAR_CHOICES, default=1)
    field_of_study = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    learning_pace = models.CharField(max_length=20, choices=PACE_CHOICES, default="medium")
    two_factor_enabled = models.BooleanField(default=False)
    sso_provider = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def is_professor(self):
        return self.role == "professor"

    def is_student(self):
        return self.role == "student"


class LoginTwoFactorChallenge(models.Model):
    PURPOSE_CHOICES = [
        ("login", "Login"),
    ]

    challenge_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="two_factor_challenges")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default="login")
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user.username} {self.purpose} challenge {self.challenge_id}"

    @staticmethod
    def hash_code(raw_code: str) -> str:
        return hashlib.sha256(raw_code.encode("utf-8")).hexdigest()

    def set_code(self, raw_code: str):
        self.code_hash = self.hash_code(raw_code)

    def matches_code(self, raw_code: str) -> bool:
        return self.code_hash == self.hash_code(raw_code)

    def is_active(self) -> bool:
        return self.consumed_at is None and timezone.now() < self.expires_at

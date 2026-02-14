from django.db import models
from django.contrib.auth.models import User


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
    year_of_study = models.IntegerField(choices=YEAR_CHOICES, default=1)
    field_of_study = models.CharField(max_length=255, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profiles/", blank=True, null=True)
    learning_pace = models.CharField(max_length=20, choices=PACE_CHOICES, default="medium")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def is_professor(self):
        return self.role == "professor"

    def is_student(self):
        return self.role == "student"

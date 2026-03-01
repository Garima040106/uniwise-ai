from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import hashlib
import uuid


class University(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    country = models.CharField(max_length=100)
    subdomain = models.CharField(max_length=100, unique=True, blank=True, null=True)
    custom_domain = models.CharField(max_length=255, unique=True, blank=True, null=True)
    branding_primary_color = models.CharField(max_length=20, default="#2563eb")
    branding_secondary_color = models.CharField(max_length=20, default="#14b8a6")
    logo_url = models.URLField(blank=True)
    db_alias = models.CharField(max_length=64, blank=True)
    erp_system = models.CharField(max_length=100, blank=True)
    erp_integration_url = models.URLField(blank=True)
    allow_public_university_info = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
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


class UniversityIntegration(models.Model):
    CATEGORY_CHOICES = [
        ("widget", "Website Widget"),
        ("lms", "LMS"),
        ("erp", "ERP"),
        ("calendar", "Calendar"),
        ("sso", "SSO"),
        ("api", "API Integration"),
    ]
    STATUS_CHOICES = [
        ("scaffold", "Scaffold"),
        ("active", "Active"),
        ("disabled", "Disabled"),
    ]

    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="integrations")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    provider_name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scaffold")
    base_url = models.URLField(blank=True)
    config = models.JSONField(default=dict, blank=True)
    api_key_hash = models.CharField(max_length=128, blank=True)
    api_key_last4 = models.CharField(max_length=4, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("university", "category", "provider_name")
        ordering = ("category", "provider_name")

    def __str__(self):
        return f"{self.university.name} - {self.category} - {self.provider_name}"


class AuditLog(models.Model):
    EVENT_CHOICES = [
        ("auth", "Auth"),
        ("data_access", "Data Access"),
        ("data_change", "Data Change"),
        ("integration", "Integration"),
        ("security", "Security"),
        ("system", "System"),
    ]

    request_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES, default="system")
    action = models.CharField(max_length=120)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    status_code = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    duration_ms = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        username = self.user.username if self.user else "anonymous"
        return f"{self.action} ({self.method} {self.path}) by {username}"

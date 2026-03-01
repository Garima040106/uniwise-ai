from django.contrib import admin
from .models import AuditLog, LoginTwoFactorChallenge, University, UniversityIntegration, UserProfile

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "country",
        "subdomain",
        "custom_domain",
        "erp_system",
        "allow_public_university_info",
        "is_active",
        "created_at",
    ]
    search_fields = ["name", "country", "subdomain", "custom_domain", "slug"]
    list_filter = ["country", "allow_public_university_info", "is_active"]

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "student_id",
        "role",
        "university",
        "year_of_study",
        "learning_pace",
        "two_factor_enabled",
        "sso_provider",
    ]
    search_fields = ["user__username", "student_id", "university__name"]
    list_filter = ["role", "learning_pace", "year_of_study", "two_factor_enabled"]


@admin.register(LoginTwoFactorChallenge)
class LoginTwoFactorChallengeAdmin(admin.ModelAdmin):
    list_display = ["challenge_id", "user", "purpose", "attempts", "expires_at", "consumed_at", "created_at"]
    search_fields = ["user__username", "challenge_id"]
    list_filter = ["purpose", "created_at", "expires_at", "consumed_at"]


@admin.register(UniversityIntegration)
class UniversityIntegrationAdmin(admin.ModelAdmin):
    list_display = ["university", "category", "provider_name", "status", "updated_at"]
    list_filter = ["category", "status", "university"]
    search_fields = ["university__name", "provider_name", "base_url"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "event_type", "action", "user", "method", "path", "status_code", "duration_ms"]
    list_filter = ["event_type", "method", "status_code", "created_at"]
    search_fields = ["action", "user__username", "path", "request_id"]

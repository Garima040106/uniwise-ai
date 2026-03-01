import os
import secrets
import hashlib
from datetime import timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AuditLog, LoginTwoFactorChallenge, University, UniversityIntegration, UserProfile
from .permissions import IsProfessorOrAdmin, IsUniversityScopedAccess

PASSWORD_RESET_TOKEN_GENERATOR = PasswordResetTokenGenerator()


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _allowed_sso_providers():
    raw = os.getenv("SSO_PROVIDERS", "google,university-sso")
    providers = [item.strip() for item in raw.split(",") if item.strip()]
    return providers or ["google", "university-sso"]


def _sso_provider_label(provider_id):
    labels = {
        "google": "Google",
        "microsoft": "Microsoft",
        "university-sso": "University SSO",
    }
    return labels.get(provider_id, provider_id.replace("-", " ").title())


def _build_google_auth_url(request, state):
    callback_url = request.build_absolute_uri("/api/accounts/sso/callback/")
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
    if not client_id:
        return f"{callback_url}?provider=google&state={state}&code=sample-code", False

    params = {
        "client_id": client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}", True


def _ensure_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    needs_save = False
    if not profile.student_id:
        profile.student_id = user.username
        needs_save = True
    if needs_save:
        profile.save()
    return profile


def _auth_payload(user, profile, request):
    return {
        "message": "Login successful!",
        "user_id": user.id,
        "username": user.username,
        "student_id": profile.student_id,
        "email": user.email,
        "university": profile.university.name if profile.university else None,
        "role": profile.role,
        "two_factor_enabled": profile.two_factor_enabled,
        "csrfToken": get_token(request),
    }


def _is_role_allowed(user, profile, required_role):
    if required_role == "admin":
        return profile.role in {"admin", "professor"} or user.is_staff or user.is_superuser
    return profile.role == required_role


def _is_professor_or_admin(user):
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", "")
    return role in {"professor", "admin"} or user.is_staff or user.is_superuser


def _find_user(identifier, required_role=None):
    if required_role == "student":
        profile = UserProfile.objects.select_related("user").filter(student_id=identifier).first()
        if profile:
            return profile.user
    return User.objects.filter(username=identifier).first()


def _generate_two_factor_code():
    return f"{secrets.randbelow(10**6):06d}"


def _issue_two_factor_challenge(user):
    now = timezone.now()
    LoginTwoFactorChallenge.objects.filter(
        user=user,
        purpose="login",
        consumed_at__isnull=True,
        expires_at__gt=now,
    ).update(expires_at=now)

    code = _generate_two_factor_code()
    challenge = LoginTwoFactorChallenge(
        user=user,
        purpose="login",
        expires_at=now + timedelta(minutes=10),
    )
    challenge.set_code(code)
    challenge.save()

    if user.email:
        send_mail(
            subject="Your Uniwise verification code",
            message=(
                f"Your Uniwise login code is {code}. "
                "It will expire in 10 minutes."
            ),
            from_email=os.getenv("DEFAULT_FROM_EMAIL", "no-reply@uniwise.ai"),
            recipient_list=[user.email],
            fail_silently=True,
        )

    return challenge, code


def _consume_two_factor_challenge(challenge, raw_code):
    if challenge.consumed_at is not None:
        return False, "This two-factor challenge has already been used."
    if timezone.now() >= challenge.expires_at:
        return False, "This two-factor challenge has expired."
    if challenge.attempts >= 5:
        return False, "Maximum verification attempts exceeded."

    challenge.attempts += 1
    if not challenge.matches_code(raw_code):
        if challenge.attempts >= 5:
            challenge.expires_at = timezone.now()
        challenge.save(update_fields=["attempts", "expires_at"])
        return False, "Invalid two-factor code."

    challenge.consumed_at = timezone.now()
    challenge.save(update_fields=["attempts", "consumed_at"])
    return True, None


def _login_handler(request, required_role=None):
    identifier = request.data.get("username") or request.data.get("student_id")
    password = request.data.get("password")

    if not identifier or not password:
        return Response(
            {"error": "Username/student_id and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    matched_user = _find_user(identifier, required_role=required_role)
    auth_username = matched_user.username if matched_user else identifier

    user = authenticate(request, username=auth_username, password=password)
    if not user:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    profile = _ensure_profile(user)
    if required_role and not _is_role_allowed(user, profile, required_role):
        return Response(
            {"error": f"This account is not permitted for {required_role} login"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if profile.two_factor_enabled:
        challenge_id = request.data.get("challenge_id")
        two_factor_code = request.data.get("two_factor_code")

        if challenge_id and two_factor_code:
            challenge = LoginTwoFactorChallenge.objects.filter(
                challenge_id=challenge_id,
                user=user,
                purpose="login",
            ).first()
            if not challenge:
                return Response({"error": "Invalid two-factor challenge"}, status=status.HTTP_400_BAD_REQUEST)
            ok, message = _consume_two_factor_challenge(challenge, two_factor_code)
            if not ok:
                return Response({"error": message}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            challenge, debug_code = _issue_two_factor_challenge(user)
            payload = {
                "two_factor_required": True,
                "challenge_id": str(challenge.challenge_id),
                "message": "Two-factor code sent to your registered email.",
            }
            if settings.DEBUG:
                payload["debug_code"] = debug_code
            return Response(payload, status=status.HTTP_202_ACCEPTED)

    login(request, user)
    return Response(_auth_payload(user, profile, request))


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """Register a new student account."""
    username = request.data.get("username") or request.data.get("student_id")
    student_id = request.data.get("student_id") or username
    email = request.data.get("email")
    password = request.data.get("password")
    university_id = request.data.get("university_id")
    field_of_study = request.data.get("field_of_study", "")
    year_of_study = request.data.get("year_of_study", 1)
    two_factor_enabled = _as_bool(request.data.get("two_factor_enabled", False))
    sso_provider = request.data.get("sso_provider", "")

    if not all([username, student_id, email, password]):
        return Response(
            {"error": "student_id/username, email, and password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)
    if UserProfile.objects.filter(student_id=student_id).exists():
        return Response({"error": "Student ID already exists"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(password)
    except ValidationError as exc:
        return Response({"error": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, email=email, password=password)
    profile = UserProfile.objects.create(
        user=user,
        university_id=university_id or None,
        role="student",
        student_id=student_id,
        field_of_study=field_of_study,
        year_of_study=year_of_study,
        two_factor_enabled=two_factor_enabled,
        sso_provider=sso_provider,
    )

    return Response(
        {
            "message": "Account created successfully!",
            "user_id": user.id,
            "username": user.username,
            "student_id": profile.student_id,
            "role": profile.role,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """Generic login endpoint (backward compatible)."""
    return _login_handler(request, required_role=None)


@api_view(["POST"])
@permission_classes([AllowAny])
def student_login_view(request):
    """Role-enforced student login."""
    return _login_handler(request, required_role="student")


@api_view(["POST"])
@permission_classes([AllowAny])
def admin_login_view(request):
    """Role-enforced admin login."""
    return _login_handler(request, required_role="admin")


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_two_factor_view(request):
    """Verify two-factor challenge and complete login."""
    challenge_id = request.data.get("challenge_id")
    code = request.data.get("two_factor_code")
    if not challenge_id or not code:
        return Response(
            {"error": "challenge_id and two_factor_code are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    challenge = LoginTwoFactorChallenge.objects.select_related("user").filter(
        challenge_id=challenge_id,
        purpose="login",
    ).first()
    if not challenge:
        return Response({"error": "Invalid challenge"}, status=status.HTTP_400_BAD_REQUEST)

    ok, message = _consume_two_factor_challenge(challenge, code)
    if not ok:
        return Response({"error": message}, status=status.HTTP_401_UNAUTHORIZED)

    user = challenge.user
    profile = _ensure_profile(user)
    login(request, user)
    return Response(_auth_payload(user, profile, request), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def forgot_password(request):
    """Start password reset flow."""
    identifier = (
        request.data.get("identifier")
        or request.data.get("email")
        or request.data.get("username")
        or request.data.get("student_id")
    )
    if not identifier:
        return Response({"error": "identifier is required"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email__iexact=identifier).first()
    if not user:
        profile = UserProfile.objects.select_related("user").filter(student_id=identifier).first()
        if profile:
            user = profile.user
    if not user:
        user = User.objects.filter(username=identifier).first()

    payload = {
        "message": "If an account exists, password reset instructions have been sent.",
    }
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = PASSWORD_RESET_TOKEN_GENERATOR.make_token(user)
        reset_base_url = os.getenv("FRONTEND_RESET_PASSWORD_URL", "http://localhost:3000/reset-password")
        reset_link = f"{reset_base_url}?uid={uid}&token={token}"

        if user.email:
            send_mail(
                subject="Reset your Uniwise password",
                message=(
                    "Use the following link to reset your password:\n"
                    f"{reset_link}\n\n"
                    "If you did not request this, you can ignore this email."
                ),
                from_email=os.getenv("DEFAULT_FROM_EMAIL", "no-reply@uniwise.ai"),
                recipient_list=[user.email],
                fail_silently=True,
            )

        if settings.DEBUG:
            payload.update({
                "uid": uid,
                "token": token,
                "debug_reset_link": reset_link,
            })

    return Response(payload, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def reset_password(request):
    """Complete password reset with uid/token."""
    uid = request.data.get("uid")
    token = request.data.get("token")
    new_password = request.data.get("new_password")

    if not uid or not token or not new_password:
        return Response(
            {"error": "uid, token, and new_password are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except Exception:
        return Response({"error": "Invalid reset link"}, status=status.HTTP_400_BAD_REQUEST)

    if not PASSWORD_RESET_TOKEN_GENERATOR.check_token(user, token):
        return Response({"error": "Invalid or expired reset token"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        validate_password(new_password, user)
    except ValidationError as exc:
        return Response({"error": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(new_password)
    user.save(update_fields=["password"])
    LoginTwoFactorChallenge.objects.filter(user=user, consumed_at__isnull=True).update(
        expires_at=timezone.now()
    )
    return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([AllowAny])
def sso_providers(request):
    """List available SSO providers (scaffold)."""
    providers = _allowed_sso_providers()
    google_ready = bool(os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip())
    providers = [
        {
            "id": provider,
            "name": _sso_provider_label(provider),
            "status": (
                "ready"
                if provider == "google" and google_ready
                else "scaffold"
            ),
        }
        for provider in providers
    ]
    return Response({"providers": providers}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def sso_start(request):
    """Start SSO flow (scaffold)."""
    provider = request.data.get("provider", _allowed_sso_providers()[0])
    redirect_uri = request.data.get("redirect_uri", "")
    providers = _allowed_sso_providers()
    if provider not in providers:
        return Response({"error": "Unsupported SSO provider"}, status=status.HTTP_400_BAD_REQUEST)

    state = secrets.token_urlsafe(24)
    request.session["sso_state"] = state
    request.session["sso_provider"] = provider

    callback_url = request.build_absolute_uri("/api/accounts/sso/callback/")
    auth_url = f"{callback_url}?provider={provider}&state={state}&code=sample-code"
    ready = False
    message = "SSO scaffold initialized. Configure IdP settings to enable production SSO."

    if provider == "google":
        auth_url, ready = _build_google_auth_url(request, state)
        message = (
            "Google login configured. Redirect user to Google authorization."
            if ready
            else "Google login scaffold initialized. Set GOOGLE_OAUTH_CLIENT_ID to enable full OAuth redirect."
        )

    return Response(
        {
            "message": message,
            "provider": provider,
            "state": state,
            "auth_url": auth_url,
            "redirect_uri": redirect_uri,
            "status": "ready" if ready else "scaffold",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def sso_callback(request):
    """Handle SSO callback (scaffold)."""
    state = request.query_params.get("state")
    provider = request.query_params.get("provider")
    code = request.query_params.get("code")
    expected_state = request.session.get("sso_state")

    if not state or not expected_state or state != expected_state:
        return Response({"error": "Invalid SSO state"}, status=status.HTTP_400_BAD_REQUEST)

    request.session.pop("sso_state", None)
    request.session.pop("sso_provider", None)
    return Response(
        {
            "message": (
                "SSO callback received. This is a scaffold endpoint; "
                "configure provider token exchange and user mapping to complete SSO."
            ),
            "provider": provider,
            "code_received": bool(code),
            "status": "scaffold",
        },
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout user."""
    logout(request)
    return Response({"message": "Logged out successfully!"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get current user profile."""
    user = request.user
    profile_obj = _ensure_profile(user)
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "student_id": profile_obj.student_id,
            "email": user.email,
            "university": profile_obj.university.name if profile_obj.university else None,
            "role": profile_obj.role,
            "field_of_study": profile_obj.field_of_study,
            "year_of_study": profile_obj.year_of_study,
            "learning_pace": profile_obj.learning_pace,
            "two_factor_enabled": profile_obj.two_factor_enabled,
            "sso_provider": profile_obj.sso_provider,
            "university_id": profile_obj.university_id,
            "university_subdomain": profile_obj.university.subdomain if profile_obj.university else "",
            "university_custom_domain": profile_obj.university.custom_domain if profile_obj.university else "",
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def list_universities(request):
    """List all universities."""
    universities = University.objects.filter(is_active=True).order_by("name")
    data = [
        {
            "id": u.id,
            "name": u.name,
            "slug": u.slug,
            "country": u.country,
            "subdomain": u.subdomain,
            "custom_domain": u.custom_domain,
            "branding": {
                "primary_color": u.branding_primary_color,
                "secondary_color": u.branding_secondary_color,
                "logo_url": u.logo_url,
            },
            "allow_public_university_info": u.allow_public_university_info,
        }
        for u in universities
    ]
    return Response(data)


def _require_professor_or_admin(request):
    if _is_professor_or_admin(request.user):
        return None
    return Response({"error": "Professor/Admin access required"}, status=status.HTTP_403_FORBIDDEN)


def _api_key_hash(raw_key):
    normalized = (raw_key or "").strip()
    if not normalized:
        return "", ""
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest, normalized[-4:]


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsProfessorOrAdmin, IsUniversityScopedAccess])
def widget_embed_code(request):
    """Generate embeddable widget snippet for university websites."""
    access_error = _require_professor_or_admin(request)
    if access_error:
        return access_error

    profile = _ensure_profile(request.user)
    if not profile.university:
        return Response({"error": "University affiliation required"}, status=status.HTTP_400_BAD_REQUEST)

    university = profile.university
    base_widget_url = os.getenv(
        "WIDGET_BASE_URL",
        request.build_absolute_uri("/").rstrip("/"),
    )
    public_api_url = request.build_absolute_uri("/api/ai/ask/university-info/public/")

    snippet = (
        "<script>\n"
        "  window.UniwiseWidgetConfig = {\n"
        f"    universityId: {university.id},\n"
        f"    apiUrl: '{public_api_url}',\n"
        f"    primaryColor: '{university.branding_primary_color}',\n"
        f"    secondaryColor: '{university.branding_secondary_color}',\n"
        "  };\n"
        "</script>\n"
        f"<script async src=\"{base_widget_url}/static/uniwise-widget.js\"></script>"
    )

    return Response(
        {
            "university_id": university.id,
            "snippet": snippet,
            "widget_script_url": f"{base_widget_url}/static/uniwise-widget.js",
            "public_api_url": public_api_url,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsProfessorOrAdmin, IsUniversityScopedAccess])
def list_integrations(request):
    """List LMS/ERP/Calendar/SSO/Widget integrations for the user's university."""
    access_error = _require_professor_or_admin(request)
    if access_error:
        return access_error

    profile = _ensure_profile(request.user)
    if not profile.university:
        return Response({"error": "University affiliation required"}, status=status.HTTP_400_BAD_REQUEST)

    integrations = UniversityIntegration.objects.filter(university=profile.university).order_by("category", "provider_name")
    data = []
    for item in integrations:
        data.append(
            {
                "id": item.id,
                "category": item.category,
                "provider_name": item.provider_name,
                "status": item.status,
                "base_url": item.base_url,
                "config": item.config,
                "api_key_last4": item.api_key_last4,
                "updated_at": item.updated_at,
            }
        )

    return Response({"integrations": data})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsProfessorOrAdmin, IsUniversityScopedAccess])
def upsert_integration(request):
    """Create or update integration config for LMS/ERP/Calendar/SSO/widget."""
    access_error = _require_professor_or_admin(request)
    if access_error:
        return access_error

    profile = _ensure_profile(request.user)
    if not profile.university:
        return Response({"error": "University affiliation required"}, status=status.HTTP_400_BAD_REQUEST)

    category = request.data.get("category", "").strip()
    provider_name = request.data.get("provider_name", "").strip()
    status_value = request.data.get("status", "scaffold").strip()
    base_url = request.data.get("base_url", "").strip()
    config = request.data.get("config", {})
    api_key = request.data.get("api_key", "")

    valid_categories = {choice[0] for choice in UniversityIntegration.CATEGORY_CHOICES}
    valid_statuses = {choice[0] for choice in UniversityIntegration.STATUS_CHOICES}
    if category not in valid_categories:
        return Response({"error": f"category must be one of: {', '.join(sorted(valid_categories))}"}, status=400)
    if not provider_name:
        return Response({"error": "provider_name is required"}, status=400)
    if status_value not in valid_statuses:
        return Response({"error": f"status must be one of: {', '.join(sorted(valid_statuses))}"}, status=400)
    if config is None:
        config = {}
    if not isinstance(config, dict):
        return Response({"error": "config must be a JSON object"}, status=400)

    integration, created = UniversityIntegration.objects.get_or_create(
        university=profile.university,
        category=category,
        provider_name=provider_name,
        defaults={
            "created_by": request.user,
        },
    )
    integration.status = status_value
    integration.base_url = base_url
    integration.config = config
    if api_key:
        digest, last4 = _api_key_hash(api_key)
        integration.api_key_hash = digest
        integration.api_key_last4 = last4
    integration.save()

    return Response(
        {
            "message": "Integration saved",
            "created": created,
            "integration": {
                "id": integration.id,
                "category": integration.category,
                "provider_name": integration.provider_name,
                "status": integration.status,
                "base_url": integration.base_url,
                "config": integration.config,
                "api_key_last4": integration.api_key_last4,
                "updated_at": integration.updated_at,
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsProfessorOrAdmin, IsUniversityScopedAccess])
def audit_logs(request):
    """Fetch latest audit logs for security/compliance review."""
    access_error = _require_professor_or_admin(request)
    if access_error:
        return access_error

    profile = _ensure_profile(request.user)
    queryset = AuditLog.objects.all()
    if profile.university:
        queryset = queryset.filter(university=profile.university)

    logs = queryset.order_by("-created_at")[:200]
    data = [
        {
            "id": log.id,
            "request_id": str(log.request_id),
            "event_type": log.event_type,
            "action": log.action,
            "method": log.method,
            "path": log.path,
            "status_code": log.status_code,
            "duration_ms": log.duration_ms,
            "ip_address": log.ip_address,
            "user": log.user.username if log.user else None,
            "university_id": log.university_id,
            "metadata": log.metadata,
            "created_at": log.created_at,
        }
        for log in logs
    ]

    return Response({"logs": data})

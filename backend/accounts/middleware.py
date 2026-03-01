import time

from .models import AuditLog, University


def _extract_host(raw_host):
    host = (raw_host or "").strip().lower()
    if ":" in host:
        host = host.split(":", 1)[0]
    return host


def _guess_subdomain(host):
    if not host:
        return ""
    if host in {"localhost", "127.0.0.1"}:
        return ""
    parts = host.split(".")
    if len(parts) < 3:
        return ""
    return parts[0]


class UniversityTenantMiddleware:
    """
    Resolve university tenant context from:
    1) exact custom domain
    2) subdomain
    3) optional header X-University-Id (fallback)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant_university = None

        try:
            host = _extract_host(request.get_host())
            if host:
                request.tenant_university = (
                    University.objects.filter(is_active=True, custom_domain__iexact=host).first()
                )
                if request.tenant_university is None:
                    subdomain = _guess_subdomain(host)
                    if subdomain:
                        request.tenant_university = (
                            University.objects.filter(is_active=True, subdomain__iexact=subdomain).first()
                        )

            if request.tenant_university is None:
                header_university = request.headers.get("X-University-Id")
                if header_university and str(header_university).isdigit():
                    request.tenant_university = University.objects.filter(
                        id=int(header_university),
                        is_active=True,
                    ).first()
        except Exception:
            request.tenant_university = None

        return self.get_response(request)


class AuditLogMiddleware:
    """
    Lightweight API audit logger.
    Stores security/compliance evidence for API actions.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.time()
        response = self.get_response(request)
        duration_ms = int((time.time() - started_at) * 1000)

        path = (request.path or "").strip()
        if not path.startswith("/api/"):
            return response

        try:
            user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
            tenant_university = getattr(request, "tenant_university", None)
            profile = getattr(user, "profile", None) if user else None
            profile_university = getattr(profile, "university", None) if profile else None
            university = tenant_university or profile_university

            if path.startswith("/api/accounts/login") or path.startswith("/api/accounts/logout"):
                event_type = "auth"
            elif request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                event_type = "data_change"
            else:
                event_type = "data_access"

            action = f"{request.method} {path}"
            AuditLog.objects.create(
                event_type=event_type,
                action=action[:120],
                user=user,
                university=university,
                method=request.method,
                path=path[:255],
                status_code=getattr(response, "status_code", 0) or 0,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=(request.META.get("HTTP_USER_AGENT", "") or "")[:255],
                duration_ms=duration_ms,
                metadata={
                    "tenant_university_id": getattr(tenant_university, "id", None),
                    "profile_university_id": getattr(profile_university, "id", None),
                },
            )
        except Exception:
            # Never break request flow due to audit logging issues.
            pass

        return response

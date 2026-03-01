from rest_framework.permissions import BasePermission


def _get_role(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "role", "")


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and _get_role(request.user) == "student"


class IsProfessorOrAdmin(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = _get_role(request.user)
        return role in {"professor", "admin"} or request.user.is_staff or request.user.is_superuser


class IsUniversityScopedAccess(BasePermission):
    """
    Optional tenant guard:
    - If request.tenant_university exists, user must belong to the same university.
    - Staff/superusers bypass this check.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_staff or request.user.is_superuser:
            return True

        tenant_university = getattr(request, "tenant_university", None)
        if tenant_university is None:
            return True

        profile = getattr(request.user, "profile", None)
        user_university = getattr(profile, "university", None)
        if user_university is None:
            return False
        return user_university.id == tenant_university.id

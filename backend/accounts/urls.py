from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("login/student/", views.student_login_view, name="student_login"),
    path("login/admin/", views.admin_login_view, name="admin_login"),
    path("two-factor/verify/", views.verify_two_factor_view, name="verify_two_factor"),
    path("password/forgot/", views.forgot_password, name="forgot_password"),
    path("password/reset/", views.reset_password, name="reset_password"),
    path("sso/providers/", views.sso_providers, name="sso_providers"),
    path("sso/start/", views.sso_start, name="sso_start"),
    path("sso/callback/", views.sso_callback, name="sso_callback"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("universities/", views.list_universities, name="universities"),
    path("widget/embed/", views.widget_embed_code, name="widget_embed_code"),
    path("integrations/", views.list_integrations, name="list_integrations"),
    path("integrations/upsert/", views.upsert_integration, name="upsert_integration"),
    path("audit-logs/", views.audit_logs, name="audit_logs"),
]

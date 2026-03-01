from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("document-progress/", views.document_progress, name="document_progress"),
    path("learning-curve/", views.learning_curve, name="learning_curve"),
    path("skill-breakdown/", views.skill_breakdown, name="skill_breakdown"),
    path("session/start/", views.start_study_session, name="start_session"),
    path("session/<int:session_id>/end/", views.end_study_session, name="end_session"),
    path("admin/overview/", views.admin_overview, name="admin_overview"),
    path("admin/student-insights/", views.admin_student_insights, name="admin_student_insights"),
    path("admin/reports/", views.admin_reports, name="admin_reports"),
    path("admin/activity-log/", views.admin_activity_log, name="admin_activity_log"),
]

from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("learning-curve/", views.learning_curve, name="learning_curve"),
    path("skill-breakdown/", views.skill_breakdown, name="skill_breakdown"),
    path("session/start/", views.start_study_session, name="start_session"),
    path("session/<int:session_id>/end/", views.end_study_session, name="end_session"),
]

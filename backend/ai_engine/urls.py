from django.urls import path
from . import views

urlpatterns = [
    path("status/", views.ollama_status, name="ollama_status"),
    path("flashcards/generate/", views.generate_flashcards_view, name="generate_flashcards"),
    path("quiz/generate/", views.generate_quiz_view, name="generate_quiz"),
    path("exam-prep/generate/", views.generate_exam_prep_view, name="generate_exam_prep"),
    path("facts/extract/", views.extract_facts_view, name="extract_facts"),
]

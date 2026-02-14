from django.urls import path
from . import views

urlpatterns = [
    path("list/", views.list_flashcards, name="list_flashcards"),
    path("due-today/", views.flashcards_due_today, name="due_today"),
    path("<int:card_id>/review/", views.review_flashcard, name="review_flashcard"),
    path("<int:card_id>/delete/", views.delete_flashcard, name="delete_flashcard"),
]

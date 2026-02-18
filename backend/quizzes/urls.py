from django.urls import path
from . import views

urlpatterns = [
    path("list/", views.list_quizzes, name="list_quizzes"),
    path("<int:quiz_id>/", views.quiz_detail, name="quiz_detail"),
    path("<int:quiz_id>/submit/", views.submit_quiz, name="submit_quiz"),
    path("<int:quiz_id>/delete/", views.delete_quiz, name="delete_quiz"),
    path("history/", views.quiz_history, name="quiz_history"),
]

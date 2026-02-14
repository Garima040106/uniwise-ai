from django.db import models
from django.contrib.auth.models import User
from courses.models import Topic, Subject
from documents.models import Document


class Flashcard(models.Model):
    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="flashcards")
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    question = models.TextField()
    answer = models.TextField()
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="medium")
    is_ai_generated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Flashcard: {self.question[:50]}"


class FlashcardReview(models.Model):
    RATING_CHOICES = [
        (1, "Again"),
        (2, "Hard"),
        (3, "Good"),
        (4, "Easy"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="flashcard_reviews")
    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(choices=RATING_CHOICES)
    next_review_date = models.DateField(null=True, blank=True)
    interval_days = models.IntegerField(default=1)
    review_count = models.IntegerField(default=0)
    reviewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} reviewed {self.flashcard.question[:30]}"

    class Meta:
        ordering = ["-reviewed_at"]
# Create your models here.

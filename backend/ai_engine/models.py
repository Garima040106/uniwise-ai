from django.db import models
from django.contrib.auth.models import User
from documents.models import Document


class AIRequest(models.Model):
    TYPE_CHOICES = [
        ("flashcard", "Flashcard Generation"),
        ("quiz", "Quiz Generation"),
        ("summary", "Summary Generation"),
        ("fact", "Fact Extraction"),
        ("exam_prep", "Exam Prep Slides"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="ai_requests")
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True)
    request_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    prompt = models.TextField()
    response = models.TextField(blank=True)
    model_used = models.CharField(max_length=100, default="llama3.2:3b")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    tokens_used = models.IntegerField(default=0)
    processing_time_seconds = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.request_type} by {self.requested_by.username}"

    class Meta:
        ordering = ["-created_at"]


class ExamPrepSlide(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="exam_slides")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()
    key_points = models.TextField(blank=True)
    slide_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - Slide {self.slide_order}"

    class Meta:
        ordering = ["slide_order"]


class ConceptFact(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="facts")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    concept = models.CharField(max_length=255)
    fact = models.TextField()
    source_page = models.IntegerField(default=0)
    source_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Fact: {self.concept}"
# Create your models here.

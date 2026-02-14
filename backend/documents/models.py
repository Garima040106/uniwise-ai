from django.db import models
from django.contrib.auth.models import User
from courses.models import Course, Subject


class Document(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    TYPE_CHOICES = [
        ("pdf", "PDF"),
        ("docx", "Word Document"),
        ("txt", "Text File"),
        ("pptx", "PowerPoint"),
    ]

    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploads/")
    file_type = models.CharField(max_length=10, choices=TYPE_CHOICES, blank=True)
    file_size = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    extracted_text = models.TextField(blank=True)
    page_count = models.IntegerField(default=0)
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.file_type})"


class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    content = models.TextField()
    chunk_index = models.IntegerField(default=0)
    embedding_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"

    class Meta:
        ordering = ["chunk_index"]
# Create your models here.

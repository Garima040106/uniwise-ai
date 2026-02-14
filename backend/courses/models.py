from django.db import models
from accounts.models import University


class Course(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="courses")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    semester = models.CharField(max_length=50, blank=True)
    year = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Subject(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="subjects")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.name} - {self.name}"

    class Meta:
        ordering = ["order"]


class Topic(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="topics")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject.name} - {self.name}"

    class Meta:
        ordering = ["order"]
# Create your models here.

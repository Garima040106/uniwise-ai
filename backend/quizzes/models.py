from django.db import models
from django.contrib.auth.models import User
from courses.models import Subject, Topic
from documents.models import Document


class Quiz(models.Model):
    DIFFICULTY_CHOICES = [
        ("easy", "Easy"),
        ("medium", "Medium"),
        ("hard", "Hard"),
    ]

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quizzes")
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default="medium")
    time_limit_minutes = models.IntegerField(default=30)
    is_ai_generated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    TYPE_CHOICES = [
        ("mcq", "Multiple Choice"),
        ("true_false", "True or False"),
        ("short", "Short Answer"),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="mcq")
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct_answer = models.CharField(max_length=500)
    explanation = models.TextField(blank=True)
    marks = models.IntegerField(default=1)
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.quiz.title} - Q{self.order}"

    class Meta:
        ordering = ["order"]


class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    score = models.FloatField(default=0)
    total_marks = models.IntegerField(default=0)
    percentage = models.FloatField(default=0)
    time_taken_minutes = models.FloatField(default=0)
    completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} - {self.percentage}%"

    class Meta:
        ordering = ["-started_at"]


class QuestionResponse(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user_answer = models.CharField(max_length=500, blank=True)
    is_correct = models.BooleanField(default=False)
    marks_awarded = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.attempt.user.username} - Q: {self.question.question_text[:30]}"
# Create your models here.

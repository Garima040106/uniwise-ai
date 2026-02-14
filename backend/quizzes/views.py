from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import Quiz, Question, QuizAttempt, QuestionResponse


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_quizzes(request):
    """List all quizzes for current user"""
    quizzes = Quiz.objects.filter(created_by=request.user).order_by("-created_at")
    data = [{
        "id": q.id,
        "title": q.title,
        "difficulty": q.difficulty,
        "question_count": q.questions.count(),
        "time_limit_minutes": q.time_limit_minutes,
        "created_at": q.created_at,
    } for q in quizzes]
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def quiz_detail(request, quiz_id):
    """Get full quiz with questions"""
    try:
        quiz = Quiz.objects.get(id=quiz_id, created_by=request.user)
    except Quiz.DoesNotExist:
        return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)

    questions = [{
        "id": q.id,
        "question": q.question_text,
        "type": q.question_type,
        "options": {
            "A": q.option_a,
            "B": q.option_b,
            "C": q.option_c,
            "D": q.option_d,
        },
        "marks": q.marks,
    } for q in quiz.questions.all()]

    return Response({
        "id": quiz.id,
        "title": quiz.title,
        "difficulty": quiz.difficulty,
        "time_limit_minutes": quiz.time_limit_minutes,
        "questions": questions,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_quiz(request, quiz_id):
    """Submit quiz answers and get results"""
    try:
        quiz = Quiz.objects.get(id=quiz_id)
    except Quiz.DoesNotExist:
        return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)

    answers = request.data.get("answers", {})

    attempt = QuizAttempt.objects.create(
        user=request.user,
        quiz=quiz,
        completed=True,
        completed_at=timezone.now(),
    )

    score = 0
    total_marks = 0
    results = []

    for question in quiz.questions.all():
        total_marks += question.marks
        user_answer = answers.get(str(question.id), "").strip().upper()
        is_correct = user_answer == question.correct_answer.strip().upper()

        if is_correct:
            score += question.marks

        QuestionResponse.objects.create(
            attempt=attempt,
            question=question,
            user_answer=user_answer,
            is_correct=is_correct,
            marks_awarded=question.marks if is_correct else 0,
        )

        results.append({
            "question": question.question_text,
            "your_answer": user_answer,
            "correct_answer": question.correct_answer,
            "is_correct": is_correct,
            "explanation": question.explanation,
        })

    percentage = round((score / total_marks * 100), 2) if total_marks > 0 else 0
    attempt.score = score
    attempt.total_marks = total_marks
    attempt.percentage = percentage
    attempt.save()

    return Response({
        "message": "Quiz submitted!",
        "score": score,
        "total_marks": total_marks,
        "percentage": percentage,
        "results": results,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def quiz_history(request):
    """Get user's quiz attempt history"""
    attempts = QuizAttempt.objects.filter(
        user=request.user,
        completed=True
    ).order_by("-started_at")[:20]

    data = [{
        "quiz_title": a.quiz.title,
        "score": a.score,
        "total_marks": a.total_marks,
        "percentage": a.percentage,
        "date": a.started_at,
    } for a in attempts]

    return Response(data)
# Create your views here.

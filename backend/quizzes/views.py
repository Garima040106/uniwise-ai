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
        "completed": QuizAttempt.objects.filter(
            user=request.user,
            quiz=q,
            completed=True,
        ).exists(),
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

    correct_count = sum(1 for item in results if item["is_correct"])
    incorrect_count = sum(1 for item in results if not item["is_correct"] and item["your_answer"])
    unanswered_count = sum(1 for item in results if not item["your_answer"])

    if percentage >= 80:
        summary = "Strong performance. Your understanding is solid."
        recommendation = "Try hard-level quizzes from the same document to deepen retention."
    elif percentage >= 60:
        summary = "Good progress with some gaps to revise."
        recommendation = "Review missed concepts, then retake a medium quiz."
    else:
        summary = "Foundational concepts need reinforcement."
        recommendation = "Revise the document and retry an easy quiz before moving up."

    missed_questions = [item["question"] for item in results if not item["is_correct"]][:3]

    return Response({
        "message": "Quiz submitted!",
        "score": score,
        "total_marks": total_marks,
        "percentage": percentage,
        "results": results,
        "analysis": {
            "summary": summary,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "unanswered_count": unanswered_count,
            "accuracy": round((correct_count / len(results)) * 100, 2) if results else 0,
            "focus_topics": missed_questions,
            "recommendation": recommendation,
        },
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


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_quiz(request, quiz_id):
    """Delete a quiz owned by current user"""
    try:
        quiz = Quiz.objects.get(id=quiz_id, created_by=request.user)
    except Quiz.DoesNotExist:
        return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)

    quiz.delete()
    return Response({"message": "Quiz deleted"}, status=status.HTTP_200_OK)
# Create your views here.

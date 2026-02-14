from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import LearningProgress, StudySession, SkillSnapshot
from quizzes.models import QuizAttempt
from flashcards.models import FlashcardReview


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Main dashboard - overall progress summary"""
    user = request.user

    total_flashcards = FlashcardReview.objects.filter(user=user).count()
    total_quizzes = QuizAttempt.objects.filter(user=user, completed=True).count()

    quiz_scores = QuizAttempt.objects.filter(
        user=user, completed=True
    ).values_list("percentage", flat=True)
    avg_score = round(sum(quiz_scores) / len(quiz_scores), 2) if quiz_scores else 0

    total_study_minutes = StudySession.objects.filter(
        user=user
    ).values_list("duration_minutes", flat=True)
    total_minutes = sum(total_study_minutes)

    progress_records = LearningProgress.objects.filter(user=user)
    skill_levels = [p.skill_level for p in progress_records]
    overall_skill = round(sum(skill_levels) / len(skill_levels), 2) if skill_levels else 0

    return Response({
        "overall_skill_level": overall_skill,
        "total_flashcards_reviewed": total_flashcards,
        "total_quizzes_completed": total_quizzes,
        "average_quiz_score": avg_score,
        "total_study_minutes": total_minutes,
        "total_study_hours": round(total_minutes / 60, 1),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def learning_curve(request):
    """Get learning curve data for charts"""
    user = request.user

    attempts = QuizAttempt.objects.filter(
        user=user, completed=True
    ).order_by("started_at")[:30]

    curve_data = [{
        "date": str(a.started_at.date()),
        "score": a.percentage,
        "quiz": a.quiz.title,
    } for a in attempts]

    snapshots = SkillSnapshot.objects.filter(user=user).order_by("recorded_at")[:30]
    skill_data = [{
        "date": str(s.recorded_at.date()),
        "skill_level": s.skill_level,
        "course": s.course.name,
    } for s in snapshots]

    return Response({
        "quiz_performance": curve_data,
        "skill_progression": skill_data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_study_session(request):
    """Start a new study session"""
    course_id = request.data.get("course_id")
    session = StudySession.objects.create(
        user=request.user,
        course_id=course_id,
    )
    return Response({
        "session_id": session.id,
        "started_at": session.started_at,
        "message": "Study session started!",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end_study_session(request, session_id):
    """End a study session and record duration"""
    try:
        session = StudySession.objects.get(id=session_id, user=request.user)
    except StudySession.DoesNotExist:
        return Response({"error": "Session not found"})

    session.ended_at = timezone.now()
    duration = (session.ended_at - session.started_at).seconds // 60
    session.duration_minutes = duration
    session.flashcards_reviewed = request.data.get("flashcards_reviewed", 0)
    session.quizzes_taken = request.data.get("quizzes_taken", 0)
    session.save()

    return Response({
        "message": "Session ended!",
        "duration_minutes": duration,
        "flashcards_reviewed": session.flashcards_reviewed,
        "quizzes_taken": session.quizzes_taken,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def skill_breakdown(request):
    """Get skill level breakdown by course"""
    progress = LearningProgress.objects.filter(user=request.user)
    data = [{
        "course": p.course.name,
        "skill_level": p.skill_level,
        "quizzes_completed": p.quizzes_completed,
        "average_score": p.average_quiz_score,
        "study_streak": p.study_streak_days,
        "last_studied": p.last_studied,
    } for p in progress]

    return Response(data)
# Create your views here.

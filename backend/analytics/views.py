from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg, Count, Max, Q, Sum, Value
from django.db.models.functions import Coalesce
import requests as req
from .models import LearningProgress, StudySession, SkillSnapshot
from quizzes.models import QuizAttempt, Question, QuestionResponse
from flashcards.models import Flashcard, FlashcardReview
from documents.models import Document
from ai_engine.models import AIRequest
from accounts.models import UserProfile
from accounts.permissions import IsProfessorOrAdmin, IsUniversityScopedAccess


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


def _get_visible_documents(user):
    profile = getattr(user, "profile", None)
    if profile and profile.role == "professor":
        return Document.objects.filter(uploaded_by=user).order_by("-created_at")
    if profile and profile.university:
        return Document.objects.filter(
            uploaded_by__profile__university=profile.university
        ).order_by("-created_at")
    return Document.objects.filter(uploaded_by=user).order_by("-created_at")


def _is_admin_context(user):
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", "")
    return role in {"admin", "professor"} or user.is_staff or user.is_superuser


def _admin_scope_users(user):
    profile = getattr(user, "profile", None)
    if profile and profile.university:
        return UserProfile.objects.filter(university=profile.university).values_list("user_id", flat=True)
    return [user.id]


def _topic_grouped_queryset(base_queryset):
    return (
        base_queryset.annotate(
            topic_label=Coalesce(
                "question__quiz__topic__name",
                "question__quiz__subject__name",
                Value("General"),
            )
        )
        .values("topic_label")
    )


def _build_activity_log(scoped_user_ids, limit=15):
    activity = []

    recent_docs = Document.objects.filter(uploaded_by_id__in=scoped_user_ids).order_by("-created_at")[:limit]
    for doc in recent_docs:
        activity.append({
            "timestamp": doc.created_at,
            "type": "document_upload",
            "message": f"{doc.uploaded_by.username} uploaded '{doc.title}'",
        })

    recent_ai = AIRequest.objects.filter(requested_by_id__in=scoped_user_ids).order_by("-created_at")[:limit]
    for req_item in recent_ai:
        activity.append({
            "timestamp": req_item.created_at,
            "type": "ai_request",
            "message": f"{req_item.requested_by.username} used AI for {req_item.request_type}",
        })

    recent_attempts = QuizAttempt.objects.filter(user_id__in=scoped_user_ids).order_by("-started_at")[:limit]
    for attempt in recent_attempts:
        activity.append({
            "timestamp": attempt.started_at,
            "type": "quiz_attempt",
            "message": (
                f"{attempt.user.username} attempted '{attempt.quiz.title}'"
                + (f" ({round(attempt.percentage, 1)}%)" if attempt.completed else "")
            ),
        })

    activity.sort(key=lambda item: item["timestamp"], reverse=True)
    return activity[:limit]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def document_progress(request):
    """Estimated learning coverage (1-100) for each visible document."""
    user = request.user
    doc_id = request.query_params.get("document_id")

    documents = _get_visible_documents(user)
    if doc_id:
        documents = documents.filter(id=doc_id)

    data = []
    for doc in documents:
        total_questions = Question.objects.filter(quiz__document=doc).count()
        attempted_questions = QuestionResponse.objects.filter(
            attempt__user=user,
            attempt__completed=True,
            question__quiz__document=doc,
        ).values("question_id").distinct().count()

        total_flashcards = Flashcard.objects.filter(document=doc).count()
        reviewed_flashcards = FlashcardReview.objects.filter(
            user=user,
            flashcard__document=doc,
        ).values("flashcard_id").distinct().count()

        available_items = total_questions + total_flashcards
        covered_items = attempted_questions + reviewed_flashcards
        if available_items > 0:
            progress_score = round((covered_items / available_items) * 100)
        else:
            chunk_count = doc.chunks.count()
            activity_count = attempted_questions + reviewed_flashcards
            progress_score = round((activity_count / max(chunk_count, 1)) * 100) if chunk_count else 0

        if doc.is_processed:
            progress_score = max(1, progress_score)
        progress_score = min(100, progress_score)

        data.append({
            "document_id": doc.id,
            "title": doc.title,
            "progress_score": progress_score,
            "question_coverage": {
                "covered": attempted_questions,
                "total": total_questions,
            },
            "flashcard_coverage": {
                "covered": reviewed_flashcards,
                "total": total_flashcards,
            },
            "is_processed": doc.is_processed,
        })

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsProfessorOrAdmin, IsUniversityScopedAccess])
def admin_overview(request):
    """Admin/professor university-level dashboard metrics."""
    if not _is_admin_context(request.user):
        return Response({"error": "Admin/professor access required"}, status=403)

    scoped_user_ids = _admin_scope_users(request.user)
    student_ids = UserProfile.objects.filter(
        user_id__in=scoped_user_ids,
        role="student",
    ).values_list("user_id", flat=True)

    documents_qs = Document.objects.filter(uploaded_by_id__in=scoped_user_ids)
    ai_qs = AIRequest.objects.filter(requested_by_id__in=scoped_user_ids)
    attempts_qs = QuizAttempt.objects.filter(user_id__in=student_ids, completed=True)

    now = timezone.now()
    week_ago = now - timezone.timedelta(days=7)

    active_student_ids = set(
        list(StudySession.objects.filter(user_id__in=student_ids, started_at__gte=week_ago).values_list("user_id", flat=True))
        + list(QuizAttempt.objects.filter(user_id__in=student_ids, started_at__gte=week_ago).values_list("user_id", flat=True))
        + list(AIRequest.objects.filter(requested_by_id__in=student_ids, created_at__gte=week_ago).values_list("requested_by_id", flat=True))
    )

    trending_questions = []
    top_questions_qs = (
        ai_qs.filter(request_type="ask")
        .exclude(prompt__isnull=True)
        .exclude(prompt__exact="")
        .values("prompt")
        .annotate(ask_count=Count("id"), last_asked=Max("created_at"))
        .order_by("-ask_count", "-last_asked")[:5]
    )
    for row in top_questions_qs:
        prompt_text = row["prompt"].strip()
        trending_questions.append({
            "question": (prompt_text[:140] + "...") if len(prompt_text) > 140 else prompt_text,
            "count": row["ask_count"],
            "last_asked": row["last_asked"],
        })

    system_health = {
        "status": "unknown",
        "model": settings.OLLAMA_MODEL,
        "message": "Health check not run.",
        "model_available": False,
    }
    try:
        tags_response = req.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=8)
        if tags_response.status_code == 200:
            models = (tags_response.json() or {}).get("models", [])
            model_names = [m.get("name", "") for m in models if m.get("name")]
            system_health.update({
                "status": "online",
                "model_available": settings.OLLAMA_MODEL in model_names,
                "installed_models": model_names[:12],
                "message": "Ollama reachable.",
            })
        else:
            system_health.update({
                "status": "offline",
                "message": f"Ollama health check failed ({tags_response.status_code}).",
            })
    except Exception as exc:
        system_health.update({
            "status": "offline",
            "message": str(exc),
        })

    return Response({
        "university_overview": {
            "total_students": len(set(student_ids)),
            "total_documents_uploaded": documents_qs.count(),
            "total_ai_requests": ai_qs.count(),
            "total_quizzes_completed": attempts_qs.count(),
            "active_students_last_7_days": len(active_student_ids),
            "class_average_quiz_score": round(attempts_qs.aggregate(avg=Avg("percentage")).get("avg") or 0, 2),
        },
        "most_asked_questions": trending_questions,
        "system_health": system_health,
        "recent_activity": _build_activity_log(scoped_user_ids, limit=12),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsProfessorOrAdmin, IsUniversityScopedAccess])
def admin_student_insights(request):
    """Class-level and individual student analytics for admin/professor."""
    if not _is_admin_context(request.user):
        return Response({"error": "Admin/professor access required"}, status=403)

    scoped_user_ids = _admin_scope_users(request.user)
    student_profiles = list(
        UserProfile.objects.select_related("user")
        .filter(user_id__in=scoped_user_ids, role="student")
    )
    student_ids = [profile.user_id for profile in student_profiles]

    attempts_qs = QuizAttempt.objects.filter(user_id__in=student_ids, completed=True)
    responses_qs = QuestionResponse.objects.filter(
        attempt__user_id__in=student_ids,
        attempt__completed=True,
    )
    study_qs = StudySession.objects.filter(user_id__in=student_ids)
    ask_qs = AIRequest.objects.filter(requested_by_id__in=student_ids, request_type="ask")

    now = timezone.now()
    month_ago = now - timezone.timedelta(days=30)
    active_student_ids = set(
        list(StudySession.objects.filter(user_id__in=student_ids, started_at__gte=month_ago).values_list("user_id", flat=True))
        + list(QuizAttempt.objects.filter(user_id__in=student_ids, started_at__gte=month_ago).values_list("user_id", flat=True))
        + list(AIRequest.objects.filter(requested_by_id__in=student_ids, created_at__gte=month_ago).values_list("requested_by_id", flat=True))
    )

    topic_heatmap_raw = (
        _topic_grouped_queryset(responses_qs)
        .annotate(
            total_attempts=Count("id"),
            incorrect_attempts=Count("id", filter=Q(is_correct=False)),
        )
        .order_by("-incorrect_attempts", "-total_attempts")[:10]
    )
    topic_heatmap = []
    for row in topic_heatmap_raw:
        total_attempts = row["total_attempts"] or 1
        topic_heatmap.append({
            "topic": row["topic_label"],
            "difficulty_index": round((row["incorrect_attempts"] / total_attempts) * 100, 1),
            "attempts": row["total_attempts"],
        })

    most_asked_students_raw = (
        ask_qs.exclude(prompt__exact="")
        .values("prompt")
        .annotate(ask_count=Count("id"))
        .order_by("-ask_count")[:8]
    )
    most_asked_students = [
        {
            "question": (row["prompt"][:120] + "...") if len(row["prompt"]) > 120 else row["prompt"],
            "count": row["ask_count"],
        }
        for row in most_asked_students_raw
    ]

    docs = list(Document.objects.filter(uploaded_by_id__in=scoped_user_ids).order_by("-created_at")[:30])
    document_usage = []
    for doc in docs:
        flashcard_reviews = FlashcardReview.objects.filter(
            flashcard__document=doc,
            user_id__in=student_ids,
        ).count()
        question_attempts = QuestionResponse.objects.filter(
            question__quiz__document=doc,
            attempt__user_id__in=student_ids,
            attempt__completed=True,
        ).count()
        ai_doc_questions = ask_qs.filter(document_id=doc.id).count()
        usage_score = flashcard_reviews + question_attempts + ai_doc_questions
        document_usage.append({
            "document_id": doc.id,
            "title": doc.title,
            "usage_score": usage_score,
            "flashcard_reviews": flashcard_reviews,
            "quiz_interactions": question_attempts,
            "ai_questions": ai_doc_questions,
        })
    document_usage.sort(key=lambda item: item["usage_score"], reverse=True)
    document_usage = document_usage[:10]

    individual = []
    at_risk = []
    for profile in student_profiles:
        user = profile.user
        quizzes_completed = attempts_qs.filter(user=user).count()
        avg_score = attempts_qs.filter(user=user).aggregate(avg=Avg("percentage")).get("avg") or 0
        flashcard_reviews = FlashcardReview.objects.filter(user=user).count()
        study_minutes = study_qs.filter(user=user).aggregate(total=Sum("duration_minutes")).get("total") or 0
        asked_questions = ask_qs.filter(requested_by=user).count()

        weak_topic_entry = (
            _topic_grouped_queryset(responses_qs.filter(attempt__user=user))
            .annotate(total_attempts=Count("id"), incorrect_attempts=Count("id", filter=Q(is_correct=False)))
            .order_by("-incorrect_attempts", "-total_attempts")
            .first()
        )
        weak_area = weak_topic_entry["topic_label"] if weak_topic_entry and weak_topic_entry["incorrect_attempts"] > 0 else "No clear weak area yet"

        student_row = {
            "student_id": profile.student_id,
            "username": user.username,
            "quiz_scores_average": round(avg_score, 2),
            "quizzes_completed": quizzes_completed,
            "flashcard_review_frequency": flashcard_reviews,
            "study_hours_logged": round(study_minutes / 60, 2),
            "questions_asked": asked_questions,
            "weak_area": weak_area,
            "engagement_score": round((quizzes_completed * 3) + (flashcard_reviews * 0.5) + (asked_questions * 0.8), 2),
        }
        individual.append(student_row)

        if (study_minutes < 45 and quizzes_completed == 0) or (avg_score < 45 and quizzes_completed >= 2):
            at_risk.append({
                "student_id": profile.student_id,
                "username": user.username,
                "reason": (
                    "Low engagement"
                    if study_minutes < 45 and quizzes_completed == 0
                    else "Low assessment performance"
                ),
            })

    individual.sort(key=lambda item: item["engagement_score"], reverse=True)

    return Response({
        "class_level": {
            "class_average_quiz_scores": round(attempts_qs.aggregate(avg=Avg("percentage")).get("avg") or 0, 2),
            "engagement_metrics": {
                "total_questions_asked": ask_qs.count(),
                "study_hours_logged": round((study_qs.aggregate(total=Sum("duration_minutes")).get("total") or 0) / 60, 2),
                "active_students_last_30_days": len(active_student_ids),
                "students_count": len(student_ids),
            },
            "topic_difficulty_heatmap": topic_heatmap,
            "most_asked_questions": most_asked_students,
            "document_usage_statistics": document_usage,
        },
        "individual_student_analytics": individual[:30],
        "at_risk_student_alerts": at_risk[:20],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsProfessorOrAdmin, IsUniversityScopedAccess])
def admin_reports(request):
    """Reporting endpoint for admin/professor insights."""
    if not _is_admin_context(request.user):
        return Response({"error": "Admin/professor access required"}, status=403)

    scoped_user_ids = _admin_scope_users(request.user)
    student_ids = UserProfile.objects.filter(
        user_id__in=scoped_user_ids,
        role="student",
    ).values_list("user_id", flat=True)

    now = timezone.now()
    one_day_ago = now - timezone.timedelta(days=1)
    seven_days_ago = now - timezone.timedelta(days=7)
    thirty_days_ago = now - timezone.timedelta(days=30)

    session_qs = StudySession.objects.filter(user_id__in=student_ids)
    quiz_qs = QuizAttempt.objects.filter(user_id__in=student_ids, completed=True)
    ask_qs = AIRequest.objects.filter(requested_by_id__in=student_ids, request_type="ask")

    def active_students_since(since_dt):
        return len(set(
            list(session_qs.filter(started_at__gte=since_dt).values_list("user_id", flat=True))
            + list(quiz_qs.filter(started_at__gte=since_dt).values_list("user_id", flat=True))
            + list(ask_qs.filter(created_at__gte=since_dt).values_list("requested_by_id", flat=True))
        ))

    ai_perf = AIRequest.objects.filter(requested_by_id__in=scoped_user_ids)
    ai_total = ai_perf.count()
    ai_completed = ai_perf.filter(status="completed").count()

    content_effectiveness = []
    docs = Document.objects.filter(uploaded_by_id__in=scoped_user_ids).order_by("-created_at")[:40]
    for doc in docs:
        quiz_usage = QuizAttempt.objects.filter(
            quiz__document=doc,
            user_id__in=student_ids,
            completed=True,
        ).count()
        flashcard_usage = FlashcardReview.objects.filter(
            flashcard__document=doc,
            user_id__in=student_ids,
        ).count()
        ask_usage = ask_qs.filter(document_id=doc.id).count()
        usage_count = quiz_usage + flashcard_usage + ask_usage
        content_effectiveness.append({
            "title": doc.title,
            "usage_count": usage_count,
        })
    content_effectiveness.sort(key=lambda item: item["usage_count"], reverse=True)

    return Response({
        "platform_usage_reports": {
            "daily_active_students": active_students_since(one_day_ago),
            "weekly_active_students": active_students_since(seven_days_ago),
            "monthly_active_students": active_students_since(thirty_days_ago),
            "daily_ai_requests": ai_perf.filter(created_at__gte=one_day_ago).count(),
            "weekly_ai_requests": ai_perf.filter(created_at__gte=seven_days_ago).count(),
            "monthly_ai_requests": ai_perf.filter(created_at__gte=thirty_days_ago).count(),
        },
        "student_engagement_reports": {
            "average_study_hours_per_student": round(
                ((session_qs.aggregate(total=Sum("duration_minutes")).get("total") or 0) / max(len(set(student_ids)), 1)) / 60, 2
            ),
            "quiz_completion_count_30_days": quiz_qs.filter(started_at__gte=thirty_days_ago).count(),
            "questions_asked_30_days": ask_qs.filter(created_at__gte=thirty_days_ago).count(),
        },
        "content_effectiveness_reports": {
            "top_helpful_documents": content_effectiveness[:10],
        },
        "ai_performance_metrics": {
            "request_success_rate": round((ai_completed / ai_total) * 100, 2) if ai_total else 0,
            "average_processing_time_seconds": round(ai_perf.aggregate(avg=Avg("processing_time_seconds")).get("avg") or 0, 2),
            "total_requests": ai_total,
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsProfessorOrAdmin, IsUniversityScopedAccess])
def admin_activity_log(request):
    """Recent system activity for admin/professor monitoring."""
    if not _is_admin_context(request.user):
        return Response({"error": "Admin/professor access required"}, status=403)

    scoped_user_ids = _admin_scope_users(request.user)
    return Response({
        "recent_activity_log": _build_activity_log(scoped_user_ids, limit=25),
    })
# Create your views here.

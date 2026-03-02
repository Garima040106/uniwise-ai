import time
import hashlib
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.conf import settings
from django.core.cache import cache
from accounts.models import University
from accounts.permissions import IsUniversityScopedAccess
from courses.models import Course
from documents.models import Document
from flashcards.models import Flashcard
from quizzes.models import Quiz, Question
from django.db.models.functions import Lower
from .models import AIRequest, ExamPrepSlide, ConceptFact
from .utils import (
    generate_flashcards,
    generate_quiz,
    generate_summary,
    extract_facts,
    answer_question_rag,
)


def get_university_id(user):
    profile = getattr(user, "profile", None)
    if profile and profile.university:
        return profile.university.id
    return None


def get_request_university_id(request, allow_tenant_fallback=True):
    profile = getattr(request.user, "profile", None) if getattr(request, "user", None) else None
    if profile and profile.university:
        return profile.university.id

    if allow_tenant_fallback:
        tenant = getattr(request, "tenant_university", None)
        if tenant:
            return tenant.id
    return None


def _parse_optional_int(raw_value, field_name):
    if raw_value in (None, ""):
        return None, None
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be an integer"
    if parsed <= 0:
        return None, f"{field_name} must be a positive integer"
    return parsed, None


def _parse_positive_int(raw_value, field_name, default_value):
    if raw_value in (None, ""):
        return default_value, None
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return None, f"{field_name} must be an integer"
    if parsed <= 0:
        return None, f"{field_name} must be greater than 0"
    return parsed, None


def _qa_cache_key(university_id, question, course_id=None, document_id=None, knowledge_base="academic", visibility_scope=None):
    payload = f"{university_id}|{knowledge_base}|{visibility_scope}|{course_id}|{document_id}|{question.strip().lower()}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"qa_answer:{digest}"


def _fetch_cached_answer(cache_key):
    cached = cache.get(cache_key)
    if not cached:
        return None
    return {
        "question": cached.get("question", ""),
        "answer": cached.get("answer", ""),
        "sources": cached.get("sources", []),
        "found_in_docs": cached.get("found_in_docs", False),
        "cached": True,
    }


def _store_cached_answer(cache_key, payload):
    timeout = getattr(settings, "RAG_ANSWER_CACHE_TIMEOUT", 300)
    cache.set(cache_key, payload, timeout=timeout)


def _get_document_for_generation(request, doc_id):
    profile = getattr(request.user, "profile", None)
    university = getattr(profile, "university", None)
    if university:
        return Document.objects.filter(
            id=doc_id,
            uploaded_by__profile__university=university,
        ).first()
    return Document.objects.filter(id=doc_id, uploaded_by=request.user).first()


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def generate_flashcards_view(request):
    """Generate flashcards from a document"""
    doc_id = request.data.get("document_id")
    num_cards, num_cards_error = _parse_positive_int(request.data.get("num_cards"), "num_cards", 10)
    if num_cards_error:
        return Response({"error": num_cards_error}, status=status.HTTP_400_BAD_REQUEST)
    difficulty = request.data.get("difficulty", "medium")

    doc = _get_document_for_generation(request, doc_id)
    if not doc:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
    if getattr(doc, "knowledge_base", "academic") != "academic":
        return Response(
            {"error": "Flashcard generation is only supported for academic documents."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not doc.extracted_text:
        return Response({"error": "Document has no extracted text"}, status=status.HTTP_400_BAD_REQUEST)

    ai_request = AIRequest.objects.create(
        requested_by=request.user,
        document=doc,
        request_type="flashcard",
        prompt=f"Generate {num_cards} flashcards at {difficulty} difficulty",
        model_used="llama3.2:3b",
        status="processing",
    )

    start_time = time.time()
    university_id = get_university_id(request.user)
    course_id = request.data.get("course_id") or doc.course_id
    cards_data = generate_flashcards(
        doc.extracted_text,
        university_id=university_id,
        course_id=course_id,
        document_id=doc.id,
        num_cards=num_cards,
        difficulty=difficulty,
    )
    processing_time = time.time() - start_time

    if not cards_data:
        ai_request.status = "failed"
        ai_request.save()
        return Response({
            "error": (
                "Failed to generate flashcards. Ollama may be busy on CPU-only mode. "
                "Try fewer cards (2-3) or wait 1-3 minutes and retry."
            )
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    created_cards = []
    for card in cards_data:
        flashcard = Flashcard.objects.create(
            created_by=request.user,
            document=doc,
            question=card.get("question", ""),
            answer=card.get("answer", ""),
            difficulty=card.get("difficulty", difficulty),
            is_ai_generated=True,
        )
        created_cards.append({
            "id": flashcard.id,
            "question": flashcard.question,
            "answer": flashcard.answer,
            "difficulty": flashcard.difficulty,
        })

    ai_request.status = "completed"
    ai_request.processing_time_seconds = processing_time
    ai_request.save()

    return Response({
        "message": f"Successfully generated {len(created_cards)} flashcards!",
        "processing_time": round(processing_time, 2),
        "flashcards": created_cards,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def generate_quiz_view(request):
    """Generate a quiz from a document"""
    doc_id = request.data.get("document_id")
    num_questions, num_questions_error = _parse_positive_int(request.data.get("num_questions"), "num_questions", 5)
    if num_questions_error:
        return Response({"error": num_questions_error}, status=status.HTTP_400_BAD_REQUEST)
    difficulty = request.data.get("difficulty", "medium")
    title = request.data.get("title", "AI Generated Quiz")

    doc = _get_document_for_generation(request, doc_id)
    if not doc:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
    if getattr(doc, "knowledge_base", "academic") != "academic":
        return Response(
            {"error": "Quiz generation is only supported for academic documents."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not doc.extracted_text:
        return Response({"error": "Document has no extracted text"}, status=status.HTTP_400_BAD_REQUEST)

    ai_request = AIRequest.objects.create(
        requested_by=request.user,
        document=doc,
        request_type="quiz",
        prompt=f"Generate {num_questions} questions at {difficulty} difficulty",
        model_used="llama3.2:3b",
        status="processing",
    )

    start_time = time.time()
    university_id = get_university_id(request.user)
    course_id = request.data.get("course_id") or doc.course_id
    questions_data = generate_quiz(
        doc.extracted_text,
        university_id=university_id,
        course_id=course_id,
        document_id=doc.id,
        num_questions=num_questions,
        difficulty=difficulty,
    )
    processing_time = time.time() - start_time

    if not questions_data:
        ai_request.status = "failed"
        ai_request.save()
        return Response({
            "error": (
                "Failed to generate quiz. Ollama may be busy on CPU-only mode. "
                "Try fewer questions (2-3) or wait 1-3 minutes and retry."
            )
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    existing_question_keys = set(
        Question.objects.filter(
            quiz__document=doc,
            quiz__created_by=request.user,
        ).annotate(
            q_norm=Lower("question_text")
        ).values_list("q_norm", flat=True)
    )

    filtered_questions = []
    for q in questions_data:
        q_text = (q.get("question") or "").strip()
        if not q_text:
            continue
        q_key = " ".join(q_text.lower().split())
        if q_key in existing_question_keys:
            continue
        existing_question_keys.add(q_key)
        filtered_questions.append(q)

    if not filtered_questions:
        used_questions = list(
            Question.objects.filter(
                quiz__document=doc,
                quiz__created_by=request.user,
            ).values_list("question_text", flat=True)
        )
        retry_questions = generate_quiz(
            doc.extracted_text,
            university_id=university_id,
            course_id=course_id,
            document_id=doc.id,
            num_questions=num_questions,
            difficulty=difficulty,
            excluded_questions=used_questions,
        )

        for q in retry_questions:
            q_text = (q.get("question") or "").strip()
            if not q_text:
                continue
            q_key = " ".join(q_text.lower().split())
            if q_key in existing_question_keys:
                continue
            existing_question_keys.add(q_key)
            filtered_questions.append(q)

    if not filtered_questions:
        ai_request.status = "failed"
        ai_request.save()
        return Response({
            "error": (
                "Generated questions were duplicates of existing quizzes for this document. "
                "Try a different difficulty or regenerate."
            )
        }, status=status.HTTP_409_CONFLICT)

    quiz = Quiz.objects.create(
        created_by=request.user,
        document=doc,
        title=title,
        difficulty=difficulty,
        is_ai_generated=True,
    )

    created_questions = []
    for i, q in enumerate(filtered_questions):
        question = Question.objects.create(
            quiz=quiz,
            question_text=q.get("question", ""),
            question_type="mcq",
            option_a=q.get("option_a", ""),
            option_b=q.get("option_b", ""),
            option_c=q.get("option_c", ""),
            option_d=q.get("option_d", ""),
            correct_answer=q.get("correct_answer", ""),
            explanation=q.get("explanation", ""),
            order=i + 1,
        )
        created_questions.append({
            "id": question.id,
            "question": question.question_text,
            "options": {
                "A": question.option_a,
                "B": question.option_b,
                "C": question.option_c,
                "D": question.option_d,
            },
            "correct_answer": question.correct_answer,
            "explanation": question.explanation,
        })

    ai_request.status = "completed"
    ai_request.processing_time_seconds = processing_time
    ai_request.save()

    return Response({
        "message": f"Quiz created with {len(created_questions)} questions!",
        "quiz_id": quiz.id,
        "title": quiz.title,
        "processing_time": round(processing_time, 2),
        "questions": created_questions,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def generate_exam_prep_view(request):
    """Generate exam prep slides from a document"""
    doc_id = request.data.get("document_id")

    doc = _get_document_for_generation(request, doc_id)
    if not doc:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
    if getattr(doc, "knowledge_base", "academic") != "academic":
        return Response(
            {"error": "Exam prep is only supported for academic documents."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    start_time = time.time()
    university_id = get_university_id(request.user)
    course_id = request.data.get("course_id") or doc.course_id
    summary = generate_summary(
        doc.extracted_text,
        university_id=university_id,
        course_id=course_id,
        document_id=doc.id,
    )
    processing_time = time.time() - start_time

    if not summary:
        return Response({"error": "Failed to generate summary"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    slide = ExamPrepSlide.objects.create(
        document=doc,
        created_by=request.user,
        title=summary.get("title", doc.title),
        content="\n".join(summary.get("key_points", [])),
        key_points="\n".join(summary.get("important_facts", [])),
        slide_order=1,
    )

    return Response({
        "message": "Exam prep slides generated!",
        "slide_id": slide.id,
        "title": slide.title,
        "processing_time": round(processing_time, 2),
        "key_points": summary.get("key_points", []),
        "important_facts": summary.get("important_facts", []),
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def extract_facts_view(request):
    """Extract key facts from a document"""
    doc_id = request.data.get("document_id")
    num_facts, num_facts_error = _parse_positive_int(request.data.get("num_facts"), "num_facts", 10)
    if num_facts_error:
        return Response({"error": num_facts_error}, status=status.HTTP_400_BAD_REQUEST)

    doc = _get_document_for_generation(request, doc_id)
    if not doc:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
    if getattr(doc, "knowledge_base", "academic") != "academic":
        return Response(
            {"error": "Fact extraction is only supported for academic documents."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    start_time = time.time()
    university_id = get_university_id(request.user)
    course_id = request.data.get("course_id") or doc.course_id
    facts_data = extract_facts(
        doc.extracted_text,
        university_id=university_id,
        course_id=course_id,
        document_id=doc.id,
        num_facts=num_facts,
    )
    processing_time = time.time() - start_time

    created_facts = []
    for fact in facts_data:
        concept_fact = ConceptFact.objects.create(
            document=doc,
            created_by=request.user,
            concept=fact.get("concept", ""),
            fact=fact.get("fact", ""),
            source_text=fact.get("source_text", ""),
        )
        created_facts.append({
            "id": concept_fact.id,
            "concept": concept_fact.concept,
            "fact": concept_fact.fact,
            "source_text": concept_fact.source_text,
        })

    return Response({
        "message": f"Extracted {len(created_facts)} facts!",
        "processing_time": round(processing_time, 2),
        "facts": created_facts,
    }, status=status.HTTP_201_CREATED)

@api_view(["GET"])
@permission_classes([AllowAny])
def ollama_status(request):
    """Check Ollama server health and configured model availability."""
    try:
        import requests as req
        from django.conf import settings

        tags_response = req.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=10)
        if tags_response.status_code != 200:
            return Response({
                "status": "offline",
                "model": settings.OLLAMA_MODEL,
                "message": f"Ollama health check failed with status code: {tags_response.status_code}",
            })

        payload = tags_response.json() or {}
        models = payload.get("models", [])
        installed_model_names = [model.get("name", "") for model in models if model.get("name")]
        model_available = settings.OLLAMA_MODEL in installed_model_names

        response_data = {
            "status": "online",
            "model": settings.OLLAMA_MODEL,
            "model_available": model_available,
        }
        if not model_available:
            response_data["message"] = (
                f"Configured model '{settings.OLLAMA_MODEL}' is not installed in Ollama."
            )
            response_data["installed_models"] = installed_model_names[:10]

        return Response(response_data)
    except Exception as e:
        fallback_model = "llama3.2:3b"
        configured_model = fallback_model
        if "settings" in locals():
            configured_model = getattr(settings, "OLLAMA_MODEL", fallback_model)
        return Response({
            "status": "offline",
            "model": configured_model,
            "message": str(e),
        })
# Create your views here.
@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def ask_question(request):
    """
    Core RAG Q&A - student asks question, AI answers from university docs ONLY
    """
    question = request.data.get("question")
    raw_course_id = request.data.get("course_id")
    raw_document_id = request.data.get("document_id")

    if not question:
        return Response({"error": "Question is required"}, status=status.HTTP_400_BAD_REQUEST)

    university_id = get_request_university_id(request, allow_tenant_fallback=False)

    if not university_id:
        return Response({
            "error": "You must be affiliated with a university to use this feature"
        }, status=status.HTTP_400_BAD_REQUEST)

    course_id, course_error = _parse_optional_int(raw_course_id, "course_id")
    if course_error:
        return Response({"error": course_error}, status=status.HTTP_400_BAD_REQUEST)
    if course_id and not Course.objects.filter(id=course_id, university_id=university_id).exists():
        return Response({"error": "course_id is invalid for your university"}, status=status.HTTP_400_BAD_REQUEST)

    document_id, doc_error = _parse_optional_int(raw_document_id, "document_id")
    if doc_error:
        return Response({"error": doc_error}, status=status.HTTP_400_BAD_REQUEST)
    if document_id and not Document.objects.filter(
        id=document_id,
        uploaded_by__profile__university_id=university_id,
    ).exists():
        return Response({"error": "document_id is invalid for your university"}, status=status.HTTP_400_BAD_REQUEST)

    cache_key = _qa_cache_key(
        university_id=university_id,
        question=question,
        course_id=course_id,
        document_id=document_id,
        knowledge_base="academic",
        visibility_scope=None,
    )
    cached_response = _fetch_cached_answer(cache_key)
    if cached_response:
        cached_response["university_id"] = university_id
        return Response(cached_response)

    ai_request = AIRequest.objects.create(
        requested_by=request.user,
        document_id=document_id or None,
        request_type="ask",
        prompt=question,
        model_used="llama3.2:3b",
        status="processing",
    )

    start_time = time.time()
    try:
        result = answer_question_rag(
            question,
            university_id,
            course_id,
            document_id=document_id,
            knowledge_base="academic",
        )
        processing_time = time.time() - start_time

        ai_request.status = "completed"
        ai_request.response = (result.get("answer", "") or "")[:4000]
        ai_request.processing_time_seconds = processing_time
        ai_request.save(update_fields=["status", "response", "processing_time_seconds"])
        _store_cached_answer(
            cache_key,
            {
                "question": question,
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "found_in_docs": result.get("found_in_docs", False),
            },
        )
    except Exception as exc:
        ai_request.status = "failed"
        ai_request.response = str(exc)[:4000]
        ai_request.processing_time_seconds = time.time() - start_time
        ai_request.save(update_fields=["status", "response", "processing_time_seconds"])
        return Response(
            {"error": "Failed to process question right now. Please retry."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"],
        "found_in_docs": result["found_in_docs"],
        "university_id": university_id,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def ask_university_info_public(request):
    """
    Public university information Q&A.
    Uses university_info knowledge base and only public documents.
    """
    question = request.data.get("question")
    university_id = request.data.get("university_id")
    if not question:
        return Response({"error": "Question is required"}, status=status.HTTP_400_BAD_REQUEST)

    if not university_id:
        tenant = getattr(request, "tenant_university", None)
        university_id = getattr(tenant, "id", None)

    if not university_id:
        return Response({"error": "university_id is required for public info lookup"}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(university_id, str):
        if not university_id.isdigit():
            return Response({"error": "university_id must be numeric"}, status=status.HTTP_400_BAD_REQUEST)
        university_id = int(university_id)

    university = University.objects.filter(id=university_id, is_active=True).first()
    if not university:
        return Response({"error": "University not found"}, status=status.HTTP_404_NOT_FOUND)
    if not university.allow_public_university_info:
        return Response({"error": "Public university info access is disabled for this tenant"}, status=403)

    cache_key = _qa_cache_key(
        university_id=university_id,
        question=question,
        knowledge_base="university_info",
        visibility_scope="public",
    )
    cached_response = _fetch_cached_answer(cache_key)
    if cached_response:
        cached_response["university_id"] = int(university_id)
        cached_response["knowledge_base"] = "university_info"
        cached_response["visibility_scope"] = "public"
        return Response(cached_response)

    result = answer_question_rag(
        question=question,
        university_id=university_id,
        course_id=None,
        document_id=None,
        knowledge_base="university_info",
        visibility_scope="public",
    )
    _store_cached_answer(
        cache_key,
        {
            "question": question,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "found_in_docs": result.get("found_in_docs", False),
        },
    )

    return Response({
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"],
        "found_in_docs": result["found_in_docs"],
        "university_id": int(university_id),
        "knowledge_base": "university_info",
        "visibility_scope": "public",
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsUniversityScopedAccess])
def ask_university_info_private(request):
    """
    Private university information Q&A for authenticated users.
    Uses university_info knowledge base and can read private+public docs.
    """
    question = request.data.get("question")
    if not question:
        return Response({"error": "Question is required"}, status=status.HTTP_400_BAD_REQUEST)

    university_id = get_request_university_id(request, allow_tenant_fallback=False)
    if not university_id:
        return Response({"error": "University affiliation is required"}, status=status.HTTP_400_BAD_REQUEST)

    cache_key = _qa_cache_key(
        university_id=university_id,
        question=question,
        knowledge_base="university_info",
        visibility_scope="private",
    )
    cached_response = _fetch_cached_answer(cache_key)
    if cached_response:
        cached_response["university_id"] = university_id
        cached_response["knowledge_base"] = "university_info"
        cached_response["visibility_scope"] = "private"
        return Response(cached_response)

    result = answer_question_rag(
        question=question,
        university_id=university_id,
        course_id=None,
        document_id=None,
        knowledge_base="university_info",
        visibility_scope=None,
    )
    _store_cached_answer(
        cache_key,
        {
            "question": question,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "found_in_docs": result.get("found_in_docs", False),
        },
    )

    return Response({
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"],
        "found_in_docs": result["found_in_docs"],
        "university_id": university_id,
        "knowledge_base": "university_info",
        "visibility_scope": "private",
    })

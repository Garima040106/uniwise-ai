import time
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_flashcards_view(request):
    """Generate flashcards from a document"""
    doc_id = request.data.get("document_id")
    num_cards = int(request.data.get("num_cards", 10))
    difficulty = request.data.get("difficulty", "medium")

    try:
        doc = Document.objects.get(id=doc_id, uploaded_by=request.user)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

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
@permission_classes([IsAuthenticated])
def generate_quiz_view(request):
    """Generate a quiz from a document"""
    doc_id = request.data.get("document_id")
    num_questions = int(request.data.get("num_questions", 5))
    difficulty = request.data.get("difficulty", "medium")
    title = request.data.get("title", "AI Generated Quiz")

    try:
        doc = Document.objects.get(id=doc_id, uploaded_by=request.user)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

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
@permission_classes([IsAuthenticated])
def generate_exam_prep_view(request):
    """Generate exam prep slides from a document"""
    doc_id = request.data.get("document_id")

    try:
        doc = Document.objects.get(id=doc_id, uploaded_by=request.user)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

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
@permission_classes([IsAuthenticated])
def extract_facts_view(request):
    """Extract key facts from a document"""
    doc_id = request.data.get("document_id")
    num_facts = int(request.data.get("num_facts", 10))

    try:
        doc = Document.objects.get(id=doc_id, uploaded_by=request.user)
    except Document.DoesNotExist:
        return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)

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
@permission_classes([IsAuthenticated])
def ask_question(request):
    """
    Core RAG Q&A - student asks question, AI answers from university docs ONLY
    """
    question = request.data.get("question")
    course_id = request.data.get("course_id")

    if not question:
        return Response({"error": "Question is required"}, status=status.HTTP_400_BAD_REQUEST)

    profile = getattr(request.user, "profile", None)
    university_id = profile.university.id if profile and profile.university else None

    if not university_id:
        return Response({
            "error": "You must be affiliated with a university to use this feature"
        }, status=status.HTTP_400_BAD_REQUEST)

    result = answer_question_rag(question, university_id, course_id)

    return Response({
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"],
        "found_in_docs": result["found_in_docs"],
        "university_id": university_id,
    })

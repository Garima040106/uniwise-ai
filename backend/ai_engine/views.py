import time
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from documents.models import Document
from flashcards.models import Flashcard
from quizzes.models import Quiz, Question
from .models import AIRequest, ExamPrepSlide, ConceptFact
from .utils import (
    generate_flashcards,
    generate_quiz,
    generate_summary,
    extract_facts,
    query_ollama,
)


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
    cards_data = generate_flashcards(doc.extracted_text, num_cards, difficulty)
    processing_time = time.time() - start_time

    if not cards_data:
        ai_request.status = "failed"
        ai_request.save()
        return Response({"error": "Failed to generate flashcards"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    questions_data = generate_quiz(doc.extracted_text, num_questions, difficulty)
    processing_time = time.time() - start_time

    if not questions_data:
        ai_request.status = "failed"
        ai_request.save()
        return Response({"error": "Failed to generate quiz"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    quiz = Quiz.objects.create(
        created_by=request.user,
        document=doc,
        title=title,
        difficulty=difficulty,
        is_ai_generated=True,
    )

    created_questions = []
    for i, q in enumerate(questions_data):
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
    summary = generate_summary(doc.extracted_text)
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
    facts_data = extract_facts(doc.extracted_text, num_facts)
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
@permission_classes([IsAuthenticated])
def ollama_status(request):
    """Check if Ollama is running"""
    response = query_ollama("Say 'OK' and nothing else.")
    if "Error" in response:
        return Response({"status": "offline", "message": response})
    return Response({"status": "online", "model": "llama3.2:3b", "response": response})
# Create your views here.

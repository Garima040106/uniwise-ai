from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import date, timedelta
from .models import Flashcard, FlashcardReview


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_flashcards(request):
    """List all flashcards for current user"""
    difficulty = request.GET.get("difficulty")
    flashcards = Flashcard.objects.filter(created_by=request.user)
    if difficulty:
        flashcards = flashcards.filter(difficulty=difficulty)
    data = [{
        "id": f.id,
        "question": f.question,
        "answer": f.answer,
        "difficulty": f.difficulty,
        "is_ai_generated": f.is_ai_generated,
        "created_at": f.created_at,
    } for f in flashcards]
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def flashcards_due_today(request):
    """Get flashcards due for review today (spaced repetition)"""
    today = date.today()
    reviewed_ids = FlashcardReview.objects.filter(
        user=request.user,
        next_review_date__gt=today,
    ).values_list("flashcard_id", flat=True)

    due_cards = Flashcard.objects.filter(
        created_by=request.user
    ).exclude(id__in=reviewed_ids)

    data = [{
        "id": f.id,
        "question": f.question,
        "answer": f.answer,
        "difficulty": f.difficulty,
    } for f in due_cards]

    return Response({
        "due_today": len(data),
        "flashcards": data,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def review_flashcard(request, card_id):
    """
    Submit a flashcard review with spaced repetition
    Rating: 1=Again, 2=Hard, 3=Good, 4=Easy
    """
    try:
        flashcard = Flashcard.objects.get(id=card_id, created_by=request.user)
    except Flashcard.DoesNotExist:
        return Response({"error": "Flashcard not found"}, status=status.HTTP_404_NOT_FOUND)

    rating = int(request.data.get("rating", 3))

    # Spaced repetition intervals based on rating
    intervals = {1: 1, 2: 3, 3: 7, 4: 14}
    interval_days = intervals.get(rating, 7)
    next_review = date.today() + timedelta(days=interval_days)

    review = FlashcardReview.objects.create(
        user=request.user,
        flashcard=flashcard,
        rating=rating,
        next_review_date=next_review,
        interval_days=interval_days,
    )

    return Response({
        "message": "Review recorded!",
        "next_review_date": next_review,
        "interval_days": interval_days,
    })


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_flashcard(request, card_id):
    """Delete a flashcard"""
    try:
        flashcard = Flashcard.objects.get(id=card_id, created_by=request.user)
        flashcard.delete()
        return Response({"message": "Flashcard deleted"})
    except Flashcard.DoesNotExist:
        return Response({"error": "Flashcard not found"}, status=status.HTTP_404_NOT_FOUND)
# Create your views here.

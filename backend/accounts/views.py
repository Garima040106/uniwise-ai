from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from .models import UserProfile, University


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
    username = request.data.get("username")
    email = request.data.get("email")
    password = request.data.get("password")
    university_id = request.data.get("university_id")
    field_of_study = request.data.get("field_of_study", "")
    year_of_study = request.data.get("year_of_study", 1)

    if not all([username, email, password]):
        return Response({"error": "Username, email and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, email=email, password=password)

    profile = UserProfile.objects.create(
        user=user,
        university_id=university_id,
        field_of_study=field_of_study,
        year_of_study=year_of_study,
    )

    return Response({
        "message": "Account created successfully!",
        "user_id": user.id,
        "username": user.username,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """Login user"""
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        profile = getattr(user, "profile", None)
        return Response({
            "message": "Login successful!",
            "user_id": user.id,
            "username": user.username,
            "university": profile.university.name if profile and profile.university else None,
        })
    return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """Logout user"""
    logout(request)
    return Response({"message": "Logged out successfully!"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    """Get current user profile"""
    user = request.user
    profile = getattr(user, "profile", None)
    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "university": profile.university.name if profile and profile.university else None,
        "field_of_study": profile.field_of_study if profile else "",
        "year_of_study": profile.year_of_study if profile else 1,
        "learning_pace": profile.learning_pace if profile else "medium",
    })


@api_view(["GET"])
@permission_classes([AllowAny])
def list_universities(request):
    """List all universities"""
    universities = University.objects.all()
    data = [{"id": u.id, "name": u.name, "country": u.country} for u in universities]
    return Response(data)
# Create your views here.

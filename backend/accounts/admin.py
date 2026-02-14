from django.contrib import admin
from .models import University, UserProfile

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "erp_system", "created_at"]
    search_fields = ["name", "country"]

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "university", "year_of_study", "field_of_study", "learning_pace"]
    search_fields = ["user__username", "university__name"]
    list_filter = ["learning_pace", "year_of_study"]
# Register your models here.

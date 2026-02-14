from django.contrib import admin
from .models import Course, Subject, Topic

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "university", "year", "semester"]
    search_fields = ["name", "code"]
    list_filter = ["year", "university"]

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["name", "course", "order"]
    search_fields = ["name"]

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "order"]
    search_fields = ["name"]
# Register your models here.

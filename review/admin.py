# review/admin.py
from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "reviewer", "reviewee", "role", "rating", "created_at")
    list_filter = ("role", "rating", "created_at")
    search_fields = ("reviewer__username", "reviewee__username", "task__title")
    ordering = ("-created_at",)

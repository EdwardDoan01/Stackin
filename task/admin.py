from django.contrib import admin
from .models import Category, TaskerSkill, Task, TaskAttachment, TaskEvent, TaskQR


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "parent", "is_active", "sort_order", "created_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    ordering = ("parent", "sort_order", "name")
    prepopulated_fields = {"slug": ("name",)}  # chỉ hỗ trợ nhập nhanh, không đổi model


@admin.register(TaskerSkill)
class TaskerSkillAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "experience_level", "is_primary", "created_at")
    list_filter = ("experience_level", "category", "is_primary")
    search_fields = ("user__username", "category__name")
    ordering = ("-created_at",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "client", "tasker", "category", "status",
        "price", "currency", "posted_at", "created_at"
    )
    list_filter = ("status", "category", "currency")
    search_fields = ("title", "description", "client__username", "tasker__username")
    ordering = ("-created_at",)


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "file", "uploaded_at")
    search_fields = ("task__title",)
    ordering = ("-uploaded_at",)


@admin.register(TaskEvent)
class TaskEventAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "actor", "event", "from_status", "to_status", "created_at")
    list_filter = ("event", "from_status", "to_status")
    search_fields = ("task__title", "actor__username", "note")
    ordering = ("-created_at",)


@admin.register(TaskQR)
class TaskQRAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "code", "is_used", "created_at")
    list_filter = ("is_used",)
    search_fields = ("task__title", "task__id", "code")
    ordering = ("-created_at",)

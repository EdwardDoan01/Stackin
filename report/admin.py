# report/admin.py
from django.contrib import admin
from .models import Report, ReportAttachment, ReportEvent


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("id", "type", "title", "reporter", "reported_user", "task", "status", "severity", "created_at")
    list_filter = ("type", "status", "severity", "category")
    search_fields = ("title", "description", "reporter__username", "reported_user__username", "task__title")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "handled_at")


@admin.register(ReportAttachment)
class ReportAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "file", "uploaded_at")
    ordering = ("-uploaded_at",)


@admin.register(ReportEvent)
class ReportEventAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "actor", "event", "from_status", "to_status", "created_at")
    ordering = ("-created_at",)

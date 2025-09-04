# report/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Q, F, UniqueConstraint

from task.models import Task


class Report(models.Model):
    class ReportType(models.TextChoices):
        CLIENT = "CLIENT", "Report Client"
        TASKER = "TASKER", "Report Tasker"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        RESOLVED_UPHELD = "RESOLVED_UPHELD", "Resolved (Upheld)"
        RESOLVED_REJECTED = "RESOLVED_REJECTED", "Resolved (Rejected)"
        CANCELLED = "CANCELLED", "Cancelled"

    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Category(models.TextChoices):
        CONDUCT = "conduct", "Conduct / Behavior"
        HARASSMENT = "harassment", "Harassment / Abuse"
        SPAM = "spam", "Spam / Scam"
        FRAUD = "fraud", "Fraud / Payment"
        QUALITY = "quality", "Poor Quality"
        NO_SHOW = "no_show", "No show / Late"
        SAFETY = "safety", "Safety Issue"
        OTHER = "other", "Other"

    id = models.BigAutoField(primary_key=True)

    # ngữ cảnh
    type = models.CharField(max_length=12, choices=ReportType.choices)
    task = models.ForeignKey(
        Task, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports"
    )

    # chủ thể
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_made"
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports_received"
    )

    # nội dung
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # trạng thái xử lý
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_note = models.TextField(blank=True)        # ghi chú nội bộ trong quá trình review
    resolution_note = models.TextField(blank=True)   # kết luận cuối cùng

    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reports_handled"
    )
    handled_at = models.DateTimeField(null=True, blank=True)

    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "report"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task", "status"]),
            models.Index(fields=["reporter"]),
            models.Index(fields=["reported_user"]),
            models.Index(fields=["type"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            # Không cho report chính mình
            models.CheckConstraint(
                check=~Q(reporter=F("reported_user")),
                name="report_reporter_not_target",
            ),
            # Chỉ 1 report 'đang mở' cho cùng (reporter, reported_user, task, type)
            UniqueConstraint(
                fields=["reporter", "reported_user", "task", "type"],
                condition=Q(status__in=["PENDING", "UNDER_REVIEW"]),
                name="uniq_open_report_per_pair_task_type",
            ),
        ]

    def __str__(self):
        return f"Report#{self.id} {self.type} {self.status}"


class ReportAttachment(models.Model):
    id = models.BigAutoField(primary_key=True)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="report/files/")
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "report_attachment"
        indexes = [
            models.Index(fields=["report", "-uploaded_at"]),
        ]

    def __str__(self):
        return f"Attachment#{self.id} for Report#{self.report_id}"


class ReportEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        STATUS_CHANGED = "status_changed", "Status Changed"
        NOTE_ADDED = "note_added", "Note Added"

    id = models.BigAutoField(primary_key=True)
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="report_events"
    )
    event = models.CharField(max_length=32, choices=EventType.choices)
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20, blank=True)
    note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "report_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["report", "-created_at"]),
            models.Index(fields=["event"]),
        ]

    def __str__(self):
        return f"{self.event} on Report {self.report_id} at {self.created_at:%Y-%m-%d %H:%M:%S}"

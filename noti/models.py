# noti/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from task.models import Task
from payment.models import Payment

class Notification(models.Model):
    class Type(models.TextChoices):
        TASK = "TASK", "Task"
        PAYMENT = "PAYMENT", "Payment"
        SYSTEM = "SYSTEM", "System"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In-App"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        PUSH = "push", "Push"

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.SYSTEM)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)

    # Bổ sung để đồng bộ với serializer/views
    is_archived = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    task = models.ForeignKey(Task, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")

    category = models.CharField(max_length=50, null=True, blank=True)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.NORMAL)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.IN_APP)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["type"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["category"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Noti#{self.id} to {self.user.username} {self.type} {self.title}"

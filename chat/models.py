# chat/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from task.models import Task


class ChatRoom(models.Model):
    """
    Mỗi Task có một ChatRoom để client và tasker trao đổi.
    """
    id = models.BigAutoField(primary_key=True)
    task = models.OneToOneField(
        Task,
        on_delete=models.CASCADE,
        related_name="chat_room",
        help_text="Chat room này gắn với Task"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_room"
        verbose_name = "Chat Room"
        verbose_name_plural = "Chat Rooms"

    def __str__(self):
        return f"ChatRoom for Task#{self.task_id}"


class ChatMessage(models.Model):
    class MessageType(models.TextChoices):
        TEXT = "TEXT", "Text"
        FILE = "FILE", "File"
        SYSTEM = "SYSTEM", "System"

    id = models.BigAutoField(primary_key=True)
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages_sent"
    )
    message_type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    content = models.TextField(blank=True, null=True, help_text="Nội dung text hoặc mô tả file")
    file = models.FileField(upload_to="chat/files/", blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "chat_message"
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"
        ordering = ["created_at"]

        indexes = [
            models.Index(fields=["room", "created_at"]),
            models.Index(fields=["sender"]),
        ]

    def __str__(self):
        return f"Msg#{self.id} in Room#{self.room_id} by {self.sender_id}"

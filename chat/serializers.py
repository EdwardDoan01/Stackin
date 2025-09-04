# chat/serializers.py
from rest_framework import serializers
from .models import ChatRoom, ChatMessage
from user.serializers import UserSerializer  # tái sử dụng
from task.serializers import TaskListSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    message_type_display = serializers.CharField(
        source="get_message_type_display", read_only=True
    )

    class Meta:
        model = ChatMessage
        fields = [
            "id",
            "room",
            "sender",
            "message_type",
            "message_type_display",
            "content",
            "file",
            "metadata",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "room",
            "sender",
            "message_type_display",
            "is_read",
            "read_at",
            "created_at",
        ]


class ChatRoomSerializer(serializers.ModelSerializer):
    task = TaskListSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    client = serializers.SerializerMethodField()
    tasker = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            "id",
            "task",
            "client",
            "tasker",
            "last_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_last_message(self, obj):
        msg = obj.messages.order_by("-created_at").first()
        if msg:
            return ChatMessageSerializer(msg).data
        return None

    def get_client(self, obj):
        return UserSerializer(obj.task.client).data if obj.task.client else None

    def get_tasker(self, obj):
        return UserSerializer(obj.task.tasker).data if obj.task.tasker else None

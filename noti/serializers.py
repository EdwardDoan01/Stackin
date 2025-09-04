# noti/serializers.py
from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "user",
            "type",
            "type_display",
            "title",
            "message",
            "task",
            "payment",
            "category",
            "priority",
            "priority_display",
            "channel",
            "channel_display",
            "is_read",
            "is_archived",
            "metadata",
            "created_at",
            "updated_at",
            "read_at",
        ]
        read_only_fields = [
            "id",
            "type_display",
            "priority_display",
            "channel_display",
            "created_at",
            "updated_at",
            "read_at",
        ]

class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "user",
            "type",
            "title",
            "message",
            "task",
            "payment",
            "category",
            "priority",
            "channel",
            "metadata",
        ]
        # is_read/is_archived được set mặc định qua model → không nhận từ client
        read_only_fields = []

class NotificationStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["is_read", "is_archived"]

from rest_framework import serializers
from .models import ChatMessage, ChatbotSuggestion

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'message', 'response', 'timestamp', 'session_id']
        read_only_fields = ['id', 'timestamp']

class ChatbotSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotSuggestion
        fields = ['id', 'title', 'description', 'category']
        read_only_fields = ['id']

class ChatbotMessageSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=1000)
    session_id = serializers.CharField(max_length=100, required=False, allow_blank=True)

from django.contrib import admin
from .models import ChatMessage, ChatbotSuggestion

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'message_preview', 'response_preview', 'timestamp', 'session_id']
    list_filter = ['timestamp', 'user']
    search_fields = ['message', 'response', 'user__username', 'user__email']
    readonly_fields = ['timestamp']
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def response_preview(self, obj):
        return obj.response[:50] + '...' if len(obj.response) > 50 else obj.response
    response_preview.short_description = 'Response'

@admin.register(ChatbotSuggestion)
class ChatbotSuggestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_active', 'order']
    list_filter = ['category', 'is_active']
    search_fields = ['title', 'description']
    list_editable = ['is_active', 'order']
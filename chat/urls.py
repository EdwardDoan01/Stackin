# chat/urls.py
from django.urls import path
from .views import (
    # ChatRoom Views
    ChatRoomListView,
    ChatRoomDetailView,

    # ChatMessage Views
    ChatMessageListView,
    ChatMessageCreateView,
    ChatMessageMarkReadView,
)

urlpatterns = [
    # ===============================
    # ChatRoom Endpoints
    # ===============================
    path("rooms/", ChatRoomListView.as_view(), name="chatroom-list"),
    path("rooms/<int:pk>/", ChatRoomDetailView.as_view(), name="chatroom-detail"),

    # ===============================
    # ChatMessage Endpoints
    # ===============================
    path("rooms/<int:room_id>/messages/", ChatMessageListView.as_view(), name="chatmessage-list"),
    path("rooms/<int:room_id>/messages/send/", ChatMessageCreateView.as_view(), name="chatmessage-create"),
    path("messages/<int:pk>/read/", ChatMessageMarkReadView.as_view(), name="chatmessage-mark-read"),
]

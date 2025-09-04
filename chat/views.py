# chat/views.py
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import ChatRoom, ChatMessage
from .serializers import ChatRoomSerializer, ChatMessageSerializer
from .permissions import IsRoomParticipant


# ================================
# ChatRoom Views
# ================================
class ChatRoomListView(generics.ListAPIView):
    """
    Danh sách tất cả chat room mà user hiện tại tham gia.
    (Lấy ra từ các task mà user là client hoặc tasker).
    """
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return ChatRoom.objects.select_related("task__client", "task__tasker").filter(
            Q(task__client=user) | Q(task__tasker=user)
        ).order_by("-updated_at")


class ChatRoomDetailView(generics.RetrieveAPIView):
    """
    Xem chi tiết 1 chat room (bao gồm last_message, client, tasker).
    """
    queryset = ChatRoom.objects.select_related("task__client", "task__tasker")
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated, IsRoomParticipant]

    def get_object(self):
        obj = get_object_or_404(ChatRoom, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj


# ================================
# ChatMessage Views
# ================================
class ChatMessageListView(generics.ListAPIView):
    """
    Danh sách tin nhắn trong 1 room.
    Hỗ trợ phân trang (limit/offset hoặc page).
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsRoomParticipant]

    def get_queryset(self):
        room = get_object_or_404(ChatRoom, pk=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)
        return room.messages.select_related("sender").order_by("-created_at")


class ChatMessageCreateView(generics.CreateAPIView):
    """
    Gửi một tin nhắn mới trong room.
    - sender = request.user
    - room lấy từ URL param
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsRoomParticipant]

    def perform_create(self, serializer):
        room = get_object_or_404(ChatRoom, pk=self.kwargs["room_id"])
        self.check_object_permissions(self.request, room)

        msg = serializer.save(
            room=room,
            sender=self.request.user,
            created_at=timezone.now(),
        )

        # Cập nhật updated_at cho room
        room.updated_at = timezone.now()
        room.save(update_fields=["updated_at"])

        # TODO: push Notification cho người kia
        return msg


class ChatMessageMarkReadView(APIView):
    """
    Đánh dấu 1 message là đã đọc.
    """
    permission_classes = [permissions.IsAuthenticated, IsRoomParticipant]

    def post(self, request, pk):
        msg = get_object_or_404(ChatMessage, pk=pk)
        self.check_object_permissions(request, msg.room)

        if msg.sender_id == request.user.id:
            return Response({"error": "Cannot mark your own message as read"}, status=status.HTTP_400_BAD_REQUEST)

        msg.is_read = True
        msg.read_at = timezone.now()
        msg.save(update_fields=["is_read", "read_at"])
        return Response({"message": "Marked as read"}, status=status.HTTP_200_OK)

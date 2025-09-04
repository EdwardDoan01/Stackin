# chat/permissions.py
from typing import Optional

from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.shortcuts import get_object_or_404

from .models import ChatRoom, ChatMessage
from task.models import Task


def _is_participant(task: Task, user) -> bool:
    """
    User là participant hợp lệ nếu là client hoặc tasker của task.
    """
    if not user or not user.is_authenticated:
        return False
    return user.id in {task.client_id, task.tasker_id}


def _chat_allowed(task: Task) -> bool:
    """
    Task còn hợp lệ để chat.
    - Không cho chat khi Cancelled/Expired.
    - Cho chat ở các trạng thái còn lại (đặc biệt sau khi đã assign).
    """
    banned = {
        Task.Status.CANCELLED_BY_CLIENT,
        Task.Status.CANCELLED_BY_TASKER,
        Task.Status.CANCELLED_BY_SYSTEM,
        Task.Status.EXPIRED,
    }
    return task.status not in banned


def _get_room_from_view(view, request) -> Optional[ChatRoom]:
    """
    Cố gắng suy ra ChatRoom từ:
    - URL kwarg: pk hoặc room_id
    - Query param: room
    - Body: room
    Trả về None nếu không xác định được (ví dụ endpoint dạng /rooms/ list).
    """
    room_id = (
        view.kwargs.get("pk")
        or view.kwargs.get("room_id")
        or request.query_params.get("room")
        or (request.data.get("room") if isinstance(request.data, dict) else None)
    )
    if not room_id:
        return None
    try:
        return ChatRoom.objects.select_related("task__client", "task__tasker").get(pk=room_id)
    except ChatRoom.DoesNotExist:
        return None


class IsRoomParticipant(BasePermission):
    """
    Quyền xem/đọc room và messages trong room:
      - Admin (is_staff) luôn được phép.
      - Chỉ client/tasker của task gắn với room mới được vào phòng.
      - Ngoài ra, task phải còn “hợp lệ để chat” (không bị cancel/expired).
    Gợi ý gắn cho:
      - ChatRoom detail
      - Message list by room
      - Any read-only operations inside a room
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True

        # Với các endpoint không có room cụ thể (vd: /rooms/ list), cho phép;
        # view cần filter theo request.user ở queryset (avoid data leak).
        room = _get_room_from_view(view, request)
        if room is None:
            return True

        task = room.task
        # Nếu task chưa có tasker -> vẫn cho CLient xem phòng (để hiển thị UI),
        # nhưng thường app của bạn tạo room khi đã assign. Tuỳ policy, ở đây cho phép
        # participant vào nhưng _chat_allowed_ mới chặn action gửi tin.
        return _is_participant(task, request.user) and _chat_allowed(task)

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True

        if isinstance(obj, ChatRoom):
            task = obj.task
        elif isinstance(obj, ChatMessage):
            task = obj.room.task
        else:
            return False

        return _is_participant(task, request.user) and _chat_allowed(task)


class CanSendChatMessage(BasePermission):
    """
    Quyền gửi tin nhắn:
      - Admin luôn được.
      - User phải là participant của room.
      - Task phải còn hợp lệ để chat (không bị cancel/expired).
      - Task phải có tasker (đảm bảo chat là 1–1 sau khi đã assign).
    Gợi ý gắn cho endpoint POST /messages/ (create).
    """

    def has_permission(self, request, view):
        if request.method not in ("POST",):
            return True  # Chỉ xét cho create
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True

        room = _get_room_from_view(view, request)
        if room is None:
            # Nếu endpoint nhận task_id và tự suy ra room, hãy điều chỉnh lại logic lấy room ở view.
            return False

        task = room.task
        if not _is_participant(task, request.user):
            return False
        if not _chat_allowed(task):
            return False
        # Bắt buộc phải có tasker (tránh client “tự chat” khi chưa có tasker)
        if task.tasker_id is None:
            return False
        return True


class CanMarkMessageRead(BasePermission):
    """
    Quyền đánh dấu đã đọc tin nhắn:
      - Admin luôn được.
      - User phải là participant và KHÔNG phải là sender (tức là người nhận).
    Gợi ý gắn cho endpoint POST /messages/<id>/read
    """

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, ChatMessage):
            return False
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True

        task = obj.room.task
        if not _is_participant(task, request.user):
            return False
        # Người nhận mới có quyền mark read
        return obj.sender_id != request.user.id


class IsMessageSenderOrAdmin(BasePermission):
    """
    Quyền sửa/xoá tin nhắn (nếu bạn hỗ trợ):
      - Admin luôn được.
      - Chỉ sender của message mới được.
    """

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, ChatMessage):
            return False
        if request.user.is_staff:
            return True
        return obj.sender_id == request.user.id

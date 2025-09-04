# noti/views.py
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationCreateSerializer,
    NotificationStatusUpdateSerializer,
)
from .permissions import IsOwnerOfNotification, IsSystemOrAdmin


def _parse_bool(value, default=None):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in ("1", "true", "t", "yes", "y"):
        return True
    if s in ("0", "false", "f", "no", "n"):
        return False
    return default


# =========================
# USER-SCOPE: LIST & DETAIL
# =========================
class NotificationListView(generics.ListAPIView):
    """
    Danh sách notification của chính user đang đăng nhập.
    Hỗ trợ filter qua query params:
      - is_read=[true|false]
      - is_archived=[true|false]
      - category=<slug/enum>
      - priority=[low|normal|high]
    Mặc định: sắp xếp -created_at (mới nhất trước).
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.select_related("user").filter(user=self.request.user)

        # Filters
        is_read = _parse_bool(self.request.query_params.get("is_read"))
        if is_read is not None:
            qs = qs.filter(is_read=is_read)

        is_archived = _parse_bool(self.request.query_params.get("is_archived"))
        if is_archived is not None:
            qs = qs.filter(is_archived=is_archived)

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)

        priority = self.request.query_params.get("priority")
        if priority:
            qs = qs.filter(priority=priority)

        return qs.order_by("-created_at")


class NotificationDetailView(generics.RetrieveAPIView):
    """
    Xem chi tiết 1 notification của chính mình.
    """
    queryset = Notification.objects.select_related("user")
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfNotification]

    def get_object(self):
        obj = get_object_or_404(Notification, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj


# =========================
# USER-SCOPE: STATUS ACTIONS
# =========================
class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfNotification]

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk)
        self.check_object_permissions(request, notif)

        read = _parse_bool(request.data.get("read"))
        if read is None:
            return Response({"error": "Missing or invalid 'read' flag"}, status=status.HTTP_400_BAD_REQUEST)

        notif.is_read = bool(read)
        notif.read_at = timezone.now() if notif.is_read else None
        notif.save(update_fields=["is_read", "read_at", "updated_at"])
        return Response({"message": "Updated", "is_read": notif.is_read}, status=status.HTTP_200_OK)



class NotificationArchiveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfNotification]

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk)
        self.check_object_permissions(request, notif)

        archived = _parse_bool(request.data.get("archived"))
        if archived is None:
            return Response({"error": "Missing or invalid 'archived' flag"}, status=status.HTTP_400_BAD_REQUEST)

        notif.is_archived = bool(archived)
        notif.save(update_fields=["is_archived", "updated_at"])
        return Response({"message": "Updated", "is_archived": notif.is_archived}, status=status.HTTP_200_OK)


class NotificationBulkMarkReadView(APIView):
    """
    Đánh dấu tất cả (hoặc theo filter) là đã đọc cho user hiện tại.
    Query params tùy chọn:
      - category=<...>
      - include_archived=true|false (default: false)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        qs = Notification.objects.filter(user=request.user, is_read=False)

        include_archived = _parse_bool(request.query_params.get("include_archived"), default=False)
        if not include_archived:
            qs = qs.filter(is_archived=False)

        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)

        updated = qs.update(is_read=True, read_at=timezone.now())
        return Response({"updated": updated}, status=status.HTTP_200_OK)


class NotificationUnreadCountView(APIView):
    """
    Đếm số notification chưa đọc (mặc định bỏ qua archived).
    Query param: include_archived=true|false (default: false)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        include_archived = _parse_bool(request.query_params.get("include_archived"), default=False)
        qs = Notification.objects.filter(user=request.user, is_read=False)
        if not include_archived:
            qs = qs.filter(is_archived=False)
        return Response({"unread": qs.count()}, status=status.HTTP_200_OK)


# =========================
# ADMIN/SYSTEM: CREATE & BROADCAST
# =========================
class NotificationCreateView(generics.CreateAPIView):
    """
    Tạo 1 notification cho 1 user (chỉ Admin/System).
    """
    queryset = Notification.objects.select_related("user")
    serializer_class = NotificationCreateSerializer
    permission_classes = [permissions.IsAuthenticated, IsSystemOrAdmin]


class NotificationBroadcastView(APIView):
    """
    Body:
    {
      "user_ids": [1,2,3],
      "title": "...",
      "message": "...",
      "category": "task|payment|system|...",
      "channel": "in_app|email|sms|push",
      "priority": "low|normal|high",
      "metadata": {...},
      "task": <task_id?>,
      "payment": <payment_id?>
    }
    """
    permission_classes = [permissions.IsAuthenticated, IsSystemOrAdmin]

    def post(self, request):
        payload = request.data or {}
        user_ids = payload.get("user_ids")
        if not isinstance(user_ids, list) or not user_ids:
            return Response({"error": "user_ids must be a non-empty list"}, status=status.HTTP_400_BAD_REQUEST)

        proto_data = {
            key: payload.get(key)
            for key in ["type", "title", "message", "task", "payment", "category", "priority", "channel", "metadata"]
            if key in payload
        }
        # Validate shared fields with serializer (without user)
        proto = NotificationCreateSerializer(data=proto_data)
        proto.is_valid(raise_exception=True)
        vd = proto.validated_data

        notifs = []
        now = timezone.now()
        for uid in user_ids:
            notifs.append(
                Notification(
                    user_id=uid,
                    type=vd.get("type", Notification.Type.SYSTEM),
                    title=vd["title"],
                    message=vd.get("message", ""),
                    task=vd.get("task"),
                    payment=vd.get("payment"),
                    category=vd.get("category"),
                    channel=vd.get("channel", Notification.Channel.IN_APP),
                    priority=vd.get("priority", Notification.Priority.NORMAL),
                    metadata=vd.get("metadata", {}),
                    created_at=now,
                    updated_at=now,
                )
            )

        Notification.objects.bulk_create(notifs, batch_size=500)
        return Response({"created": len(notifs)}, status=status.HTTP_201_CREATED)


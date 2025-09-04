from rest_framework import permissions
from .models import Notification


class IsOwnerOfNotification(permissions.BasePermission):
    """
    Chỉ cho phép user truy cập vào notification của chính mình.
    Admin thì có thể truy cập mọi notification.
    """

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Notification):
            # Admin có toàn quyền
            if request.user and request.user.is_staff:
                return True
            # Chỉ chủ sở hữu notification được quyền
            return obj.user == request.user
        return False


class IsSystemOrAdmin(permissions.BasePermission):
    """
    Cho phép thực hiện các hành động hệ thống (tạo/sync notification).
    Thường chỉ dùng cho admin hoặc background service.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_staff

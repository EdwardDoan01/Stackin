# report/permissions.py
from rest_framework import permissions
from .models import Report


class CanCreateReport(permissions.BasePermission):
    """
    Cho phép tạo report khi authenticated.
    Validation chi tiết nằm ở serializer.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsReportOwnerOrAdmin(permissions.BasePermission):
    """
    Chỉ owner (reporter) hoặc reported_user hoặc admin mới xem report chi tiết.
    """
    def has_object_permission(self, request, view, obj: Report):
        if request.user and request.user.is_staff:
            return True
        return obj.reporter_id == request.user.id or obj.reported_user_id == request.user.id


class IsStaffForModeration(permissions.BasePermission):
    """
    Chỉ staff (is_staff) mới có quyền thay đổi trạng thái / xử lý report.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff

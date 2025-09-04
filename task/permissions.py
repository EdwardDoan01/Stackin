from rest_framework.permissions import BasePermission, SAFE_METHODS
from user.models import TaskerRegistration


class IsClient(BasePermission):
    """
    Chỉ cho phép client (user thường, không phải tasker) thực hiện hành động này.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and not request.user.is_tasker


class IsTaskOwner(BasePermission):
    """
    Chỉ cho phép client chủ sở hữu task thực hiện action.
    """
    def has_object_permission(self, request, view, obj):
        return obj.client_id == request.user.id


class IsTasker(BasePermission):
    """
    Chỉ cho phép user là tasker (is_tasker = True).
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_tasker


class IsApprovedTasker(BasePermission):
    """
    Chỉ cho phép tasker đã được admin duyệt.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated or not user.is_tasker:
            return False
        try:
            reg = TaskerRegistration.objects.get(user=user)
            return reg.status == "approved"
        except TaskerRegistration.DoesNotExist:
            return False


class IsAssignedTasker(BasePermission):
    """
    Chỉ cho phép tasker đã được assign vào task đó.
    """
    def has_object_permission(self, request, view, obj):
        return obj.tasker_id == request.user.id


class ReadOnly(BasePermission):
    """
    Cho phép chỉ đọc (GET, HEAD, OPTIONS).
    """
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS

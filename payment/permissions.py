from rest_framework import permissions
from .models import Payment, PaymentIntent
from task.models import Task

class IsClientOfTask(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, PaymentIntent):
            return obj.client == request.user
        elif isinstance(obj, Payment):
            return obj.client == request.user
        return False


class IsTaskerOfTask(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Payment):
            return obj.tasker == request.user
        return False


class IsPlatformAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class IsClientOfTaskForIntent(permissions.BasePermission):
    """
    Kiểm tra user có phải là client của task khi tạo PaymentIntent
    """
    def has_permission(self, request, view):
        task_id = request.data.get("task")
        if not task_id:
            return False
        return Task.objects.filter(id=task_id, client=request.user).exists()

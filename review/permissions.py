# review/permissions.py
from rest_framework import permissions
from task.models import Task
from .models import Review


class CanCreateReview(permissions.BasePermission):
    """
    Quyền tạo review:
      - Nếu role=CLIENT: chỉ client của task được review tasker.
      - Nếu role=TASKER: chỉ tasker của task được review client.
      - Task phải ở trạng thái COMPLETED hoặc CLIENT_CONFIRMED.
      - Admin (is_staff) bypass mọi check.
    """

    def has_permission(self, request, view):
        # Chỉ áp dụng cho action create
        if request.method != "POST":
            return True

        if request.user and request.user.is_staff:
            return True  # Admin có toàn quyền

        data = request.data or {}
        task_id = data.get("task")
        role = data.get("role")

        if not task_id or not role:
            return False

        try:
            task = Task.objects.get(pk=task_id)
        except Task.DoesNotExist:
            return False

        # Task phải hoàn tất
        if task.status not in [Task.Status.COMPLETED, Task.Status.CLIENT_CONFIRMED]:
            return False

        # Role-specific check
        if role == Review.Role.CLIENT:
            # Reviewer phải là client
            return task.client_id == request.user.id and task.tasker_id is not None

        elif role == Review.Role.TASKER:
            # Reviewer phải là tasker
            return task.tasker_id == request.user.id

        return False


class CanViewReview(permissions.BasePermission):
    """
    Quyền xem review:
      - Reviewer hoặc Reviewee có thể xem review của mình.
      - Admin (is_staff) có thể xem tất cả.
    """

    def has_object_permission(self, request, view, obj: Review):
        if request.user and request.user.is_staff:
            return True
        return obj.reviewer_id == request.user.id or obj.reviewee_id == request.user.id

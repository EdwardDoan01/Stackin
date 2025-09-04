from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Category, Task, TaskerSkill, TaskAttachment, TaskEvent
from .serializers import (
    CategorySerializer,
    TaskCreateUpdateSerializer,
    TaskListSerializer,
    TaskDetailSerializer,
    TaskerSkillSerializer,
    TaskAttachmentSerializer,
    TaskEventSerializer
)
from .permissions import (
    IsApprovedTasker,
    IsAssignedTasker,
    IsTaskOwner,
)
from user.models import User
from payment.models import Payment


# -------------------------
# CATEGORY
# -------------------------
class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.filter(parent__isnull=True)  # chỉ lấy category cha
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


# -------------------------
# TASK CRUD
# -------------------------
class TaskListCreateView(generics.ListCreateAPIView):
    """
    - List: Ai cũng có thể xem task public (client chưa gán tasker).
    - Create: Mọi user authenticated đều có thể đăng task (kể cả tasker).
    """
    serializer_class = TaskCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Task.objects.all().select_related("client", "tasker", "category")

    def perform_create(self, serializer):
        serializer.save(client=self.request.user)


class TaskDetailView(generics.RetrieveAPIView):
    queryset = Task.objects.all().select_related("client", "tasker", "category")
    serializer_class = TaskDetailSerializer
    permission_classes = [permissions.AllowAny]


class TaskUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsTaskOwner]

    def perform_update(self, serializer):
        serializer.save(client=self.request.user)


# -------------------------
# TASK FLOW: Accept, Start, Complete
# -------------------------
class TaskAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsApprovedTasker]

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)

        if task.tasker:
            return Response({"error": "Task đã có tasker"}, status=status.HTTP_400_BAD_REQUEST)

        # 🔑 Kiểm tra payment intent (escrow)
        if not hasattr(task, "payment_intent"):
            return Response({"error": "Task chưa có PaymentIntent (client chưa thanh toán trước)."},
                            status=status.HTTP_400_BAD_REQUEST)

        if not task.payment_intent.is_authorized:
            return Response({"error": "Thanh toán chưa được xác thực (escrow chưa giữ tiền)."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Nếu chưa có Payment record → tạo mới
        if not hasattr(task, "payment"):
            payment = Payment.objects.create(
                task=task,
                client=task.client,
                tasker=request.user,
                amount=task.price,
                currency=task.payment_intent.currency,
                platform_fee_percent=10.0  # ví dụ: 10% phí nền tảng
            )
            payment.mark_held()
        else:
            payment = task.payment
            if payment.status != Payment.Status.HELD:
                payment.mark_held()

        # Gán tasker và update status
        task.tasker = request.user
        task.status = "in_progress"  # giữ đúng với Task.Status
        task.save()

        TaskEvent.objects.create(task=task, event="assigned", actor=request.user)

        return Response({"message": "Nhận task thành công"}, status=status.HTTP_200_OK)


class TaskStatusUpdateView(APIView):
    """
    Tasker có thể start/complete task mà họ đã nhận
    """
    permission_classes = [permissions.IsAuthenticated, IsAssignedTasker]

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        action = request.data.get("action")

        if action == "start" and task.status == "in_progress":
            task.status = "started"
            task.save()
            TaskEvent.objects.create(task=task, event="started", actor=request.user)
            return Response({"message": "Task đã bắt đầu"}, status=status.HTTP_200_OK)

        elif action == "complete" and task.status in ["started", "in_progress"]:
            task.status = "completed"
            task.save()
            TaskEvent.objects.create(task=task, event="completed", actor=request.user)

            # 🔑 khi complete thì mark payment completed
            if hasattr(task, "payment"):
                task.payment.mark_completed()

            return Response({"message": "Task đã hoàn thành"}, status=status.HTTP_200_OK)

        return Response({"error": "Hành động không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)


# -------------------------
# TASKER SKILL
# -------------------------
class TaskerSkillViewSet(viewsets.ModelViewSet):
    serializer_class = TaskerSkillSerializer
    permission_classes = [permissions.IsAuthenticated, IsApprovedTasker]

    def get_queryset(self):
        return TaskerSkill.objects.filter(tasker=self.request.user)

    def perform_create(self, serializer):
        serializer.save(tasker=self.request.user)


# -------------------------
# ATTACHMENTS
# -------------------------
class TaskAttachmentViewSet(viewsets.ModelViewSet):
    serializer_class = TaskAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskAttachment.objects.filter(task__client=self.request.user)

    def perform_create(self, serializer):
        task_id = self.request.data.get("task")
        task = get_object_or_404(Task, id=task_id, client=self.request.user)
        serializer.save(task=task)


# -------------------------
# EVENTS (chỉ xem lịch sử)
# -------------------------
class TaskEventListView(generics.ListAPIView):
    serializer_class = TaskEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        task_id = self.kwargs.get("pk")
        task = get_object_or_404(Task, id=task_id)

        # chỉ client hoặc tasker liên quan mới được xem
        if self.request.user not in [task.client, task.tasker]:
            return TaskEvent.objects.none()

        return TaskEvent.objects.filter(task=task).order_by("-created_at")


# -------------------------
# Đây là class dummy để sau này thêm QR code
# -------------------------
class TaskCompleteWithQRView(APIView):
    def post(self, request, task_id):
        # TODO: sẽ implement logic quét QR sau
        return Response({"message": f"QR completion endpoint cho Task {task_id} chưa implement."}, status=status.HTTP_200_OK)
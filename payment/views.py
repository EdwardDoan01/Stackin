from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import PaymentIntent, Payment
from .serializers import PaymentIntentSerializer, PaymentSerializer
from .permissions import IsClientOfTask, IsTaskerOfTask, IsPlatformAdmin,IsClientOfTaskForIntent
from task.models import Task


# -------------------------
# PAYMENT INTENT
# -------------------------
class PaymentIntentCreateView(generics.CreateAPIView):
    """
    Client tạo PaymentIntent cho Task.
    - Chỉ client của task mới tạo được.
    - Một task chỉ có thể có 1 PaymentIntent.
    """
    queryset = PaymentIntent.objects.all()
    serializer_class = PaymentIntentSerializer
    permission_classes = [permissions.IsAuthenticated, IsClientOfTaskForIntent]


# -------------------------
# PAYMENT (VIEW & ADMIN ACTIONS)
# -------------------------
class PaymentDetailView(generics.RetrieveAPIView):
    """
    Xem chi tiết Payment.
    - Client (task.owner) hoặc Tasker liên quan được xem.
    """
    queryset = Payment.objects.all().select_related("task", "client", "tasker")
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, (IsClientOfTask | IsTaskerOfTask)]

    def get_object(self):
        """
        Thay vì filter toàn bộ queryset theo user,
        ta dùng permission để check object-level access.
        """
        obj = get_object_or_404(Payment, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj


class PaymentReleaseView(APIView):
    """
    Client xác nhận hoàn thành task -> release tiền cho Tasker.
    Chỉ client của task có quyền thực hiện.
    """
    permission_classes = [permissions.IsAuthenticated, IsClientOfTask]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        self.check_object_permissions(request, payment)

        if payment.status != Payment.Status.HELD:
            return Response(
                {"error": "Payment không ở trạng thái HELD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ở version cải tiến, nên gọi mark_released() để đảm bảo logic fee & wallet
        try:
            payment.mark_released()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Thanh toán đã được giải phóng cho Tasker"},
            status=status.HTTP_200_OK
        )



class PaymentRefundView(APIView):
    """
    Admin hoặc Client có thể yêu cầu refund.
    - Client: refund payment của task mình.
    - Admin: refund bất kỳ payment nào.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)

        # Kiểm tra quyền: admin hoặc client của task
        if not (IsPlatformAdmin().has_permission(request, self) or IsClientOfTask().has_object_permission(request, self, payment)):
            return Response({"error": "Bạn không có quyền refund"}, status=status.HTTP_403_FORBIDDEN)

        if payment.status != Payment.Status.HELD:
            return Response(
                {"error": "Chỉ có thể refund khi Payment đang HELD"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment.mark_refunded()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "Thanh toán đã được hoàn lại"},
            status=status.HTTP_200_OK
        )



# -------------------------
# ADMIN VIEW ALL PAYMENTS
# -------------------------
class PaymentAdminListView(generics.ListAPIView):
    """
    Admin xem tất cả payment (cho dashboard quản trị).
    """
    queryset = Payment.objects.all().select_related("task", "client", "tasker")
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]

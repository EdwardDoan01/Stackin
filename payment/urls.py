from django.urls import path
from .views import (
    PaymentIntentCreateView,
    PaymentDetailView,
    PaymentReleaseView,
    PaymentRefundView,
    PaymentAdminListView,
)
from .views_webhook import PaymentWebhookView

urlpatterns = [
    # Client tạo PaymentIntent cho task
    path("intent/create/", PaymentIntentCreateView.as_view(), name="payment-intent-create"),

    # Xem chi tiết Payment (client hoặc tasker)
    path("<int:pk>/", PaymentDetailView.as_view(), name="payment-detail"),

    # Client xác nhận release tiền (sau này sẽ thay = QR verification)
    path("<int:pk>/release/", PaymentReleaseView.as_view(), name="payment-release"),

    # Refund (client hoặc admin)
    path("<int:pk>/refund/", PaymentRefundView.as_view(), name="payment-refund"),

    # Admin xem toàn bộ Payment
    path("admin/list/", PaymentAdminListView.as_view(), name="payment-admin-list"),

    path("webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),
]

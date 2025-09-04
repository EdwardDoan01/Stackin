from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
import hmac, hashlib
from django.conf import settings

from .models import PaymentIntent, Payment, ProviderWebhookLog


class PaymentWebhookView(APIView):
    """
    Webhook nhận từ Provider (MOCK / Tazapay).
    - Lưu log vào ProviderWebhookLog.
    - Cập nhật PaymentIntent & Payment tương ứng.
    """

    WEBHOOK_SECRET = getattr(settings, "WEBHOOK_SECRET", "mock-secret")

    @staticmethod
    def verify_signature(secret: str, signature: str, payload: bytes) -> bool:
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    def post(self, request, *args, **kwargs):
        # --- Xác thực chữ ký webhook ---
        signature = request.headers.get("X-Webhook-Signature")
        if not signature or not self.verify_signature(self.WEBHOOK_SECRET, signature, request.body):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
        
        payload = request.data
        provider = payload.get("provider", "MOCK")
        event = payload.get("event")
        provider_ref = payload.get("provider_ref")

        # Lưu log trước
        log = ProviderWebhookLog.objects.create(
            provider=provider,
            event=event or "UNKNOWN",
            provider_ref=provider_ref,
            payload=payload,
            received_at=timezone.now(),
        )
        
        try:
            # Xử lý logic cập nhật PaymentIntent
            intent = PaymentIntent.objects.filter(provider_ref=provider_ref).first()
            if not intent:
                log.error = "Không tìm thấy PaymentIntent"
                log.save(update_fields=["error"])
                return Response({"error": "PaymentIntent not found"}, status=status.HTTP_404_NOT_FOUND)

            if event == "AUTHORIZED":
                intent.status = PaymentIntent.Status.AUTHORIZED
                intent.save(update_fields=["status", "updated_at"])

                # Nếu chưa có Payment thì tạo
                payment, _ = Payment.objects.get_or_create(
                    task=intent.task,
                    defaults={
                        "client": intent.client,
                        "tasker": intent.task.tasker,  # tasker có thể null lúc tạo
                        "amount": intent.amount,
                        "currency": intent.currency,
                    },
                )
                payment.mark_held()

            elif event in ["CANCELED", "EXPIRED"]:
                intent.status = PaymentIntent.Status.CANCELED if event == "CANCELED" else PaymentIntent.Status.EXPIRED
                intent.save(update_fields=["status", "updated_at"])

            log.processed = True
            log.processed_at = timezone.now()
            log.save(update_fields=["processed", "processed_at"])

            return Response({"message": f"Webhook {event} processed"}, status=status.HTTP_200_OK)

        except Exception as e:
            log.error = str(e)
            log.save(update_fields=["error"])
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# payment/models.py
from __future__ import annotations

import uuid
from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.utils import timezone

# Liên kết sang Task
from task.models import Task


CURRENCY_CHOICES = [
    ("VND", "Vietnamese Dong"),
    ("USD", "US Dollar"),
]

PROVIDER_CHOICES = [
    ("MOCK", "Mock Provider"),
    ("TAZAPAY", "Tazapay"),
]


class PaymentIntent(models.Model):
    """
    Đại diện cho ý định thanh toán (khởi tạo phiên thanh toán với provider).
    - Với Tazapay: create order -> có checkout_url; khi user thanh toán xong -> webhook -> AUTHORIZED.
    - Với MOCK: loopback giả lập.
    """
    class Status(models.TextChoices):
        CREATED = "CREATED", "Created"
        REQUIRES_ACTION = "REQUIRES_ACTION", "Requires Action"
        AUTHORIZED = "AUTHORIZED", "Authorized (Escrow funded)"
        CANCELED = "CANCELED", "Canceled"
        EXPIRED = "EXPIRED", "Expired"

    id = models.BigAutoField(primary_key=True)
    task = models.OneToOneField(Task, on_delete=models.PROTECT, related_name="payment_intent")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_intents")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="VND")

    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CREATED)
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, default="MOCK")
    provider_ref = models.CharField(max_length=128, blank=True, null=True, help_text="ID/order_id từ provider")
    checkout_url = models.URLField(blank=True, null=True)
    client_secret = models.CharField(max_length=128, blank=True, null=True)  # tuỳ provider

    # Idempotency cho Create/Confirm/Refund…
    idempotency_key = models.CharField(max_length=64, blank=True, null=True, unique=True)

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["provider", "provider_ref"]),
        ]

    def __str__(self):
        return f"Intent#{self.id} task={self.task_id} {self.status}"

    @property
    def is_authorized(self) -> bool:
        return self.status == self.Status.AUTHORIZED


class Payment(models.Model):
    """
    Bản ghi escrow tương ứng 1 Task.
    Khi intent AUTHORIZED => Payment chuyển sang HELD.
    Khi release => RELEASED (tiền về tasker), có thể ghi phí nền tảng.
    Khi refund => REFUNDED (tiền về client).
    """
    class Status(models.TextChoices):
        NONE = "NONE", "None"
        HELD = "HELD", "Held in Escrow"
        RELEASING = "RELEASING", "Releasing"
        RELEASED = "RELEASED", "Released"
        REFUNDED = "REFUNDED", "Refunded"

    id = models.BigAutoField(primary_key=True)
    task = models.OneToOneField(Task, on_delete=models.PROTECT, related_name="payment")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments_made")
    tasker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments_received", null=True, blank=True
    )

    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="VND")

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NONE)

    platform_fee_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))],
        help_text="Phần trăm phí nền tảng trên amount, ví dụ 10.00 = 10%"
    )
    platform_fee_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Số tiền phí đã tính (snapshot)"
    )

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Payment#{self.id} task={self.task_id} {self.status}"

    def compute_platform_fee(self) -> Decimal:
        return (self.amount * (self.platform_fee_percent / Decimal("100.00"))).quantize(Decimal("0.01"))

    @transaction.atomic
    def mark_held(self):
        if self.status not in [self.Status.NONE, self.Status.HELD]:
            raise ValueError("Invalid transition to HELD")
        self.status = self.Status.HELD
        # snapshot fee lần đầu chuyển HELD
        if self.platform_fee_amount == Decimal("0.00") and self.platform_fee_percent > Decimal("0.00"):
            self.platform_fee_amount = self.compute_platform_fee()
        self.save(update_fields=["status", "platform_fee_amount", "updated_at"])

    @transaction.atomic
    def mark_released(self):
        if self.status != self.Status.HELD:
            raise ValueError("Invalid transition to RELEASED (must be HELD)")
        self.status = self.Status.RELEASING
        self.save(update_fields=["status", "updated_at"])

        # Bút toán release (sang ví tasker + phí nền tảng)
        Wallet.apply_escrow_release(self)

        self.status = self.Status.RELEASED
        self.save(update_fields=["status", "updated_at"])

    @transaction.atomic
    def mark_refunded(self):
        if self.status != self.Status.HELD:
            raise ValueError("Invalid transition to REFUNDED (must be HELD)")
        # Với v1 mock: chỉ đổi trạng thái và ghi log transaction hoàn.
        self.status = self.Status.REFUNDED
        self.save(update_fields=["status", "updated_at"])
        # Lưu ý: Nếu cần sổ cái hoàn tiền client, có thể bổ sung Wallet cho client trong v2.


class Wallet(models.Model):
    """
    Ví tiền. Mỗi tasker có 1 ví. Platform có thể có ví riêng (user=None).
    """
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet", null=True, blank=True
    )
    # Gợi ý: pending_balance dành cho case settlement delay; v1 dùng available luôn.
    available_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    pending_balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        owner = self.user.username if self.user_id else "PLATFORM"
        return f"Wallet({owner}) bal={self.available_balance}"

    @classmethod
    def get_or_create_platform_wallet(cls) -> "Wallet":
        wallet, _ = cls.objects.get_or_create(user=None)
        return wallet

    @classmethod
    @transaction.atomic
    def apply_escrow_release(cls, payment: Payment):
        """
        Chuyển tiền từ escrow (off-ledger) về:
          - Tasker wallet (+amount - fee)
          - Platform wallet (+fee)
        """
        if not payment.tasker_id:
            raise ValueError("Cannot release without assigned tasker")

        fee = payment.platform_fee_amount
        net_to_tasker = (payment.amount - fee).quantize(Decimal("0.01"))

        if net_to_tasker < Decimal("0.00"):
            raise ValueError("Net to tasker negative")

        # Tasker wallet
        tasker_wallet, _ = cls.objects.select_for_update().get_or_create(user_id=payment.tasker_id)
        tasker_wallet.available_balance = (tasker_wallet.available_balance + net_to_tasker).quantize(Decimal("0.01"))
        tasker_wallet.save(update_fields=["available_balance", "updated_at"])

        WalletTransaction.objects.create(
            wallet=tasker_wallet,
            type=WalletTransaction.Type.ESCROW_RELEASE,
            amount=net_to_tasker,
            ref_task=payment.task,
            ref_payment=payment,
            memo=f"Release from task #{payment.task_id}"
        )

        # Platform wallet (phí)
        if fee > Decimal("0.00"):
            platform_wallet = cls.get_or_create_platform_wallet()
            platform_wallet.available_balance = (platform_wallet.available_balance + fee).quantize(Decimal("0.01"))
            platform_wallet.save(update_fields=["available_balance", "updated_at"])

            WalletTransaction.objects.create(
                wallet=platform_wallet,
                type=WalletTransaction.Type.PLATFORM_FEE,
                amount=fee,
                ref_task=payment.task,
                ref_payment=payment,
                memo=f"Platform fee for task #{payment.task_id}"
            )


class WalletTransaction(models.Model):
    """
    Sổ cái giao dịch ví (đơn giản, ghi có vào ví).
    Nếu cần ghi âm (trừ) rõ ràng, thêm sign hoặc type DEBIT/CREDIT; v1 ghi dương cho tăng.
    """
    class Type(models.TextChoices):
        ESCROW_RELEASE = "ESCROW_RELEASE", "Escrow Release to Tasker"
        PLATFORM_FEE = "PLATFORM_FEE", "Platform Fee Income"
        REFUND = "REFUND", "Refund to Client"
        ADJUSTMENT = "ADJUSTMENT", "Manual Adjustment"

    id = models.BigAutoField(primary_key=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    type = models.CharField(max_length=32, choices=Type.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.00"))])

    ref_task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    ref_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    ref_intent = models.ForeignKey(PaymentIntent, on_delete=models.SET_NULL, null=True, blank=True)

    memo = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Txn#{self.id} {self.type} +{self.amount}"


class ProviderWebhookLog(models.Model):
    """
    Nhật ký webhook từ provider (Tazapay/Mock).
    Dùng để audit & idempotency xử lý webhook.
    """
    id = models.BigAutoField(primary_key=True)
    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, default="MOCK")
    event = models.CharField(max_length=64)
    provider_ref = models.CharField(max_length=128, blank=True, null=True)
    signature = models.CharField(max_length=256, blank=True, null=True)
    payload = models.JSONField(default=dict)
    received_at = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["provider", "provider_ref"]),
            models.Index(fields=["processed"]),
            models.Index(fields=["received_at"]),
        ]

    def __str__(self):
        return f"Webhook({self.provider}) {self.event} {self.provider_ref or ''}"

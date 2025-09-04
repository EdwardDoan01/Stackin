from rest_framework import serializers
from .models import PaymentIntent, Payment


class PaymentIntentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentIntent
        fields = [
            "id", "task", "client", "amount", "currency",
            "is_authorized", "provider_ref", "created_at"
        ]
        read_only_fields = ["id", "client", "is_authorized", "created_at", "provider_ref"]

    def validate_task(self, task):
        """
        - Một task chỉ có thể có 1 PaymentIntent tại 1 thời điểm
        (logic business, không phải permission).
        """
        if PaymentIntent.objects.filter(task=task).exists():
            raise serializers.ValidationError("Task này đã có PaymentIntent.")
        return task

    def create(self, validated_data):
        validated_data["client"] = self.context["request"].user
        return super().create(validated_data)


class PaymentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    platform_fee_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id", "task", "client", "tasker", "amount", "currency",
            "status", "status_display",
            "platform_fee_percent", "platform_fee_amount",
            "created_at", "task_title"
        ]
        read_only_fields = [
            "id", "client", "tasker", "status", "created_at",
            "platform_fee_amount", "task_title", "platform_fee_percent"
        ]


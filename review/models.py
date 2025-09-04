from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from task.models import Task


class Review(models.Model):
    class Role(models.TextChoices):
        CLIENT = "CLIENT", "Client"   # Client review Tasker
        TASKER = "TASKER", "Tasker"   # Tasker review Client

    id = models.BigAutoField(primary_key=True)

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="reviews",
        help_text="Review này thuộc về Task nào"
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_given",
        help_text="Người viết review"
    )

    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
        help_text="Người được review"
    )

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        help_text="Vai trò của reviewer trong task này"
    )

    rating = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Điểm đánh giá từ 1–5"
    )

    comment = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "review"
        verbose_name = "Review"
        verbose_name_plural = "Reviews"

        # Một reviewer chỉ được review 1 lần theo role trong 1 task
        unique_together = ("task", "reviewer", "role")

        # Indexes hỗ trợ query nhanh
        indexes = [
            models.Index(fields=["reviewee"]),
            models.Index(fields=["task"]),
        ]

        # CheckConstraint đảm bảo rating trong khoảng 1–5 (bổ sung an toàn DB-level)
        constraints = [
            models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5),
                name="rating_range_1_5"
            ),
        ]

    def __str__(self):
        return f"Review[{self.id}] {self.reviewer} → {self.reviewee} ({self.role})"

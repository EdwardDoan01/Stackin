# review/signals.py
"""
Signals cho review app.

- Khi một Review mới được tạo (post_save, created=True):
  1) Tạo 1 Notification cho reviewee (dùng model noti.Notification).
  2) Ghi 1 TaskEvent (dùng task.TaskEvent) để audit (sử dụng EventType có sẵn và metadata "review_created").

Kỹ thuật:
- Dùng transaction.on_commit(...) để thực hiện side-effects SAU khi transaction commit thành công.
- Import noti.TaskEvent,... bên trong hàm để giảm nguy cơ circular import.
- Ghi log mọi exception thay vì raise để không phá huỷ luồng chính.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone

from .models import Review

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Review)
def review_post_save(sender, instance: Review, created: bool, **kwargs):
    """
    Xử lý khi review được tạo.
    Side-effects (Notification, TaskEvent) sẽ chạy sau commit.
    """
    if not created:
        return

    review = instance  # alias

    def _after_commit():
        # Import ở đây để tránh circular import khi module import lúc Django start
        try:
            from noti.models import Notification
        except Exception as e:
            logger.exception("Cannot import Notification model in review signals: %s", e)
            Notification = None

        try:
            from task.models import TaskEvent
        except Exception as e:
            logger.exception("Cannot import TaskEvent model in review signals: %s", e)
            TaskEvent = None

        # 1) Create Notification for reviewee (if Notification model available)
        if Notification is not None:
            try:
                task_title = getattr(review.task, "title", "")
                title = f"Bạn vừa nhận được đánh giá từ {review.reviewer.username}"
                message = (
                    f"{review.reviewer.username} đã đánh giá bạn {review.rating}/5"
                    f"{f' cho công việc \"{task_title}\"' if task_title else ''}."
                )

                Notification.objects.create(
                    user=review.reviewee,
                    type=Notification.Type.TASK,
                    title=title,
                    message=message,
                    is_read=False,
                    task=review.task,
                    metadata={
                        "rating": float(review.rating),
                        "role": review.role,
                        "review_id": review.id,
                    },
                    created_at=timezone.now(),
                )
            except Exception as exc:
                # Log but don't raise — side-effect should not crash main flow
                logger.exception("Failed to create Notification for Review(id=%s): %s", review.id, exc)

        # 2) Create TaskEvent for audit (if TaskEvent model available)
        if TaskEvent is not None:
            try:
                # Use an existing EventType (avoid inventing new enum values).
                # We reuse STATUS_CHANGED and attach metadata to indicate review creation.
                TaskEvent.objects.create(
                    task=review.task,
                    actor=review.reviewer,
                    event=TaskEvent.EventType.STATUS_CHANGED,
                    from_status="",
                    to_status=review.task.status,
                    note=f"Review created: {review.reviewer_id} -> {review.reviewee_id}",
                    metadata={
                        "action": "review_created",
                        "rating": review.rating,
                        "role": review.role,
                        "review_id": review.id,
                    },
                )
            except Exception as exc:
                logger.exception("Failed to create TaskEvent for Review(id=%s): %s", review.id, exc)

    # Ensure the side-effects run only after the DB transaction commits.
    try:
        transaction.on_commit(_after_commit)
    except Exception as exc:
        # If on_commit is not available for some reason, attempt to run synchronously
        logger.exception("transaction.on_commit failed for Review(id=%s): %s. Running side-effects synchronously.", review.id, exc)
        _after_commit()

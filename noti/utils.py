# noti/utils.py
from .models import Notification

def push_notification(user, type, title, message, task=None, payment=None, metadata=None):
    """
    Helper để tạo notification nhanh từ các app khác (report, chat, task...).
    """
    Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        task=task,
        payment=payment,
        metadata=metadata or {},
    )

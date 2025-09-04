from django.urls import path
from .views import (
    NotificationListView,
    NotificationDetailView,
    NotificationMarkReadView,
    NotificationArchiveView,
    NotificationBulkMarkReadView,
    NotificationUnreadCountView,
    NotificationCreateView,
    NotificationBroadcastView,
)

urlpatterns = [
    # ----- USER SCOPE -----
    path("", NotificationListView.as_view(), name="notification-list"),
    path("<int:pk>/", NotificationDetailView.as_view(), name="notification-detail"),

    # Actions
    path("<int:pk>/mark-read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("<int:pk>/archive/", NotificationArchiveView.as_view(), name="notification-archive"),
    path("bulk/mark-read/", NotificationBulkMarkReadView.as_view(), name="notification-bulk-mark-read"),
    path("unread/count/", NotificationUnreadCountView.as_view(), name="notification-unread-count"),

    # ----- ADMIN / SYSTEM SCOPE -----
    path("admin/create/", NotificationCreateView.as_view(), name="notification-create"),
    path("admin/broadcast/", NotificationBroadcastView.as_view(), name="notification-broadcast"),
]

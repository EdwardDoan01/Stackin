# report/urls.py
from django.urls import path
from .views import (
    ReportListCreateView,
    ReportDetailView,
    ReportAttachmentUploadView,
    ReportModerateView,
)

urlpatterns = [
    path("", ReportListCreateView.as_view(), name="report-list-create"),
    path("<int:pk>/", ReportDetailView.as_view(), name="report-detail"),
    path("attachment/upload/", ReportAttachmentUploadView.as_view(), name="report-attachment-upload"),
    path("<int:pk>/moderate/", ReportModerateView.as_view(), name="report-moderate"),
]

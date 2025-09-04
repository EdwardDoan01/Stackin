# report/views.py
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import models
from django.contrib.auth import get_user_model
from noti.utils import push_notification
from noti.models import Notification

from .models import Report, ReportAttachment, ReportEvent
from .serializers import (
    ReportSerializer,
    ReportCreateSerializer,
    ReportAttachmentSerializer,
    ReportEventSerializer,
    ReportStatusUpdateSerializer,
)
from .permissions import CanCreateReport, IsReportOwnerOrAdmin, IsStaffForModeration


# User-scoped list/create
# report/views.py (chỉ trích phần ModerateView/perform_create)

class ReportListCreateView(generics.ListCreateAPIView):
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return ReportCreateSerializer if self.request.method == "POST" else ReportSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [CanCreateReport()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Report.objects.all().select_related("reporter", "reported_user", "task").order_by("-created_at")
        return Report.objects.filter(
            models.Q(reporter=user) | models.Q(reported_user=user)
        ).select_related("reporter", "reported_user", "task").order_by("-created_at")

    def perform_create(self, serializer):
        serializer.context["request"] = self.request
        report = serializer.save()

        # 🔔 Gửi noti cho admin
        User = get_user_model()
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            push_notification(
                user=admin,
                type=Notification.Type.SYSTEM,
                title=f"New report #{report.id}",
                message=f"Report {report.title} created by {report.reporter.username}",
                metadata={"report_id": report.id},
            )
        return report


class ReportDetailView(generics.RetrieveAPIView):
    queryset = Report.objects.select_related("reporter", "reported_user", "task")
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsReportOwnerOrAdmin]

    def get_object(self):
        obj = get_object_or_404(Report, pk=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj


class ReportAttachmentUploadView(generics.CreateAPIView):
    """
    Upload evidence for a report. User must be reporter or admin.
    """
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = ReportAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        report_id = self.request.data.get("report")
        report = get_object_or_404(Report, pk=report_id)
        # only reporter or admin may upload attachments
        if not (self.request.user.is_staff or report.reporter_id == self.request.user.id):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Bạn không có quyền đính kèm bằng chứng cho report này.")
        serializer.save(report=report)


class ReportModerateView(APIView):
    """
    Admin endpoint để thay đổi trạng thái report: PENDING / UNDER_REVIEW / RESOLVED_* / CANCELLED
    Body: {"status": "<status>", "admin_note": "...", "resolution_note": "..."}
    """
    permission_classes = [IsStaffForModeration]

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        self.check_object_permissions(request, report)

        new_status = request.data.get("status")
        admin_note = request.data.get("admin_note", "")
        resolution_note = request.data.get("resolution_note", "")

        if new_status not in dict(Report.Status.choices):
            return Response({"error": "status không hợp lệ"}, status=status.HTTP_400_BAD_REQUEST)

        old_status = report.status
        report.status = new_status
        report.admin_note = admin_note or report.admin_note
        report.resolution_note = resolution_note or report.resolution_note
        report.handled_by = request.user
        report.handled_at = timezone.now()
        report.save(update_fields=["status", "admin_note", "resolution_note", "handled_by", "handled_at", "updated_at"])

        # Event log
        ReportEvent.objects.create(
            report=report,
            actor=request.user,
            event=ReportEvent.EventType.STATUS_CHANGED,
            from_status=old_status,
            to_status=new_status,
            note=admin_note or resolution_note or "",
            metadata={"source": "admin:moderate"},
        )

        # 🔔 Notify reporter
        push_notification(
            user=report.reporter,
            type=Notification.Type.SYSTEM,
            title=f"Report #{report.id} updated",
            message=f"Your report status: {report.status}",
            metadata={"report_id": report.id},
        )

        # 🔔 Notify reported_user
        if report.reported_user_id:
            push_notification(
                user=report.reported_user,
                type=Notification.Type.SYSTEM,
                title=f"Report #{report.id} outcome",
                message=f"You were reported. Status: {report.status}",
                metadata={"report_id": report.id},
            )

        return Response({"message": "Report updated", "status": report.status}, status=status.HTTP_200_OK)

User = get_user_model()

class ReportListCreateView(generics.ListCreateAPIView):
    ...
    def perform_create(self, serializer):
        serializer.context["request"] = self.request
        report = serializer.save()

        # 🔔 Gửi noti cho admin
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            push_notification(
                user=admin,
                type=Notification.Type.SYSTEM,
                title=f"New report #{report.id}",
                message=f"Report {report.title} created by {report.reporter.username}",
                metadata={"report_id": report.id},
            )
        return report
    

class ReportStatusUpdateView(generics.UpdateAPIView):
    queryset = Report.objects.all()
    serializer_class = ReportStatusUpdateSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_update(self, serializer):
        report = serializer.save()

        # 🔔 Notify reporter
        push_notification(
            user=report.reporter,
            type=Notification.Type.SYSTEM,
            title=f"Report #{report.id} resolved",
            message=f"Your report has been marked as {report.status}",
            metadata={"report_id": report.id},
        )

        # 🔔 Notify reported_user
        if report.reported_user:
            push_notification(
                user=report.reported_user,
                type=Notification.Type.SYSTEM,
                title=f"Report #{report.id} outcome",
                message=f"You were reported. Status: {report.status}",
                metadata={"report_id": report.id},
            )
# report/serializers.py
from rest_framework import serializers
from django.db import transaction
from django.utils import timezone

from .models import Report, ReportAttachment, ReportEvent
from task.models import Task
from user.models import User


class ReportAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportAttachment
        fields = ["id", "report", "file", "caption", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


class ReportEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ReportEvent
        fields = ["id", "event", "from_status", "to_status", "note", "metadata", "actor", "created_at"]

    def get_actor(self, obj):
        if not obj.actor_id:
            return None
        return {"id": obj.actor_id, "username": getattr(obj.actor, "username", None)}


class ReportSerializer(serializers.ModelSerializer):
    reporter = serializers.PrimaryKeyRelatedField(read_only=True)
    reported_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    attachments = ReportAttachmentSerializer(many=True, read_only=True)
    events = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "type",
            "task",
            "reporter",
            "reported_user",
            "category",
            "severity",
            "title",
            "description",
            "status",
            "admin_note",
            "resolution_note",
            "handled_by",
            "handled_at",
            "metadata",
            "attachments",
            "events",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "status", "admin_note", "resolution_note",
            "handled_by", "handled_at", "metadata", "attachments", "events",
            "created_at", "updated_at"
        ]

    def get_events(self, obj):
        qs = obj.events.order_by("-created_at")
        return ReportEventSerializer(qs, many=True).data


class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Serializer dùng để tạo report.
    reporter được lấy từ request.user (không cho client gửi trường này).
    """
    reporter = serializers.PrimaryKeyRelatedField(read_only=True)
    reported_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "type",
            "task",
            "reported_user",
            "category",
            "severity",
            "title",
            "description",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        """
        1) reporter != reported_user
        2) nếu có task: validate role mapping theo type (reporter/reportee must be client/tasker)
        3) chặn duplicate open report (PENDING/UNDER_REVIEW)
        """
        request = self.context.get("request")
        reporter = getattr(request, "user", None)
        reported_user = data.get("reported_user")
        rtype = data.get("type")
        task = data.get("task", None)

        # basic auth
        if not reporter or not reporter.is_authenticated:
            raise serializers.ValidationError("Authentication required to create report.")

        if reporter.id == reported_user.id:
            raise serializers.ValidationError("Bạn không thể report chính mình.")

        # If task provided, enforce mapping
        if task:
            # ensure task exists (PrimaryKeyRelatedField already did) and mapping hold
            # For CLIENT report: reporter must be tasker, reported_user must be client
            if rtype == Report.ReportType.CLIENT:
                if task.tasker_id != reporter.id:
                    raise serializers.ValidationError("Chỉ tasker của task này mới có thể report client cho task này.")
                if task.client_id != reported_user.id:
                    raise serializers.ValidationError("reported_user không phải là client của task này.")
            elif rtype == Report.ReportType.TASKER:
                if task.client_id != reporter.id:
                    raise serializers.ValidationError("Chỉ client của task này mới có thể report tasker cho task này.")
                if task.tasker_id != reported_user.id:
                    raise serializers.ValidationError("reported_user không phải là tasker của task này.")
            else:
                raise serializers.ValidationError("Loại report không hợp lệ.")
        else:
            # No task provided: allow creation but ensure that roles align if possible
            # For safer operation, you might require task, but current design allows nullable task.
            # Here we'll do a relaxed check: if reporter.is_tasker==True and type=CLIENT -> allowed
            if rtype == Report.ReportType.CLIENT and not reporter.is_tasker:
                raise serializers.ValidationError("Chỉ tasker mới có thể tạo report kiểu CLIENT (nếu không cung cấp task).")
            if rtype == Report.ReportType.TASKER and reporter.is_tasker:
                raise serializers.ValidationError("Chỉ client mới có thể tạo report kiểu TASKER (nếu không cung cấp task).")

        # Prevent duplicate open reports for same pair+task+type
        existing = Report.objects.filter(
            reporter=reporter,
            reported_user=reported_user,
            type=rtype,
            task=task,
            status__in=[Report.Status.PENDING, Report.Status.UNDER_REVIEW],
        )
        if existing.exists():
            raise serializers.ValidationError("Đã tồn tại report đang mở cho cặp này (reporter/reported_user/task/type).")

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        reporter = request.user
        with transaction.atomic():
            report = Report.objects.create(
                reporter=reporter,
                **validated_data
            )
            # Create initial event
            ReportEvent.objects.create(
                report=report,
                actor=reporter,
                event=ReportEvent.EventType.CREATED,
                from_status="",
                to_status=report.status,
                note="Report created via API",
                metadata={"source": "api:create"},
            )
        return report

class ReportStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = ["status", "admin_note", "resolution_note"]
        read_only_fields = []
from django.utils import timezone
from rest_framework import serializers
from .models import Category, Task, TaskerSkill, TaskAttachment, TaskEvent


# ========== Category ==========
class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "description", "icon", "is_active", "sort_order", "parent", "children"]
        read_only_fields = ["slug", "children"]

    def get_children(self, obj):
        # trả về danh sách con cấp 1 (có thể mở rộng đệ quy nếu cần)
        qs = obj.children.filter(is_active=True).order_by("sort_order", "name")
        return SimpleCategorySerializer(qs, many=True).data


class SimpleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


# ========== TaskerSkill ==========
class TaskerSkillSerializer(serializers.ModelSerializer):
    category = SimpleCategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.filter(is_active=True), write_only=True
    )

    class Meta:
        model = TaskerSkill
        fields = ["id", "category", "category_id", "experience_level", "is_primary", "created_at"]
        read_only_fields = ["id", "created_at"]


# ========== TaskAttachment ==========
class TaskAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]


# ========== Task (Create/Update) ==========
class TaskCreateUpdateSerializer(serializers.ModelSerializer):
    # category nhận bằng id khi ghi
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.filter(is_active=True), write_only=True
    )
    # attachments tạo riêng endpoint; ở đây chỉ đọc
    attachments = TaskAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "price",
            "currency",
            "location_text",
            "lat",
            "lng",
            "scheduled_start",
            "duration_minutes",
            "attributes",
            "category",          # read-only nested minimal
            "category_id",       # write-only
            "status",            # read-only on create; limited on update
            "posted_at",
            "expires_at",
            "attachments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "status", "posted_at", "expires_at", "category", "created_at", "updated_at"
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["category"] = SimpleCategorySerializer(instance.category).data
        return data

    # --- VALIDATION RULES ---
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Giá phải lớn hơn 0.")
        return value

    def validate_duration_minutes(self, value):
        if value <= 0 or value > 24 * 60:
            raise serializers.ValidationError("Thời lượng phải trong khoảng 1..1440 phút.")
        return value

    def validate_scheduled_start(self, value):
        # cho phép null (task ngay lập tức), nếu có thì phải sau 'now - 5 phút' (dung sai)
        if value and value < timezone.now() - timezone.timedelta(minutes=5):
            raise serializers.ValidationError("Thời gian bắt đầu không được ở quá khứ.")
        return value

    def validate(self, attrs):
        # Ví dụ: nếu có lat thì phải có lng (và ngược lại)
        lat = attrs.get("lat")
        lng = attrs.get("lng")
        if (lat is None) ^ (lng is None):
            raise serializers.ValidationError("Nếu cung cấp toạ độ thì phải có đủ lat và lng.")
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        # đảm bảo không bị trùng client
        validated_data.pop("client", None)

        # lấy category ra riêng (nếu có)
        category = validated_data.pop("category", None)

        # tạo task
        task = Task.objects.create(client=user, category=category, **validated_data)

        # ghi lại event
        TaskEvent.objects.create(
            task=task,
            actor=user,
            event=TaskEvent.EventType.CREATED,
            from_status="",
            to_status=task.status,
            metadata={"source": "api:create"},
        )
        return task


    def update(self, instance: Task, validated_data):
        # chỉ cho phép update khi task chưa được gán
        if instance.status not in [Task.Status.DRAFT, Task.Status.POSTED]:
            raise serializers.ValidationError("Chỉ được cập nhật khi Task còn ở trạng thái DRAFT/POSTED.")
        
        validated_data.pop("client", None)
        validated_data.pop("tasker", None)
        
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        TaskEvent.objects.create(
            task=instance,
            actor=getattr(self.context.get("request"), "user", None),
            event=TaskEvent.EventType.STATUS_CHANGED,
            from_status=instance.status,
            to_status=instance.status,
            metadata={"source": "api:update"},
        )
        return instance


# ========== Task (List/Detail) ==========
class TaskListSerializer(serializers.ModelSerializer):
    category = SimpleCategorySerializer(read_only=True)
    client_id = serializers.IntegerField(source="client.id", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "title", "price", "currency", "location_text",
            "status", "category", "client_id", "posted_at", "created_at"
        ]


class TaskDetailSerializer(serializers.ModelSerializer):
    category = SimpleCategorySerializer(read_only=True)
    client = serializers.SerializerMethodField()
    tasker = serializers.SerializerMethodField()
    attachments = TaskAttachmentSerializer(many=True, read_only=True)
    events = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "title", "description",
            "price", "currency",
            "location_text", "lat", "lng",
            "scheduled_start", "duration_minutes",
            "status", "category",
            "client", "tasker",
            "attributes",
            "posted_at", "expires_at",
            "attachments",
            "events",
            "created_at", "updated_at",
        ]

    def get_client(self, obj):
        # tránh vòng lặp import với user.UserSerializer, trả minimal
        return {
            "id": obj.client_id,
            "username": getattr(obj.client, "username", None),
        }

    def get_tasker(self, obj):
        if not obj.tasker_id:
            return None
        return {
            "id": obj.tasker_id,
            "username": getattr(obj.tasker, "username", None),
        }

    def get_events(self, obj):
        qs = obj.events.order_by("-created_at")[:20]
        return TaskEventSerializer(qs, many=True).data


# ========== TaskEvent (read-only) ==========
class TaskEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = TaskEvent
        fields = ["id", "event", "from_status", "to_status", "note", "metadata", "actor", "created_at"]

    def get_actor(self, obj):
        if not obj.actor_id:
            return None
        return {"id": obj.actor_id, "username": getattr(obj.actor, "username", None)}

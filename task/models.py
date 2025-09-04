from django.conf import settings
from django.db import models
from django.utils.text import slugify
import uuid


# ==========
# Category (có phân cấp, phục vụ filter & recommend)
# ==========
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children'
    )
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='category_icons/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        indexes = [
            models.Index(fields=['parent', 'sort_order']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            i = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)



class TaskerSkill(models.Model):
    class ExperienceLevel(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        EXPERT = "expert", "Expert"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasker_skills'
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='tasker_skills')
    experience_level = models.CharField(
        max_length=20, choices=ExperienceLevel.choices, default=ExperienceLevel.BEGINNER
    )
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'category')
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['category']),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} - {self.category.name} ({self.experience_level})"



class Task(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        POSTED = "posted", "Posted"
        ASSIGNED = "assigned", "Assigned"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CLIENT_CONFIRMED = "client_confirmed", "Client Confirmed"
        DISPUTED = "disputed", "Disputed"
        CANCELLED_BY_CLIENT = "cancelled_by_client", "Cancelled by Client"
        CANCELLED_BY_TASKER = "cancelled_by_tasker", "Cancelled by Tasker"
        CANCELLED_BY_SYSTEM = "cancelled_by_system", "Cancelled by System"
        EXPIRED = "expired", "Expired"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks_created"
    )
    tasker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tasks_taken"
    )
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="tasks")

    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="VND")

    # địa điểm cơ bản; có thể mở rộng geo sau
    location_text = models.CharField(max_length=255, blank=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    scheduled_start = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=60)

    status = models.CharField(max_length=32, choices=Status.choices, default=Status.POSTED)

    # thuộc tính động theo category (vd: plumbing: urgency, dog_walking: dog_size, ...)
    attributes = models.JSONField(default=dict, blank=True)

    posted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status', 'category', '-posted_at']),
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['tasker', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        return f"{self.title} [{self.get_status_display()}]"

    @property
    def is_open(self) -> bool:
        return self.status == self.Status.POSTED


class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['task', '-uploaded_at']),
        ]

    def __str__(self) -> str:
        return f"Attachment {self.id} for Task {self.task_id}"


class TaskEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        PUBLISHED = "published", "Published"
        ASSIGNED = "assigned", "Assigned"
        STARTED = "started", "Started"
        COMPLETED = "completed", "Completed"
        CONFIRMED = "confirmed", "Client Confirmed"
        DISPUTED = "disputed", "Disputed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        STATUS_CHANGED = "status_changed", "Status Changed"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='events')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='task_events'
    )
    event = models.CharField(max_length=32, choices=EventType.choices)
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, blank=True)
    note = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

    class Meta:
        indexes = [
            models.Index(fields=['task', '-created_at']),
            models.Index(fields=['event']),
        ]

    def __str__(self) -> str:
        return f"{self.event} on Task {self.task_id} at {self.created_at:%Y-%m-%d %H:%M:%S}"


class TaskQR(models.Model):
    task = models.OneToOneField(Task, on_delete=models.CASCADE, related_name="qr_code")
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"QR for Task {self.task.id}"
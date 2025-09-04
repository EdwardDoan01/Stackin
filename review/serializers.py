from rest_framework import serializers
from django.db.models import Avg, Count
from .models import Review
from user.models import User


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.username", read_only=True)
    reviewee_name = serializers.CharField(source="reviewee.username", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "task",
            "reviewer",
            "reviewer_name",
            "reviewee",
            "reviewee_name",
            "role",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ReviewCreateSerializer(serializers.ModelSerializer):
    """
    Serializer để tạo mới Review.
    - reviewer sẽ lấy từ request.user → không cần client gửi lên
    - reviewee sẽ được xác định theo role:
        + Nếu role = CLIENT → reviewer = Client, reviewee = Tasker
        + Nếu role = TASKER → reviewer = Tasker, reviewee = Client
    """

    class Meta:
        model = Review
        fields = ["task", "role", "rating", "comment"]

    def create(self, validated_data):
        request = self.context["request"]
        reviewer = request.user
        task = validated_data["task"]
        role = validated_data["role"]

        # Xác định reviewee
        if role == Review.Role.CLIENT:
            # Client review Tasker
            reviewee = task.tasker
        else:
            # Tasker review Client
            reviewee = task.client

        review = Review.objects.create(
            reviewer=reviewer,
            reviewee=reviewee,
            **validated_data
        )
        return review


class UserReviewStatsSerializer(serializers.ModelSerializer):
    """
    Trả về rating trung bình & tổng số review cho 1 user.
    Dùng trong API profile hoặc khi xem chi tiết Tasker.
    """
    avg_rating = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "avg_rating", "total_reviews"]

    def get_avg_rating(self, obj):
        return obj.reviews_received.aggregate(avg=Avg("rating"))["avg"] or 0

    def get_total_reviews(self, obj):
        return obj.reviews_received.aggregate(count=Count("id"))["count"] or 0

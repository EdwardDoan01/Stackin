# review/views.py
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Review
from .serializers import (
    ReviewSerializer,
    ReviewCreateSerializer,
    UserReviewStatsSerializer,
)
from .permissions import CanCreateReview, CanViewReview
from user.models import User


# ------------------------
# CREATE
# ------------------------
class ReviewCreateView(generics.CreateAPIView):
    """
    Client review Tasker hoặc Tasker review Client.
    Chỉ cho phép nếu task đã COMPLETED / CLIENT_CONFIRMED.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated, CanCreateReview]

    def perform_create(self, serializer):
        review = serializer.save(reviewer=self.request.user)
        # TODO: Tích hợp TaskEvent + Notification ở đây
        return review


# ------------------------
# DETAIL
# ------------------------
class ReviewDetailView(generics.RetrieveAPIView):
    """
    Xem chi tiết 1 review.
    Reviewer, Reviewee hoặc Admin mới được xem.
    """
    queryset = Review.objects.select_related("task", "reviewer", "reviewee")
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, CanViewReview]


# ------------------------
# LIST
# ------------------------
class ReviewListView(generics.ListAPIView):
    """
    Danh sách review của 1 user (reviewee).
    Query param:
      - reviewee=<user_id> (nếu không truyền → mặc định = request.user)
      - role=CLIENT|TASKER (lọc theo vai trò reviewer)
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        reviewee_id = self.request.query_params.get("reviewee") or self.request.user.id
        qs = Review.objects.filter(reviewee_id=reviewee_id)

        role = self.request.query_params.get("role")
        if role in [Review.Role.CLIENT, Review.Role.TASKER]:
            qs = qs.filter(role=role)

        return qs.select_related("task", "reviewer", "reviewee").order_by("-created_at")


# ------------------------
# USER STATS
# ------------------------
class UserReviewStatsView(APIView):
    """
    Trả về tổng quan review của 1 user (avg rating + total reviews).
    Endpoint: /reviews/stats/<user_id>/
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        serializer = UserReviewStatsSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

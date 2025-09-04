# review/urls.py
from django.urls import path
from .views import (
    ReviewCreateView,
    ReviewDetailView,
    ReviewListView,
    UserReviewStatsView,
)

urlpatterns = [
    # ----- CREATE -----
    path("create/", ReviewCreateView.as_view(), name="review-create"),

    # ----- DETAIL -----
    path("<int:pk>/", ReviewDetailView.as_view(), name="review-detail"),

    # ----- LIST -----
    path("", ReviewListView.as_view(), name="review-list"),

    # ----- USER STATS -----
    path("stats/<int:user_id>/", UserReviewStatsView.as_view(), name="review-stats"),
]

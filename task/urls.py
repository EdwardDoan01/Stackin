from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryListView,
    TaskListCreateView,
    TaskDetailView,
    TaskUpdateDeleteView,
    TaskAcceptView,
    TaskStatusUpdateView,
    TaskerSkillViewSet,
    TaskAttachmentViewSet,
    TaskEventListView,
    TaskCompleteWithQRView
)

router = DefaultRouter()
router.register(r"skills", TaskerSkillViewSet, basename="tasker-skill")
router.register(r"attachments", TaskAttachmentViewSet, basename="task-attachment")

urlpatterns = [
    # Category
    path("categories/", CategoryListView.as_view(), name="category-list"),

    # Task CRUD
    path("tasks/", TaskListCreateView.as_view(), name="task-list-create"),
    path("tasks/<int:pk>/", TaskDetailView.as_view(), name="task-detail"),
    path("tasks/<int:pk>/update-delete/", TaskUpdateDeleteView.as_view(), name="task-update-delete"),

    # Task flow
    path("tasks/<int:pk>/accept/", TaskAcceptView.as_view(), name="task-accept"),
    path("tasks/<int:pk>/status/", TaskStatusUpdateView.as_view(), name="task-status-update"),

    # Task events
    path("tasks/<int:pk>/events/", TaskEventListView.as_view(), name="task-events"),

    # Routers (skills, attachments)
    path("", include(router.urls)),

    path("tasks/<int:task_id>/complete-qr/", TaskCompleteWithQRView.as_view(), name="task-complete-qr"),

]

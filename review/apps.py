from django.apps import AppConfig


class ReviewConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'review'

    def ready(self):
        # Import signals khi Django start
        try:
            import review.signals  # noqa: F401
        except ImportError:
            pass
from django.apps import AppConfig


class AutoApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.auto_api'

    def ready(self):
        from src.apps.auto_api import signals  # noqa: F401

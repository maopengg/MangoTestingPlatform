from django.apps import AppConfig


class PerfConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.perf'
    label = 'auto_perf'

    def ready(self):
        from src.apps.perf import receivers  # noqa: F401

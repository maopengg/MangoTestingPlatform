from django.apps import AppConfig


class TestCenterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "src.apps.test_center"
    verbose_name = "测试管理"

    def ready(self):
        from src.apps.test_center import signals  # noqa: F401

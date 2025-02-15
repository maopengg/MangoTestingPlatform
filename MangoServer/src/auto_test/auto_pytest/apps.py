from django.apps import AppConfig


class AutoPytestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_pytest'

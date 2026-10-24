from django.apps import AppConfig


class AutoUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.auto_ui'

    def ready(self):
        return

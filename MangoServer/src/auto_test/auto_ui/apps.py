from threading import Thread

from django.apps import AppConfig


class AutoUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_ui'

    def ready(self):
        def run():
            pass

        task = Thread(target=run)
        task.start()

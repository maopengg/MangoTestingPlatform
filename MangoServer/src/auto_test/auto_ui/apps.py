from threading import Thread

import time
from django.apps import AppConfig


class AutoUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_ui'

    def ready(self):
        task = Thread(target=self.start_consumer)
        task.start()

    def start_consumer(self):
        time.sleep(5)
        self.run_tests()

    def run_tests(self):
        pass

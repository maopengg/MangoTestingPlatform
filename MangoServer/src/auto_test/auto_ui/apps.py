from threading import Thread

import time
from django.apps import AppConfig

from src.enums.tools_enum import TaskEnum


class AutoUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_ui'

    def ready(self):
        task = Thread(target=self.start_consumer)
        task.start()

    def start_consumer(self):
        time.sleep(5)
        self.refresh_status()

    def refresh_status(self):
        pass
        # while True:
        #     time.sleep(30)
        #     from src.auto_test.auto_ui.models import UiCase, UiCaseStepsDetailed, PageSteps
        #     UiCase.objects.filter(status=TaskEnum.PROCEED.value).update(status=TaskEnum.FAIL)
        #     UiCaseStepsDetailed.objects.filter(status=TaskEnum.PROCEED.value).update(status=TaskEnum.FAIL)
        #     PageSteps.objects.filter(status=TaskEnum.PROCEED.value).update(status=TaskEnum.FAIL)

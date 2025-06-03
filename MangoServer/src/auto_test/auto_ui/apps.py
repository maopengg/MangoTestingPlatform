import time
from apscheduler.schedulers.background import BackgroundScheduler
from django.apps import AppConfig

from src.enums.tools_enum import TaskEnum


class AutoUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_ui'

    def ready(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.refresh_status, 'interval', minutes=10)
        scheduler.start()

    def start_consumer(self):
        time.sleep(5)
        self.refresh_status()

    def refresh_status(self):
        from src.auto_test.auto_ui.models import UiCase, UiCaseStepsDetailed, PageSteps
        UiCase.objects.filter(status=TaskEnum.PROCEED.value).update(status=TaskEnum.FAIL.value)
        UiCaseStepsDetailed.objects.filter(status=TaskEnum.PROCEED.value).update(status=TaskEnum.FAIL.value)
        PageSteps.objects.filter(status=TaskEnum.PROCEED.value).update(status=TaskEnum.FAIL.value)

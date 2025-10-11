from datetime import timedelta
from threading import Thread

import time
from apscheduler.schedulers.background import BackgroundScheduler
from django.apps import AppConfig
from django.utils import timezone

from src.enums.tools_enum import TaskEnum
from src.tools.decorator.retry import ensure_db_connection


class AutoUiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_ui'

    def ready(self):
        def run():
            time.sleep(3)
            # self.test_case_consumption()
            self.start_consumer()

        task = Thread(target=run)
        task.start()

    def start_consumer(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.refresh_status, 'interval', minutes=5)
        scheduler.start()

    @ensure_db_connection()
    def refresh_status(self):
        from src.auto_test.auto_ui.models import UiCase, UiCaseStepsDetailed, PageSteps
        ten_minutes_ago = timezone.now() - timedelta(minutes=10)
        UiCase.objects.filter(
            status=TaskEnum.PROCEED.value,
            update_time__lt=ten_minutes_ago
        ).update(status=TaskEnum.FAIL.value)

        UiCaseStepsDetailed.objects.filter(
            status=TaskEnum.PROCEED.value,
            update_time__lt=ten_minutes_ago
        ).update(status=TaskEnum.FAIL.value)

        PageSteps.objects.filter(
            status=TaskEnum.PROCEED.value,
            update_time__lt=ten_minutes_ago
        ).update(status=TaskEnum.FAIL.value)

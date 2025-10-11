from datetime import timedelta
from threading import Thread

import time
from apscheduler.schedulers.background import BackgroundScheduler
from django.apps import AppConfig
from django.utils import timezone

from src.enums.tools_enum import TaskEnum
from src.tools.decorator.retry import ensure_db_connection
from src.tools.log_collector import log


class AutoPytestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_pytest'

    def ready(self):
        def run():
            time.sleep(5)
            self.pull_code()
            self.start_consumer()

        task = Thread(target=run)
        task.start()

    # def test_case_consumption(self):
    #     self.case_flow = PytestCaseFlow()
    #     self.pytest_task = Thread(target=self.case_flow.process_tasks)
    #     self.pytest_task.daemon = True
    #     self.pytest_task.start()
    # def shutdown(self):
    #     self.case_flow.stop()
    #     self.pytest_task.join()

    def pull_code(self):
        from src.auto_test.auto_pytest.service.base import git_obj
        try:
            git_obj()
        except Exception:
            import traceback
            log.pytest.debug(f'{traceback.format_exc()}')
            log.pytest.info(f'如果您的项目已经配置了pytest等相关配置则关注下这个异常，如果没有配置请忽略！')

    def start_consumer(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(self.refresh_status, 'interval', minutes=5)
        scheduler.start()

    @ensure_db_connection()
    def refresh_status(self):
        from src.auto_test.auto_pytest.models import PytestCase
        ten_minutes_ago = timezone.now() - timedelta(minutes=10)

        PytestCase.objects.filter(
            status=TaskEnum.PROCEED.value,
            update_time__lt=ten_minutes_ago
        ).update(status=TaskEnum.FAIL.value)

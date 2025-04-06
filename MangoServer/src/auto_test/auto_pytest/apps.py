from threading import Thread

import atexit
import time
from django.apps import AppConfig

from src.auto_test.auto_pytest.service.test_case.case_flow import PytestCaseFlow
from src.enums.system_enum import CacheDataKeyEnum


class AutoPytestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_pytest'

    def ready(self):
        def run():
            time.sleep(5)
            self.test_case_consumption()
            self.pull_code()

        task = Thread(target=run)
        task.start()
        atexit.register(self.shutdown)

    def test_case_consumption(self):
        self.case_flow = PytestCaseFlow()
        self.pytest_task = Thread(target=self.case_flow.process_tasks)
        self.pytest_task.daemon = True
        self.pytest_task.start()

    def pull_code(self):
        from src.auto_test.auto_pytest.service.base.version_control import GitRepo
        from src.auto_test.auto_system.models import CacheData
        try:
            repo_url = CacheData.objects.get(key=CacheDataKeyEnum.GIT_URL.name)
            if repo_url and repo_url.value:
                repo = GitRepo()
                repo.pull_repo()
        except Exception:
            pass

    def shutdown(self):
        self.case_flow.stop()
        self.pytest_task.join()

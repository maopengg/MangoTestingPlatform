import time
from threading import Thread

from django.apps import AppConfig

# from src.auto_test.auto_pytest.service.test_case.case_flow import PytestCaseFlow
from src.enums.system_enum import CacheDataKeyEnum
from src.tools import project_dir
from src.tools.log_collector import log


class AutoPytestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_pytest'

    def ready(self):
        def run():
            time.sleep(5)
            # self.test_case_consumption()
            self.pull_code()

        task = Thread(target=run)
        task.start()
        # atexit.register(self.shutdown)

    # def test_case_consumption(self):
    #     self.case_flow = PytestCaseFlow()
    #     self.pytest_task = Thread(target=self.case_flow.process_tasks)
    #     self.pytest_task.daemon = True
    #     self.pytest_task.start()

    def pull_code(self):
        from mangotools.mangos import GitRepoOperator
        from src.auto_test.auto_system.models import CacheData
        try:
            repo_url = CacheData.objects.get(key=CacheDataKeyEnum.PYTEST_GIT_URL.name).value
            username = CacheData.objects.get(key=CacheDataKeyEnum.PYTEST_GIT_USERNAME.name).value
            password = CacheData.objects.get(key=CacheDataKeyEnum.PYTEST_GIT_PASSWORD.name).value
            if repo_url is not None and username is None and password is not None:
                repo = GitRepoOperator(repo_url, project_dir.root_path(), log.pytest, username, password)
                repo.clone()
        except Exception:
            pass

    # def shutdown(self):
    #     self.case_flow.stop()
    #     self.pytest_task.join()

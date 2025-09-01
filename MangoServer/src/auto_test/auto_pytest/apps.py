from threading import Thread

import time
from django.apps import AppConfig

# from src.auto_test.auto_pytest.service.test_case.case_flow import PytestCaseFlow
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
        from src.auto_test.auto_pytest.service.base import git_obj
        try:
            repo = git_obj()
            repo.clone()
        except Exception:
            import traceback
            log.pytest.error(f'{traceback.format_exc()}')

    # def shutdown(self):
    #     self.case_flow.stop()
    #     self.pytest_task.join()

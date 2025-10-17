from threading import Thread

import time
from django.apps import AppConfig

from src.tools.log_collector import log


class AutoPytestConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_pytest'

    def ready(self):
        def run():
            time.sleep(10)
            self.pull_code()

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
        except Exception as e:
            import traceback
            log.pytest.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')
            log.pytest.info(f'如果您的项目已经配置了pytest等相关配置则关注下这个异常，如果没有配置请忽略！')

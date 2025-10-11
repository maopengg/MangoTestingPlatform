from threading import Thread

import atexit
import time
from django.apps import AppConfig

from src.auto_test.auto_api.service.test_case.case_flow import ApiCaseFlow


class AutoApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.auto_test.auto_api'

    def ready(self):
        def run():
            time.sleep(3)
            self.test_case_consumption()

        task = Thread(target=run)
        task.start()
        atexit.register(self.shutdown)

    def test_case_consumption(self):
        self.case_flow = ApiCaseFlow()
        self.api_task = Thread(target=self.case_flow.process_tasks)
        self.api_task.daemon = True
        self.api_task.start()

    def shutdown(self):
        self.case_flow.stop()
        self.api_task.join()

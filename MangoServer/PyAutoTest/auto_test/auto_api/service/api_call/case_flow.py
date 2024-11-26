# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

import time

from PyAutoTest.models.api_model import ApiCaseModel
from PyAutoTest.tools.log_collector import log
from mangokit import singleton


@singleton
class CaseFlow:
    queue = Queue()
    max_tasks = 5

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=self.max_tasks)
        self.futures = []

    def process_tasks(self):
        try:
            while True:
                if not self.queue.empty():
                    case_model = self.queue.get()
                    future = self.executor.submit(self.execute_task, case_model)
                    self.futures.append(future)
                for future in as_completed(self.futures):
                    self.futures.remove(future)
                time.sleep(0.1)
        except Exception as error:
            traceback.print_exc()
            log.system.error(f'API线程池发生异常：{error}')

    @classmethod
    def execute_task(cls, case_model: ApiCaseModel):
        from PyAutoTest.auto_test.auto_api.service.api_call.test_case import TestCase
        test_case = TestCase(
            user_id=case_model.user_id,
            test_env=case_model.test_env,
            tasks_id=case_model.tasks_id,
            test_suite=case_model.test_suite,
            test_suite_details=case_model.test_suite_details,
            is_send=False,
        )
        test_case.test_case(case_model.case_id)

    @classmethod
    def add_task(cls, case_model: ApiCaseModel):
        cls.queue.put(case_model)

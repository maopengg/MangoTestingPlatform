# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import time

from src.models.system_model import ConsumerCaseModel
from src.tools.decorator.retry import ensure_db_connection


class PytestCaseFlow:
    queue = Queue()
    max_tasks = 2
    executor = ThreadPoolExecutor(max_workers=max_tasks)
    running = True

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    @ensure_db_connection(True)
    def process_tasks(cls):
        while cls.running:
            if not cls.queue.empty():
                case_model = cls.queue.get()
                cls.executor.submit(cls.execute_task, case_model)
            time.sleep(0.1)

    @classmethod
    @ensure_db_connection()
    def execute_task(cls, case_model: ConsumerCaseModel):
        from src.auto_test.auto_pytest.service.test_case.test_case import TestCase
        test_case = TestCase(
            user_id=case_model.user_id,
            test_suite=case_model.test_suite,
            test_suite_details=case_model.test_suite_details,
        )
        return test_case.test_case_main(case_model.case_id)

    @classmethod
    def add_task(cls, case_model: ConsumerCaseModel):
        cls.queue.put(case_model)

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import traceback
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import time

from mangokit import Mango
from src.models.system_model import ConsumerCaseModel
from src.settings import IS_SEND_MAIL
from src.tools.log_collector import log


class PytestCaseFlow:
    queue = Queue()
    max_tasks = 2
    executor = ThreadPoolExecutor(max_workers=max_tasks)
    running = True

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    def process_tasks(cls):
        while cls.running:
            try:
                if not cls.queue.empty():
                    case_model = cls.queue.get()
                    cls.executor.submit(cls.execute_task, case_model)
                time.sleep(0.1)
            except Exception as error:
                trace = traceback.format_exc()
                log.system.error(f'Pytest线程池发生异常：{error}，报错：{trace}')
                if IS_SEND_MAIL:
                    Mango.s(cls.process_tasks, error, trace)

    @classmethod
    def execute_task(cls, case_model: ConsumerCaseModel):
        from src.auto_test.auto_pytest.service.test_case.test_case import TestCase
        try:
            test_case = TestCase(
                user_id=case_model.user_id,
                test_suite=case_model.test_suite,
                test_suite_details=case_model.test_suite_details,
            )
            return test_case.test_case_main(case_model.case_id)
        except Exception as error:
            trace = traceback.format_exc()
            log.pytest.error(f'pytest线程池任务异常：{trace}')
            if IS_SEND_MAIL:
                Mango.s(cls.execute_task, error, trace, case_model=case_model)
            log.system.error(f'Pytest线程池发生异常：{error}，错误内容：{trace}')

    @classmethod
    def add_task(cls, case_model: ConsumerCaseModel):
        cls.queue.put(case_model)

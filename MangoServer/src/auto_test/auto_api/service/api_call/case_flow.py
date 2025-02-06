# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
from concurrent.futures import ThreadPoolExecutor

import time
import traceback
from datetime import datetime
from queue import Queue

from src.models.api_model import ApiCaseModel
from src.settings import IS_SEND_MAIL
from src.tools.log_collector import log
from mangokit import singleton
from mangokit import Mango


@singleton
class CaseFlow:
    queue = Queue()
    max_tasks = 5

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=self.max_tasks)
        self.running = True

    def stop(self):
        self.running = False

    def process_tasks(self):
        case_model = None
        while self.running:
            try:
                if not self.queue.empty():
                    case_model = self.queue.get()
                    self.executor.submit(self.execute_task, case_model)
                time.sleep(0.1)
            except Exception as error:
                trace = traceback.format_exc()
                log.system.error(f'API线程池发生异常：{error}，报错：{trace}')
                if IS_SEND_MAIL:
                    Mango.s(self.process_tasks, error, trace, case_model=case_model)

    @classmethod
    def execute_task(cls, case_model: ApiCaseModel):
        try:
            from src.auto_test.auto_api.service.api_call.test_case import TestCase
            test_case = TestCase(
                user_id=case_model.user_id,
                test_env=case_model.test_env,
                tasks_id=case_model.tasks_id,
                test_suite=case_model.test_suite,
                test_suite_details=case_model.test_suite_details,
                is_send=False,
            )
            return test_case.test_case(case_model.case_id)
        except Exception as error:
            trace = traceback.format_exc()
            if IS_SEND_MAIL:
                Mango.s(cls.execute_task, error, trace, case_model=case_model)
            log.system.error(f'API线程池发生异常：{error}')

    @classmethod
    def add_task(cls, case_model: ApiCaseModel):
        cls.queue.put(case_model)

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import traceback
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

import time

from mangotools.mangos import Mango
from src.models.system_model import ConsumerCaseModel
from src.settings import IS_SEND_MAIL
from src.tools.log_collector import log


class ApiCaseFlow:
    queue = Queue()
    max_tasks = 2

    executor = ThreadPoolExecutor(max_workers=max_tasks)
    running = True

    @classmethod
    def stop(cls):
        cls.running = False

    @classmethod
    def process_tasks(cls):
        case_model = None
        while cls.running:
            try:
                if not cls.queue.empty():
                    case_model = cls.queue.get()
                    cls.executor.submit(cls.execute_task, case_model)
                time.sleep(0.1)
            except Exception as error:
                trace = traceback.format_exc()
                log.system.error(f'API线程池发生异常：{error}，报错：{trace}')
                if IS_SEND_MAIL:
                    from src.settings import VERSION
                    Mango.s(cls.process_tasks, error, trace, case_model=case_model, version=VERSION)

    @classmethod
    def execute_task(cls, case_model: ConsumerCaseModel):
        try:
            from src.auto_test.auto_api.service.test_case.test_case import TestCase
            test_case = TestCase(
                user_id=case_model.user_id,
                test_env=case_model.test_env,
                case_id=case_model.case_id,
                test_suite=case_model.test_suite,
                test_suite_details=case_model.test_suite_details,
            )
            return test_case.test_case()
        except Exception as error:
            trace = traceback.format_exc()
            if IS_SEND_MAIL:
                from src.settings import VERSION
                Mango.s(cls.execute_task, error, trace, case_model=case_model, version=VERSION)
            log.system.error(f'API线程池发生异常：{error}')

    @classmethod
    def add_task(cls, case_model: ConsumerCaseModel):
        cls.queue.put(case_model)

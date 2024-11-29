# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-11-23 20:38
# @Author : 毛鹏
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
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
                    try:
                        result = future.result()
                        print(result)
                    except Exception as error:
                        log.system.error(error)
                        trace = traceback.format_exc()
                        content = f"""
                              芒果测试平台管理员请注意查收:
                                  触发时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                                  错误函数：run_tests
                                  异常类型: {type(error)}
                                  错误提示: {str(error)}
                                  错误详情：{trace}

                              **********************************
                              详细情况可前往芒果测试平台查看，非相关负责人员可忽略此消息。谢谢！

                                                                            -----------芒果测试平台
                              """
                        from mangokit import Mango
                        Mango.s(content)
                    self.futures.remove(future)
                time.sleep(0.1)
        except Exception as error:
            traceback.print_exc()
            log.system.error(f'API线程池发生异常：{error}')

    @classmethod
    def execute_task(cls, case_model: ApiCaseModel):
        try:
            from PyAutoTest.auto_test.auto_api.service.api_call.test_case import TestCase
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
            traceback.print_exc()
            log.system.error(f'API线程池发生异常：{error}')

    @classmethod
    def add_task(cls, case_model: ApiCaseModel):
        cls.queue.put(case_model)

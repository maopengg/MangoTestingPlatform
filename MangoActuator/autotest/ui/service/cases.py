# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-02-04 11:16
# @Author : 毛鹏
import asyncio
import json
import traceback

from autotest.ui.base_tools.driver_object import DriverObject
from autotest.ui.service.steps import Steps
from enums.socket_api_enum import UiSocketEnum
from enums.tools_enum import StatusEnum, ClientTypeEnum, CacheKeyEnum
from enums.ui_enum import DriveTypeEnum
from models.socket_model.ui_model import CaseModel, TestSuiteModel
from service.socket_client import ClientWebSocket
from tools.data_processor.sql_cache import SqlCache
from tools.desktop.signal_send import SignalSend
from tools.log_collector import log


class Cases(DriverObject):

    def __init__(self, test_suite_model: TestSuiteModel):
        super().__init__()
        self.test_suite_model = test_suite_model
        self.msg = []
        self.status = []

    async def case_distribute(self):
        # 创建一个Semaphore来限制并发数
        test_case_parallelism = SqlCache.get_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value)
        if self.test_suite_model.concurrent:
            semaphore = asyncio.Semaphore(self.test_suite_model.concurrent)
        elif test_case_parallelism:
            semaphore = asyncio.Semaphore(int(test_case_parallelism))
        else:
            semaphore = asyncio.Semaphore(10)

        async def run_with_semaphore(case):
            try:
                async with semaphore:
                    # 在这里执行你的run方法
                    return await self.run(case)
            except Exception as error:
                # 处理异常，例如打印日志或者进行其他操作
                traceback.print_exc()  # 打印异常追踪信息
                log.error(f"任务 {case.id} 出现异常：{error}")

        # 创建所有任务，但是受到semaphore的限制
        tasks = [run_with_semaphore(case) for case in self.test_suite_model.case_list]

        # 并发运行所有任务并等待它们完成
        await asyncio.gather(*tasks)

        del self.test_suite_model.case_list
        if StatusEnum.FAIL.value in self.status:
            self.test_suite_model.status = StatusEnum.FAIL.value
            self.test_suite_model.error_message = json.dumps(self.msg, ensure_ascii=False)
        else:
            self.test_suite_model.status = StatusEnum.SUCCESS.value
        self.test_suite_model.run_status = StatusEnum.SUCCESS.value
        msg = f'编号：{self.test_suite_model.id}的批次用例执行完成，请前往测试报告查看' if self.test_suite_model.status else f'编号：{self.test_suite_model.id}的批次用例包含失败，请前往首页查看'
        await ClientWebSocket.async_send(
            code=200 if self.test_suite_model.status else 300,
            msg=msg,
            is_notice=ClientTypeEnum.WEB.value,
            func_name=UiSocketEnum.CASE_BATCH_RESULT.value,
            func_args=self.test_suite_model
        )

    async def run(self, case_model: CaseModel):
        async with Steps(self.test_suite_model.project, test_suite_id=self.test_suite_model.id) as obj:
            for step in case_model.case_list:
                match step.type:
                    case DriveTypeEnum.WEB.value:
                        self.web_config = step.equipment_config
                        obj.context, obj.page = await self.new_web_page()
                        break
                    case DriveTypeEnum.ANDROID.value:
                        pass
                    case DriveTypeEnum.IOS.value:
                        pass
                    case DriveTypeEnum.DESKTOP.value:
                        pass
                    case _:
                        log.error('自动化类型不存在，请联系管理员检查！')
            await obj.case_setup(case_model)
            self.msg.append(obj.case_result.error_message)
            self.status.append(obj.case_result.status)

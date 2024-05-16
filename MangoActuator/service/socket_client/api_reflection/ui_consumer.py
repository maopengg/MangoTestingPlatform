# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023/5/10 11:43
# @Author : 毛鹏
from autotest.ui.service.case_run import CaseRun
from autotest.ui.service.page_steps import PageSteps
from enums.tools_enum import ClientTypeEnum, CacheKeyEnum
from exceptions import MangoActuatorError
from models.socket_model.ui_model import PageStepsModel, WEBConfigModel, CaseModel
from service.socket_client.client_socket import ClientWebSocket
from tools.data_processor.sql_cache import SqlCache
from tools.decorator.convert_args import convert_args
from tools.public_methods import async_global_exception


class UIConsumer:
    page_steps: PageSteps = None
    case_run: CaseRun = None

    @classmethod
    @convert_args(PageStepsModel)
    async def u_page_step(cls, data: PageStepsModel):
        """
        执行页面步骤
        @param data:
        @return:
        """
        try:
            if cls.page_steps is None:
                cls.page_steps = PageSteps(data.project_product_id)
            await cls.page_steps.page_steps_setup(data)
            await cls.page_steps.page_steps_mian()
        except MangoActuatorError as error:
            await ClientWebSocket().async_send(
                code=error.code,
                msg=error.msg,
                is_notice=ClientTypeEnum.WEB.value
            )
        except Exception as error:
            await async_global_exception(
                'u_page_step',
                error
            )

    @classmethod
    @convert_args(WEBConfigModel)
    async def u_page_new_obj(cls, data: WEBConfigModel):
        """
        实例化浏览器对象
        @param data:
        @return:
        """
        try:
            if cls.page_steps is None:
                cls.page_steps = PageSteps(data.project_product_id)
            await cls.page_steps.new_web_obj(data)
        except Exception as error:
            await async_global_exception(
                'u_page_new_obj',
                error
            )

    @classmethod
    @convert_args(CaseModel)
    async def u_case(cls, data: CaseModel):
        """
        执行测试用例
        @param data:
        @return:
        """
        try:
            if cls.case_run is None:
                max_tasks = 2
                test_case_parallelism = SqlCache.get_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value)
                if test_case_parallelism:
                    max_tasks = int(test_case_parallelism)
                cls.case_run = CaseRun(max_tasks)
            await cls.case_run.queue.put(data)
        except Exception as error:
            await async_global_exception(
                'u_case',
                error
            )

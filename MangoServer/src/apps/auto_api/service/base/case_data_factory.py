# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API用例前置数据工厂

from src.apps.auto_api.models import ApiCase, ApiCaseDetailedParameter
from src.apps.auto_api.service.base.api_base_test_setup import APIBaseTestSetup
from src.apps.auto_data_factory.service.case_config_runner import DataFactoryCaseConfigRunner
from src.common.enums.data_factory_enum import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryExecutionSourceEnum,
)
from src.common.exceptions import ApiError
from src.common.tools.log_collector import log


class CaseDataFactory:
    """执行API用例前置中的数据工厂配置。"""

    def __init__(self, test_setup: APIBaseTestSetup, api_case: ApiCase, user_id: int | None = None):
        self.test_setup = test_setup
        self.api_case = api_case
        self.user_id = user_id
        self.runner: DataFactoryCaseConfigRunner | None = None

    def run_front(self):
        if not self.test_setup.test_object:
            raise ApiError(300, "数据工厂执行前请先初始化测试环境")
        self.runner = DataFactoryCaseConfigRunner(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
            source_id=self.api_case.id,
            execution_source_type=DataFactoryExecutionSourceEnum.API_CASE.value,
            test_object_id=self.test_setup.test_object.id,
            test_data=self.test_setup.test_data,
            logger=log.api,
            user_id=self.user_id,
        )
        self.runner.run_front()

    def cleanup(self):
        if self.runner:
            self.runner.cleanup()


class ParameterDataFactory:
    """执行API接口场景前置中的数据工厂配置。"""

    def __init__(self, test_setup: APIBaseTestSetup, parameter: ApiCaseDetailedParameter, user_id: int | None = None):
        self.test_setup = test_setup
        self.parameter = parameter
        self.user_id = user_id
        self.runner: DataFactoryCaseConfigRunner | None = None

    def run_front(self):
        if not self.test_setup.test_object:
            raise ApiError(300, "数据工厂执行前请先初始化测试环境")
        self.runner = DataFactoryCaseConfigRunner(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
            source_id=self.parameter.id,
            execution_source_type=DataFactoryExecutionSourceEnum.API_CASE_PARAMETER.value,
            test_object_id=self.test_setup.test_object.id,
            test_data=self.test_setup.test_data,
            logger=log.api,
            user_id=self.user_id,
        )
        self.runner.run_front()

    def cleanup(self):
        if self.runner:
            self.runner.cleanup()

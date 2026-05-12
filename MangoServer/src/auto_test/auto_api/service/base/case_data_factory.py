# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API用例前置数据工厂

from src.auto_test.auto_api.models import ApiCase, ApiCaseDetailedParameter
from src.auto_test.auto_api.service.base.api_base_test_setup import APIBaseTestSetup
from src.auto_test.auto_data_factory.service.case_config_runner import DataFactoryCaseConfigRunner
from src.enums.data_factory_enum import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryExecutionSourceEnum,
)
from src.exceptions import ApiError
from src.tools.log_collector import log


class CaseDataFactory:
    """执行API用例前置中的数据工厂配置。"""

    def __init__(self, test_setup: APIBaseTestSetup, api_case: ApiCase):
        self.test_setup = test_setup
        self.api_case = api_case
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
        )
        self.runner.run_front()

    def cleanup(self):
        if self.runner:
            self.runner.cleanup()


class ParameterDataFactory:
    """执行API接口场景前置中的数据工厂配置。"""

    def __init__(self, test_setup: APIBaseTestSetup, parameter: ApiCaseDetailedParameter):
        self.test_setup = test_setup
        self.parameter = parameter
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
        )
        self.runner.run_front()

    def cleanup(self):
        if self.runner:
            self.runner.cleanup()

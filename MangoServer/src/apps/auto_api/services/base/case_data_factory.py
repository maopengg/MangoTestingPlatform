from src.apps.auto_api.exceptions import (
    AUTO_API_BASE_CASE_DATA_FACTORY_TEST_ENVIRONMENT_EXECUTION_INVALID,
    AUTO_API_BASE_CASE_DATA_FACTORY_TEST_ENVIRONMENT_EXECUTION_INVALID_CODE_TEST_ENVIRONMENT_EXECUTION_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCase, ApiCaseDetailedParameter
from src.apps.auto_api.services.base.api_base_test_setup import APIBaseTestSetup
from src.apps.data_factory.enums import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryExecutionSourceEnum,
)
from src.apps.data_factory.services.case_config_runner import DataFactoryCaseConfigRunner
from src.common.logging import log


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API用例前置数据工厂


class CaseDataFactory:
    """执行API用例前置中的数据工厂配置。"""

    def __init__(
            self,
            test_setup: APIBaseTestSetup,
            api_case: ApiCase,
            user_id: int | None = None,
            configs=None,
    ):
        self.test_setup = test_setup
        self.api_case = api_case
        self.user_id = user_id
        self.configs = configs
        self.runner: DataFactoryCaseConfigRunner | None = None

    def run_front(self):
        self.test_setup.ensure_execution_context()
        if not self.test_setup.test_object:
            raise AutoApiError(AUTO_API_BASE_CASE_DATA_FACTORY_TEST_ENVIRONMENT_EXECUTION_INVALID)
        self.runner = DataFactoryCaseConfigRunner(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
            source_id=self.api_case.id,
            execution_source_type=DataFactoryExecutionSourceEnum.API_CASE.value,
            test_object_id=self.test_setup.test_object.id,
            test_data=self.test_setup.test_data,
            logger=log.api,
            user_id=self.user_id,
            configs=self.configs,
        )
        self.runner.run_front()

    def cleanup(self):
        if self.runner:
            self.runner.cleanup()


class ParameterDataFactory:
    """执行API接口场景前置中的数据工厂配置。"""

    def __init__(
            self,
            test_setup: APIBaseTestSetup,
            parameter: ApiCaseDetailedParameter,
            user_id: int | None = None,
            configs=None,
    ):
        self.test_setup = test_setup
        self.parameter = parameter
        self.user_id = user_id
        self.configs = configs
        self.runner: DataFactoryCaseConfigRunner | None = None

    def run_front(self):
        self.test_setup.ensure_execution_context()
        if not self.test_setup.test_object:
            raise AutoApiError(
                AUTO_API_BASE_CASE_DATA_FACTORY_TEST_ENVIRONMENT_EXECUTION_INVALID_CODE_TEST_ENVIRONMENT_EXECUTION_INVALID)
        self.runner = DataFactoryCaseConfigRunner(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
            source_id=self.parameter.id,
            execution_source_type=DataFactoryExecutionSourceEnum.API_CASE_PARAMETER.value,
            test_object_id=self.test_setup.test_object.id,
            test_data=self.test_setup.test_data,
            logger=log.api,
            user_id=self.user_id,
            configs=self.configs,
        )
        self.runner.run_front()

    def cleanup(self):
        if self.runner:
            self.runner.cleanup()

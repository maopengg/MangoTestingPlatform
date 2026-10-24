from src.apps.auto_ui.exceptions import (
    AUTO_UI_TEST_CASE_CASE_DATA_FACTORY_TEST_ENVIRONMENT_EXECUTION_INVALID,
    AutoUiError,
)
from src.apps.auto_ui.models import UiCase
from src.apps.data_factory.enums import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryExecutionSourceEnum,
)
from src.apps.data_factory.services.case_config_runner import DataFactoryCaseConfigRunner
from src.common.logging import log


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: UI用例前置数据工厂


class UiCaseDataFactory:
    """执行UI用例前置中的数据工厂配置。"""

    def __init__(self, test_object_id: int | None, test_data, ui_case: UiCase, user_id: int | None = None):
        self.test_object_id = test_object_id
        self.test_data = test_data
        self.ui_case = ui_case
        self.user_id = user_id
        self.runner: DataFactoryCaseConfigRunner | None = None

    def run_front(self):
        if not self.test_object_id:
            raise AutoUiError(AUTO_UI_TEST_CASE_CASE_DATA_FACTORY_TEST_ENVIRONMENT_EXECUTION_INVALID)
        self.runner = DataFactoryCaseConfigRunner(
            source_type=DataFactoryCaseSourceTypeEnum.UI_CASE.value,
            source_id=self.ui_case.id,
            execution_source_type=DataFactoryExecutionSourceEnum.UI_CASE.value,
            test_object_id=self.test_object_id,
            test_data=self.test_data,
            logger=log.ui,
            user_id=self.user_id,
        )
        self.runner.run_front()

    def cleanup(self):
        if self.runner:
            self.runner.cleanup()

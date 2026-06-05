# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: UI用例前置数据工厂

from src.apps.auto_data_factory.service.case_config_runner import DataFactoryCaseConfigRunner
from src.apps.auto_ui.models import UiCase
from src.common.enums.data_factory_enum import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryExecutionSourceEnum,
)
from src.common.exceptions import UiError
from src.common.tools.log_collector import log


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
            raise UiError(300, "数据工厂执行前请先初始化测试环境")
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

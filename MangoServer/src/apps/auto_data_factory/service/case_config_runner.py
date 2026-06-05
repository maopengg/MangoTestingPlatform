# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 自动化用例数据工厂配置执行服务

from typing import Any

from src.apps.auto_data_factory.models import DataFactoryCaseConfig
from src.apps.auto_data_factory.service.cleanup import DataFactoryCleanup
from src.apps.auto_data_factory.service.runner import DataFactoryRunner
from src.common.enums.data_factory_enum import (
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionStageEnum,
)
from src.common.enums.tools_enum import StatusEnum


class DataFactoryCaseConfigRunner:
    """执行 API/UI 等自动化用例绑定的数据工厂配置。"""

    def __init__(
            self,
            source_type: int,
            source_id: int,
            execution_source_type: int,
            test_object_id: int,
            test_data,
            logger,
            user_id: int | None = None,
    ):
        self.source_type = source_type
        self.source_id = source_id
        self.execution_source_type = execution_source_type
        self.test_object_id = test_object_id
        self.test_data = test_data
        self.logger = logger
        self.user_id = user_id
        self.context: dict[str, Any] = self.build_context()
        self.execution_ids: list[int] = []
        self.auto_cleanup_execution_ids: list[int] = []

    def build_context(self) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if self.user_id:
            context["__executor"] = {"user_id": self.user_id}
        return context

    def run_front(self):
        configs = DataFactoryCaseConfig.objects.select_related(
            'template',
            'template__entity',
            'template__entity__datasource_alias',
            'template__project_product',
        ).filter(
            source_type=self.source_type,
            source_id=self.source_id,
            stage=1,
            status=StatusEnum.SUCCESS.value,
        ).order_by('sort', 'id')
        if not configs:
            return

        for config in configs:
            overrides = self.replace_value(config.field_overrides or {})
            result = DataFactoryRunner.run_template(
                template_id=config.template_id,
                source_type=self.execution_source_type,
                source_id=self.source_id,
                stage=DataFactoryExecutionStageEnum.CREATE.value,
                test_object_id=self.test_object_id,
                overrides=overrides,
                context=self.context,
                cleanup_strategy_override=config.cleanup_strategy,
                test_data=self.test_data,
            )
            self.execution_ids.append(result["execution_id"])
            cleanup_strategy = config.cleanup_strategy
            if cleanup_strategy is None:
                cleanup_strategy = config.template.cleanup_strategy
            if cleanup_strategy == DataFactoryCleanupStrategyEnum.EXECUTION_END.value:
                self.auto_cleanup_execution_ids.append(result["execution_id"])
            self.write_data_factory_cache(config, result)

    def cleanup(self):
        for execution_id in self.auto_cleanup_execution_ids:
            try:
                result = DataFactoryCleanup.cleanup_execution(execution_id, allow_missing=True)
                self.logger.info(f'用例数据工厂自动清理完成，execution_id:{execution_id}，结果:{result}')
            except Exception as error:
                self.logger.error(f'用例数据工厂自动清理失败，execution_id:{execution_id}，错误:{error}')

    def replace_value(self, value):
        if isinstance(value, str):
            return self.test_data.replace(value)
        if isinstance(value, list):
            return [self.replace_value(item) for item in value]
        if isinstance(value, dict):
            return {key: self.replace_value(item) for key, item in value.items()}
        return value

    def write_data_factory_cache(self, config: DataFactoryCaseConfig, result: dict):
        cache_name = config.name or config.template.name
        data = result.get("data") or {}
        self.set_data_factory_cache(cache_name, data)
        self.set_data_factory_cache(f"{cache_name}.__execution_id", result.get("execution_id"))
        self.set_data_factory_cache(f"{cache_name}.__execution_no", result.get("execution_no"))
        for key, value in self.flatten_value(data).items():
            self.set_data_factory_cache(f"{cache_name}.{key}", value)
        for item in result.get("items") or []:
            item_name = item.get("name")
            item_data = item.get("data") or {}
            if not item_name:
                continue
            self.set_data_factory_cache(f"{cache_name}.{item_name}", item_data)
            for key, value in self.flatten_value(item_data).items():
                self.set_data_factory_cache(f"{cache_name}.{item_name}.{key}", value)

    def set_data_factory_cache(self, key: str, value: Any):
        if hasattr(self.test_data, "set_data_factory_cache"):
            self.test_data.set_data_factory_cache(key, value)
        else:
            self.test_data.set_cache(f"df.{key}", value)

    @classmethod
    def flatten_value(cls, value: Any, parent_key: str = "") -> dict[str, Any]:
        result = {}
        if isinstance(value, dict):
            for key, item in value.items():
                next_key = f"{parent_key}.{key}" if parent_key else str(key)
                result.update(cls.flatten_value(item, next_key))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                next_key = f"{parent_key}.{index}" if parent_key else str(index)
                result.update(cls.flatten_value(item, next_key))
        elif parent_key:
            result[parent_key] = value
        return result

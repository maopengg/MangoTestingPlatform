from copy import deepcopy
from typing import Any, Iterable

from django.db import models
from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import (
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionStageEnum,
)
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_CASE_AUTO_CLEANUP_FAILED,
    DataFactoryError,
)
from src.apps.data_factory.models import DataFactoryCaseConfig
from src.apps.data_factory.services.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.runner import DataFactoryRunner


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 自动化用例数据工厂配置执行服务


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
            configs: Iterable[dict[str, Any] | DataFactoryCaseConfig] | None = None,
    ):
        self.source_type = source_type
        self.source_id = source_id
        self.execution_source_type = execution_source_type
        self.test_object_id = test_object_id
        self.test_data = test_data
        self.logger = logger
        self.user_id = user_id
        self.configs = None if configs is None else tuple(deepcopy(list(configs)))
        self.context: dict[str, Any] = self.build_context()
        self.execution_ids: list[int] = []
        self.auto_cleanup_execution_ids: list[int] = []

    def build_context(self) -> dict[str, Any]:
        context: dict[str, Any] = {}
        if self.user_id:
            context["__executor"] = {"user_id": self.user_id}
        return context

    def run_front(self):
        configs = self.get_front_configs()
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

    def get_front_configs(self) -> list[DataFactoryCaseConfig]:
        if self.configs is None:
            return list(DataFactoryCaseConfig.objects.select_related(
                'template',
                'template__entity',
                'template__entity__datasource_alias',
                'template__project_product',
            ).filter(
                source_type=self.source_type,
                source_id=self.source_id,
                stage=1,
                status=StatusEnum.SUCCESS.value,
            ).order_by('sort', 'id'))

        configs = [
            self.hydrate_config(item) if isinstance(item, dict) else item
            for item in self.configs
        ]
        return sorted(
            (
                config for config in configs
                if config.source_type == self.source_type
                   and config.source_id == self.source_id
                   and config.stage == 1
                   and config.status == StatusEnum.SUCCESS.value
            ),
            key=lambda config: (config.sort, config.id),
        )

    @staticmethod
    def hydrate_config(payload: dict[str, Any]) -> DataFactoryCaseConfig:
        values = {}
        for field in DataFactoryCaseConfig._meta.concrete_fields:
            if field.name not in payload:
                continue
            key = field.attname if isinstance(field, models.ForeignKey) else field.name
            values[key] = deepcopy(payload[field.name])
        return DataFactoryCaseConfig(**values)

    def cleanup(self):
        failures = []
        for execution_id in self.auto_cleanup_execution_ids:
            try:
                result = DataFactoryCleanup.cleanup_execution(
                    execution_id, created_by=self.user_id, force_cleanup=True, allow_missing=True)
                if result.get('fail'):
                    reasons = [value['error'] for value in result.get('errors', [])
                               if isinstance(value, dict) and isinstance(value.get('error'), str)]
                    failures.append({'execution_id': execution_id, 'fail': result['fail'],
                                     'error': '；'.join(reasons) or '清理返回失败但未提供具体原因，请管理员检查执行记录的清理明细'})
                    self.logger.error(f'用例数据工厂自动清理未通过，execution_id:{execution_id}')
                else:
                    self.logger.info(f'用例数据工厂自动清理完成，execution_id:{execution_id}')
            except Exception as error:
                from src.apps.auto_api.exceptions import TestSuiteStopped
                if isinstance(error, TestSuiteStopped):
                    raise
                from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService
                if isinstance(error, DataFactoryError):
                    DatasourceInfrastructureService.annotate(error, execution_id=execution_id)
                    DatasourceInfrastructureService.capture(error, result_unknown=True)
                else:
                    error = DatasourceInfrastructureService.internal_cleanup_error(error, 'case_factory_cleanup', execution_id=execution_id)
                try:
                    from src.apps.data_factory.services.cleanup_schedule import DataFactoryCleanupScheduleService
                    DataFactoryCleanupScheduleService.record_wait_failure(execution_id)
                except Exception:
                    self.logger.error(f'记录自动清理等待失败异常，execution_id:{execution_id}')
                failures.append({'execution_id': execution_id, 'error': error.msg})
                self.logger.error(f'用例数据工厂自动清理失败，execution_id:{execution_id}，错误:{error}')
        if failures:
            summary = '; '.join(
                f"工厂执行 {item['execution_id']}，未完成 {item.get('fail', 1)} 项：{item['error']}"
                for item in failures
            )
            raise DataFactoryError(DATA_FACTORY_CASE_AUTO_CLEANUP_FAILED, value=(summary,))

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

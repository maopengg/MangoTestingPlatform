# -*- coding: utf-8 -*-
from django.utils import timezone

from src.apps.data_factory.models import DataFactoryDatasourceBinding
from src.apps.data_factory.services.data_source_execution import DataSourceExecutionService
from src.apps.data_factory.services.datasource import DataFactoryDatasourceResolver, is_missing_value
from src.apps.gray_config.enums import GrayActionEnum, GrayExecutionStatusEnum
from src.apps.gray_config.exceptions import (
    GRAY_SQL_CONFIG_GRAY_REQUIRED,
    GRAY_SQL_DATABASE_BINDING_GRAY_INVALID,
    GRAY_TEST_ENVIRONMENT_SQL_EXECUTION_GRAY_REQUIRED,
    GRAY_TEST_ENVIRONMENT_DATABASE_BINDING_GRAY_INVALID,
    GrayConfigError,
)
from src.apps.gray_config.models import GrayExecutionLog, GrayFeature


class GraySqlService:
    @classmethod
    def preview_feature(cls, feature: GrayFeature, target_value: str | None, action: str) -> dict:
        sql = cls.resolve_sql(feature, action)
        execute_sql, params = cls.build_sql_params(feature, sql, target_value)
        return {
            "feature_id": feature.id,
            "feature_key": feature.feature_key,
            "target_value": target_value,
            "action": action,
            "sql": execute_sql,
            "params": params,
            "before_text": sql,
            "after_text": execute_sql,
            "config_type": "sql",
        }

    @classmethod
    def execute_feature(
            cls,
            feature: GrayFeature,
            target_value: str | None,
            action: str,
            gray_config_id: int | None = None,
            case_snapshot: dict | None = None,
    ) -> GrayExecutionLog:
        sql = cls.resolve_sql(feature, action)
        log = GrayExecutionLog.objects.create(
            gray_config_id=gray_config_id,
            gray_feature=feature,
            database=feature.database,
            config_type=feature.config_type,
            feature_key=feature.feature_key,
            target_value=target_value,
            action=action,
            before_snapshot={"sql": sql},
            status=GrayExecutionStatusEnum.WAITING.value,
            started_at=timezone.now(),
            **(case_snapshot or {}),
        )
        try:
            execute_sql, params = cls.build_sql_params(feature, sql, target_value)
            log.before_snapshot = {"sql": execute_sql, "params": params}
            log.affected_rows = cls.execute_sql(
                feature,
                execute_sql,
                params,
                source_context={
                    **(case_snapshot or {}),
                    'source_type': 'gray_config',
                    'source_stage': action,
                    'source_id': gray_config_id or feature.id,
                    'gray_config_id': gray_config_id,
                    'gray_feature_id': feature.id,
                },
            )
            resolved_database_id = getattr(feature, 'runtime_database_id', None)
            if resolved_database_id:
                log.database_id = resolved_database_id
            log.after_snapshot = {"sql": execute_sql, "params": params, "affected_rows": log.affected_rows}
            log.status = GrayExecutionStatusEnum.SUCCESS.value
        except Exception as error:
            log.status = GrayExecutionStatusEnum.FAILED.value
            log.error_message = str(error)
        finally:
            log.finished_at = timezone.now()
            log.save()
        return log

    @staticmethod
    def resolve_sql(feature: GrayFeature, action: str) -> str:
        if action == GrayActionEnum.ENABLE.value:
            sql = feature.enable_sql
        elif action == GrayActionEnum.DISABLE.value:
            sql = feature.disable_sql
        else:
            sql = feature.restore_sql or feature.disable_sql
        if not sql:
            raise GrayConfigError(GRAY_SQL_CONFIG_GRAY_REQUIRED)
        return sql

    @staticmethod
    def build_sql_params(feature: GrayFeature, sql: str, target_value: str | None) -> tuple[str, dict]:
        target_value = "" if target_value is None else str(target_value)
        execute_sql = (
            (sql or "")
            .replace("${{target_value}}", ":target_value")
            .replace("${target_value}", ":target_value")
            .replace("{{target_value}}", ":target_value")
            .replace("${{feature_key}}", ":feature_key")
            .replace("${feature_key}", ":feature_key")
            .replace("{{feature_key}}", ":feature_key")
        )
        params = {
            "target_value": target_value,
            "feature_key": feature.feature_key,
        }
        return execute_sql, params

    @staticmethod
    def execute_sql(
            feature: GrayFeature,
            sql: str,
            params: dict,
            source_context: dict | None = None,
    ) -> int:
        if not feature.datasource_alias_id and not feature.database_id:
            raise GrayConfigError(GRAY_SQL_DATABASE_BINDING_GRAY_INVALID)
        environment = getattr(feature, 'runtime_environment', None)
        if is_missing_value(environment):
            raise GrayConfigError(GRAY_TEST_ENVIRONMENT_SQL_EXECUTION_GRAY_REQUIRED)
        if feature.datasource_alias_id:
            binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
                feature.datasource_alias_id,
                feature.project_product_id,
                environment,
            )
        else:
            binding = DataFactoryDatasourceBinding.objects.select_related(
                'database',
                'datasource_alias',
            ).filter(
                datasource_alias__project_product_id=feature.project_product_id,
                database_id=feature.database_id,
            ).filter(
                environment=environment,
            ).order_by('id').first()
        if not binding:
            raise GrayConfigError(GRAY_TEST_ENVIRONMENT_DATABASE_BINDING_GRAY_INVALID)
        feature.runtime_database_id = binding.database_id
        result = DataSourceExecutionService.execute(
            datasource_alias_id=binding.datasource_alias_id,
            project_product_id=feature.project_product_id,
            test_env=environment,
            operation_config=sql,
            parameters=params,
            source_context=source_context or {
                'source_type': 'gray_config',
                'source_stage': 'execute',
                'source_id': getattr(feature, 'id', None),
                'gray_feature_id': getattr(feature, 'id', None),
            },
        )
        return int(result.get('affected_rows') or 0)

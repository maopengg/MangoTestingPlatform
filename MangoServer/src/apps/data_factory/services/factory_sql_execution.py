from __future__ import annotations

from collections.abc import Callable
from typing import Any

from time import perf_counter
from functools import wraps
from inspect import signature

from src.apps.data_factory.services.sql_execution_audit import (
    SqlExecutionAuditHandle,
    SqlExecutionAuditService,
)
from src.apps.data_factory.services.datasource_target import DatasourceTargetService


class DataFactorySqlExecutionService:
    """在数据工厂持有的业务库事务中执行 SQL，并统一写入物理 SQL 审计。"""

    SOURCE_TYPE = 'data_factory'

    @staticmethod
    def source_for(stage):
        def decorate(method):
            parameters = signature(method)

            @wraps(method)
            def wrapped(*args, **kwargs):
                values = parameters.bind(*args, **kwargs).arguments
                item = values.get('execution_item') or values.get('item')
                execution = values.get('execution') or getattr(item, 'execution', None)
                if execution is None:
                    return method(*args, **kwargs)
                context = DataFactorySqlExecutionService.build_source_context(
                    execution=execution, stage=stage, item=item, template=values.get('template'),
                    entity=values.get('entity'), alias=values.get('alias'),
                )
                with SqlExecutionAuditService.source(context):
                    return method(*args, **kwargs)
            return wrapped
        return decorate

    @staticmethod
    def resolve_test_env(binding) -> int:
        return int(binding.environment)

    @classmethod
    def build_source_context(
            cls,
            *,
            execution,
            stage: str,
            item=None,
            template=None,
            entity=None,
            alias: str | None = None,
    ) -> dict:
        template = template or getattr(item, 'template', None)
        entity = entity or getattr(template, 'entity', None)
        return {
            'source_type': cls.SOURCE_TYPE,
            'source_stage': stage,
            'source_id': getattr(item, 'id', None) or execution.id,
            'execution_id': execution.id,
            'execution_no': execution.execution_no,
            'execution_item_id': getattr(item, 'id', None),
            'template_id': getattr(template, 'id', None),
            'entity_id': getattr(entity, 'id', None),
            'alias': alias or getattr(item, 'alias', None),
            'case_source_type': getattr(execution, 'source_type', None),
            'case_source_id': getattr(execution, 'source_id', None),
            'execution_stage': getattr(execution, 'stage', None),
            'module_id': getattr(execution, 'module_id', None),
            'project_product_id': getattr(execution, 'project_product_id', None),
            'test_env': getattr(getattr(item, 'datasource_binding', None), 'environment', None),
        }

    @classmethod
    def execute(
            cls,
            *,
            connection,
            statement,
            binding,
            execution,
            stage: str,
            callback: Callable[[], tuple[Any, dict]],
            item=None,
            template=None,
            entity=None,
            alias: str | None = None,
    ) -> tuple[Any, SqlExecutionAuditHandle]:
        compiled = statement.compile(dialect=connection.dialect)
        sql = str(compiled)
        parameters = dict(compiled.params or {})
        started_at = perf_counter()
        handle = SqlExecutionAuditService.start(
            binding=binding,
            database=DatasourceTargetService.resolve(binding),
            project_product_id=execution.project_product_id,
            test_env=cls.resolve_test_env(binding),
            sql=sql,
            parameters=parameters,
            source_context=cls.build_source_context(
                execution=execution,
                stage=stage,
                item=item,
                template=template,
                entity=entity,
                alias=alias,
            ),
            request_id=None,
            started_monotonic=started_at,
        )
        started_at = perf_counter()
        try:
            with SqlExecutionAuditService.scope(handle):
                value, audit_result = callback()
            created_item = value.get('execution_item') if item is None and isinstance(value, dict) else None
            if created_item is not None:
                cls.bind_execution_item(handle, created_item)
        except Exception as error:
            SqlExecutionAuditService.finish_failure(
                handle,
                error,
                round((perf_counter() - started_at) * 1000, 2),
            )
            cls.mark_rolled_back(getattr(handle, 'children', []), error)
            raise
        SqlExecutionAuditService.finish_success(
            handle,
            audit_result,
            round((perf_counter() - started_at) * 1000, 2),
        )
        return value, handle

    @staticmethod
    def bind_execution_item(handle: SqlExecutionAuditHandle, item) -> None:
        record = handle.record
        detail = dict(record.source_detail or {})
        detail['execution_item_id'] = item.id
        detail['source_id'] = item.id
        record.source_id = item.id
        record.source_detail = detail
        record.save(update_fields=['source_id', 'source_detail', 'update_time'])
        for child in getattr(handle, 'children', []):
            DataFactorySqlExecutionService.bind_execution_item(child, item)

    @staticmethod
    def mark_rolled_back(handles: list[SqlExecutionAuditHandle], error: Exception) -> None:
        from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService
        unknown = DatasourceGovernorService.outcome_unknown(error)
        for handle in handles:
            record = handle.record
            record.status = 'fail' if unknown else 'rolled_back'
            record.error_message = ('数据工厂事务结果未知，需按执行快照核查，不自动重放'
                                    if unknown else '数据工厂业务事务已回滚，请结合执行来源查看失败原因')
            record.source_detail = {**record.source_detail, 'outcome_unknown': unknown}
            SqlExecutionAuditService.save_completion(
                record, update_fields=['status', 'error_message', 'source_detail', 'update_time'])
            DataFactorySqlExecutionService.mark_rolled_back(getattr(handle, 'children', []), error)

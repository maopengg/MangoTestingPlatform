from __future__ import annotations

from collections.abc import Callable
from typing import Any

from time import perf_counter

from src.apps.data_factory.services.sql_execution_audit import (
    SqlExecutionAuditHandle,
    SqlExecutionAuditService,
)


class DataFactorySqlExecutionService:
    """在数据工厂持有的业务库事务中执行 SQL，并统一写入物理 SQL 审计。"""

    SOURCE_TYPE = 'data_factory'

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
            'case_source_type': execution.source_type,
            'case_source_id': execution.source_id,
            'execution_stage': execution.stage,
            'module_id': getattr(execution, 'module_id', None),
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
        try:
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

    @staticmethod
    def mark_rolled_back(handles: list[SqlExecutionAuditHandle], error: Exception) -> None:
        message = SqlExecutionAuditService.sanitize(str(error))
        for handle in handles:
            record = handle.record
            record.status = 'rolled_back'
            record.error_message = f'数据工厂业务事务已回滚：{message}'[:2000]
            record.save(update_fields=['status', 'error_message', 'update_time'])

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂清理服务

from django.db import transaction
from django.utils import timezone

from src.apps.auto_data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.common.enums.data_factory_enum import (
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryOperationTypeEnum,
)
from src.common.exceptions import ToolsError

from .datasource import DataFactoryDatasource
from .datasource import DataFactoryDatasourceResolver
from .type_cast import DataFactoryTypeCast


class DataFactoryCleanup:
    @classmethod
    @transaction.atomic
    def cleanup_execution(
            cls,
            execution_id: int,
            force_cleanup: bool = False,
            allow_missing: bool = False,
    ) -> dict:
        execution = DataFactoryExecution.objects.get(id=execution_id)
        if execution.cleanup_status == DataFactoryCleanupStatusEnum.SUCCESS.value and not force_cleanup:
            return {
                "execution_id": execution.id,
                "success": 0,
                "fail": 0,
                "skipped": 0,
                "errors": [],
                "already_cleaned": True,
                "message": "当前执行记录已清理，无需重复清理",
            }

        all_items = list(
            DataFactoryExecutionItem.objects
            .select_related('template__entity', 'database')
            .filter(execution=execution)
            .order_by('-cleanup_order', '-id')
        )
        items = all_items
        if not force_cleanup:
            items = [
                item
                for item in items
                if item.cleanup_status != DataFactoryCleanupStatusEnum.SUCCESS.value
            ]
        if not items:
            execution.cleanup_time = timezone.now()
            execution.cleanup_status = (
                DataFactoryCleanupStatusEnum.SUCCESS.value
                if all_items
                else DataFactoryCleanupStatusEnum.SKIPPED.value
            )
            execution.save(update_fields=['cleanup_time', 'cleanup_status', 'update_time'])
            return {
                "execution_id": execution.id,
                "success": 0,
                "fail": 0,
                "skipped": 0,
                "errors": [],
                "already_cleaned": True,
                "message": "当前执行记录没有需要清理的数据",
            }

        cleanup_items = []
        skipped_items = []
        errors = []
        fail = 0
        for item in items:
            if item.cleanup_strategy == DataFactoryCleanupStrategyEnum.NONE.value:
                skipped_items.append(item)
                continue
            try:
                cls.validate_cleanup_item(item)
            except Exception as error:
                error_message = str(error)
                errors.append({"item_ids": [item.id], "error": error_message})
                fail += 1
                cls.mark_failed(item, error_message)
                continue
            cleanup_items.append(item)

        success = 0
        if cleanup_items:
            effective_allow_missing = force_cleanup or allow_missing
            items_by_database: dict[int, list[DataFactoryExecutionItem]] = {}
            for item in cleanup_items:
                items_by_database.setdefault(item.database_id, []).append(item)
            for database_items in items_by_database.values():
                try:
                    cls.cleanup_items_in_database_transaction(
                        database_items,
                        allow_missing=effective_allow_missing,
                    )
                except Exception as error:
                    error_message = str(error)
                    errors.append({"item_ids": [item.id for item in database_items], "error": error_message})
                    fail += len(database_items)
                    for item in database_items:
                        cls.mark_failed(item, error_message)
                else:
                    for item in database_items:
                        cls.mark_success(item)
                    success += len(database_items)

        skipped = 0
        for item in skipped_items:
            cls.mark_skipped(item)
        skipped = len(skipped_items)

        execution.cleanup_time = timezone.now()
        if fail:
            execution.cleanup_status = DataFactoryCleanupStatusEnum.FAIL.value
        elif skipped and not success:
            execution.cleanup_status = DataFactoryCleanupStatusEnum.SKIPPED.value
        else:
            execution.cleanup_status = DataFactoryCleanupStatusEnum.SUCCESS.value
        execution.save()

        return {
            "execution_id": execution.id,
            "success": success,
            "fail": fail,
            "skipped": skipped,
            "errors": errors,
            "force_cleanup": force_cleanup,
        }

    @classmethod
    def cleanup_item(cls, item: DataFactoryExecutionItem, allow_missing: bool = False):
        cls.validate_cleanup_item(item)

        cls.delete_by_primary_key(item, allow_missing=allow_missing)
        cls.mark_success(item)

    @classmethod
    def validate_cleanup_item(cls, item: DataFactoryExecutionItem):
        entity = cls.get_item_entity(item)
        if entity.delete_type != DataFactoryOperationTypeEnum.SQL.value:
            raise ToolsError(300, "当前阶段仅支持 SQL 删除方式")
        if not item.database:
            raise ToolsError(300, f"执行明细 {item.id} 未记录实际数据库，无法安全清理")
        DataFactoryDatasourceResolver.require_permission(item.database.test_object_id, write=True)
        if not entity.table_name:
            raise ToolsError(300, f"实体 {entity.name} 未配置表名")
        if not item.primary_value:
            raise ToolsError(300, f"执行明细 {item.id} 缺少主键值，无法清理")

    @classmethod
    def cleanup_items_in_database_transaction(cls, items: list[DataFactoryExecutionItem], allow_missing: bool = False):
        if not items:
            return
        database_ids = {item.database_id for item in items}
        if len(database_ids) > 1:
            raise ToolsError(300, "一次清理涉及多个业务库，无法保证跨库事务一致性，请拆分后清理")

        database = items[0].database
        engine, managed_by_worker = DataFactoryDatasource.get_worker_engine(database)
        try:
            from sqlalchemy import MetaData

            metadata = MetaData()
            with engine.begin() as connection:
                for item in items:
                    cls.delete_by_primary_key(
                        item,
                        allow_missing=allow_missing,
                        engine=engine,
                        connection=connection,
                        metadata=metadata,
                    )
        except ImportError as error:
            raise ToolsError(300, "请先安装 SQLAlchemy 依赖后再使用数据工厂") from error
        finally:
            if not managed_by_worker:
                engine.dispose()

    @classmethod
    def delete_by_primary_key(
            cls,
            item: DataFactoryExecutionItem,
            allow_missing: bool = False,
            engine=None,
            connection=None,
            metadata=None,
    ):
        try:
            from sqlalchemy import MetaData, Table, delete
        except ImportError as error:
            raise ToolsError(300, "请先安装 SQLAlchemy 依赖后再使用数据工厂") from error

        entity = cls.get_item_entity(item)
        if not item.database:
            raise ToolsError(300, f"执行明细 {item.id} 未记录实际数据库，无法安全清理")
        own_engine = engine is None
        managed_by_worker = False
        if engine is None:
            engine, managed_by_worker = DataFactoryDatasource.get_worker_engine(item.database)
        metadata = metadata or MetaData()
        try:
            table = Table(entity.table_name, metadata, autoload_with=engine, extend_existing=True)
            primary_column = table.c[entity.primary_key]
            primary_value = item.data.get(entity.primary_key, item.primary_value)
            statement = delete(table).where(primary_column == primary_value)
            cls.record_cleanup_sql(item, statement, engine)
            if connection is None:
                with engine.begin() as connection:
                    result = connection.execute(statement)
                    cls.validate_delete_result(
                        item,
                        result,
                        entity.table_name,
                        entity.primary_key,
                        primary_value,
                        allow_missing=allow_missing,
                    )
            else:
                result = connection.execute(statement)
                cls.validate_delete_result(
                    item,
                    result,
                    entity.table_name,
                    entity.primary_key,
                    primary_value,
                    allow_missing=allow_missing,
                )
        except Exception as error:
            raise ToolsError(300, f"SQL清理数据失败：{error}") from error
        finally:
            if own_engine and not managed_by_worker:
                engine.dispose()

    @staticmethod
    def validate_delete_result(
            item: DataFactoryExecutionItem,
            result,
            table_name: str,
            primary_key: str,
            primary_value,
            allow_missing: bool = False,
    ):
        rowcount = getattr(result, "rowcount", None)
        if rowcount == 0 and not allow_missing:
            raise ToolsError(
                300,
                f"SQL清理数据未命中任何记录：执行明细 {item.id}，表 {table_name}，"
                f"主键 {primary_key}={primary_value}",
            )

    @staticmethod
    def record_cleanup_sql(item: DataFactoryExecutionItem, statement, engine):
        cleanup_sql, cleanup_sql_params = DataFactoryCleanup.compile_cleanup_sql(statement, engine.dialect)
        item.cleanup_sql = cleanup_sql
        item.cleanup_sql_params = cleanup_sql_params
        item.save(update_fields=['cleanup_sql', 'cleanup_sql_params', 'update_time'])

    @staticmethod
    def compile_cleanup_sql(statement, dialect):
        compiled = statement.compile(dialect=dialect)
        return str(compiled), DataFactoryTypeCast.to_jsonable(dict(compiled.params or {}))

    @staticmethod
    def get_item_entity(item: DataFactoryExecutionItem):
        if not item.template_id or not item.template:
            raise ToolsError(300, f"执行明细 {item.id} 未记录模板，无法推导清理实体")
        return item.template.entity

    @staticmethod
    def mark_success(item: DataFactoryExecutionItem):
        item.cleanup_status = DataFactoryCleanupStatusEnum.SUCCESS.value
        item.cleanup_time = timezone.now()
        item.cleanup_error = None
        item.save(update_fields=[
            'cleanup_status',
            'cleanup_time',
            'cleanup_error',
            'cleanup_sql',
            'cleanup_sql_params',
            'update_time',
        ])

    @staticmethod
    def mark_failed(item: DataFactoryExecutionItem, error: str):
        item.cleanup_status = DataFactoryCleanupStatusEnum.FAIL.value
        item.cleanup_error = error
        item.cleanup_time = timezone.now()
        item.save(update_fields=['cleanup_status', 'cleanup_error', 'cleanup_time', 'update_time'])

    @staticmethod
    def mark_skipped(item: DataFactoryExecutionItem):
        item.cleanup_status = DataFactoryCleanupStatusEnum.SKIPPED.value
        item.cleanup_time = timezone.now()
        item.save(update_fields=['cleanup_status', 'cleanup_time', 'update_time'])

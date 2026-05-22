# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂清理服务

from django.db import transaction
from django.utils import timezone

from src.auto_test.auto_data_factory.models import DataFactoryExecution, DataFactoryExecutionItem
from src.enums.data_factory_enum import (
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryOperationTypeEnum,
)
from src.exceptions import ToolsError

from .datasource import DataFactoryDatasource
from .type_cast import DataFactoryTypeCast


class DataFactoryCleanup:
    @classmethod
    @transaction.atomic
    def cleanup_execution(cls, execution_id: int) -> dict:
        execution = DataFactoryExecution.objects.get(id=execution_id)
        if execution.cleanup_status == DataFactoryCleanupStatusEnum.SUCCESS.value:
            return {
                "execution_id": execution.id,
                "success": 0,
                "fail": 0,
                "skipped": 0,
                "errors": [],
                "already_cleaned": True,
                "message": "当前执行记录已清理，无需重复清理",
            }

        items = list(
            DataFactoryExecutionItem.objects
            .select_related('template__entity', 'database')
            .filter(execution=execution)
            .exclude(cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value)
            .order_by('-cleanup_order', '-id')
        )
        if not items:
            return {
                "execution_id": execution.id,
                "success": 0,
                "fail": 0,
                "skipped": 0,
                "errors": [],
                "already_cleaned": True,
                "message": "当前执行记录没有需要清理的数据",
            }

        success = 0
        fail = 0
        skipped = 0
        errors = []

        for item in items:
            try:
                if item.cleanup_strategy == DataFactoryCleanupStrategyEnum.NONE.value:
                    cls.mark_skipped(item)
                    skipped += 1
                    continue
                cls.cleanup_item(item)
                success += 1
            except Exception as error:
                fail += 1
                errors.append({"item_id": item.id, "error": str(error)})
                cls.mark_failed(item, str(error))

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
        }

    @classmethod
    def cleanup_item(cls, item: DataFactoryExecutionItem):
        entity = cls.get_item_entity(item)
        if entity.delete_type != DataFactoryOperationTypeEnum.SQL.value:
            raise ToolsError(300, "当前阶段仅支持 SQL 删除方式")
        if not item.database:
            raise ToolsError(300, f"执行明细 {item.id} 未记录实际数据库，无法安全清理")
        if not entity.table_name:
            raise ToolsError(300, f"实体 {entity.name} 未配置表名")
        if not item.primary_value:
            raise ToolsError(300, f"执行明细 {item.id} 缺少主键值，无法清理")

        cls.delete_by_primary_key(item)
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

    @classmethod
    def delete_by_primary_key(cls, item: DataFactoryExecutionItem):
        try:
            from sqlalchemy import MetaData, Table, delete
        except ImportError as error:
            raise ToolsError(300, "请先安装 SQLAlchemy 依赖后再使用数据工厂") from error

        entity = cls.get_item_entity(item)
        if not item.database:
            raise ToolsError(300, f"执行明细 {item.id} 未记录实际数据库，无法安全清理")
        engine = DataFactoryDatasource.create_engine(item.database)
        try:
            metadata = MetaData()
            table = Table(entity.table_name, metadata, autoload_with=engine)
            primary_column = table.c[entity.primary_key]
            primary_value = item.data.get(entity.primary_key, item.primary_value)
            statement = delete(table).where(primary_column == primary_value)
            cls.record_cleanup_sql(item, statement, engine)
            with engine.begin() as connection:
                connection.execute(statement)
        except Exception as error:
            raise ToolsError(300, f"SQL清理数据失败：{error}") from error
        finally:
            engine.dispose()

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

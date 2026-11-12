from django.db import transaction
from django.utils import timezone

from src.apps.data_factory.enums import (
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionStatusEnum,
)
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_CONFIG_INVALID,
    DATA_FACTORY_CLEANUP_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID,
    DATA_FACTORY_CLEANUP_ENTITY_CONFIG_REQUIRED,
    DATA_FACTORY_CLEANUP_EXECUTION_CLEANUP_REQUIRED,
    DATA_FACTORY_CLEANUP_CLEANUP_INVALID,
    DATA_FACTORY_CLEANUP_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID_CODE_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID,
    DATA_FACTORY_CLEANUP_SQL_RECORD_EXECUTION_CLEANUP_INVALID,
    DATA_FACTORY_CLEANUP_ENTITY_RECORD_TEMPLATE_EXECUTION_CLEANUP_INVALID,
    DATA_FACTORY_CLEANUP_SQL_INVALID,
    DATA_FACTORY_CLEANUP_SQL_INVALID_CODE_SQL_INVALID,
    DATA_FACTORY_CLEANUP_SQL_CLEANUP_FAILED,
    DATA_FACTORY_CLEANUP_INVALID,
    DataFactoryError,
)
from src.apps.data_factory.models import (
    DataFactoryExecution,
    DataFactoryExecutionItem,
)
from src.common.logging import log
from src.common.exceptions.base import MangoServerError
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasource, is_missing_value
from src.apps.data_factory.services.datasource.datasource import DataFactoryDatasourceResolver
from src.apps.data_factory.services.datasource.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.execution.execution_snapshot import DATA_FACTORY_INSERT_SNAPSHOT_KEY, get_insert_snapshot
from src.apps.data_factory.services.sql.factory_sql_execution import DataFactorySqlExecutionService
from src.apps.data_factory.services.execution.type_cast import DataFactoryTypeCast
from src.apps.data_factory.services.cleanup.cleanup_persistence import CleanupPersistenceService
from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂清理服务


class DataFactoryCleanup:
    @staticmethod
    def clear_resolved_cleanup_error(execution):
        # 创建本身失败时必须保留原失败；仅清理成功不代表造数/业务成功。
        if (getattr(execution, 'status', None) == DataFactoryExecutionStatusEnum.SUCCESS.value
                and execution.cleanup_status == DataFactoryCleanupStatusEnum.SUCCESS.value):
            execution.error_message = None

    CLEANABLE_STATUSES = {
        DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
        DataFactoryCleanupStatusEnum.FAIL.value,
        DataFactoryCleanupStatusEnum.PENDING_MANUAL.value,
    }
    ACTIVE_EXECUTION_STATUSES = {
        DataFactoryExecutionStatusEnum.PENDING.value,
        DataFactoryExecutionStatusEnum.PROCEED.value,
    }

    @classmethod
    def is_cleanup_required(cls, execution: DataFactoryExecution) -> bool:
        """仅允许清理已结束且仍存在清理责任的执行记录。"""
        return (
                execution.cleanup_status in cls.CLEANABLE_STATUSES
                and execution.status not in cls.ACTIVE_EXECUTION_STATUSES
        )

    @classmethod
    def cleanup_execution_on_demand(cls, execution_id: int) -> dict:
        execution = DataFactoryExecution.objects.get(id=execution_id)
        if not cls.is_cleanup_required(execution):
            return {
                "execution_id": execution.id,
                "success": 0,
                "fail": 0,
                "skipped": 1,
                "errors": [],
                "already_cleaned": True,
                "cleanup_required": False,
                "message": "当前执行记录状态无需清理",
            }
        result = cls.cleanup_execution(
            execution.id,
            force_cleanup=True,
            allow_missing=True,
            controlled_retry=True,
        )
        result["cleanup_required"] = True
        return result

    @classmethod
    def batch_cleanup_executions(cls, execution_ids: list[int]) -> dict:
        """逐条隔离批量清理，单条失败不影响其余 execution。"""
        executions = {
            execution.id: execution
            for execution in DataFactoryExecution.objects.filter(id__in=execution_ids)
        }
        results = []
        succeeded = 0
        failed = 0
        skipped = 0
        for execution_id in execution_ids:
            execution = executions.get(execution_id)
            if execution is None:
                failed += 1
                results.append({
                    "execution_id": execution_id,
                    "status": "failed",
                    "message": "执行记录不存在",
                })
                continue
            if not cls.is_cleanup_required(execution):
                skipped += 1
                results.append({
                    "execution_id": execution_id,
                    "execution_no": execution.execution_no,
                    "status": "skipped",
                    "message": "当前执行记录状态无需清理",
                })
                continue
            try:
                result = cls.cleanup_execution(
                    execution_id,
                    force_cleanup=True,
                    allow_missing=True,
                    controlled_retry=True,
                )
            except DataFactoryError as error:
                failed += 1
                results.append({
                    "execution_id": execution_id,
                    "execution_no": execution.execution_no,
                    "status": "failed",
                    "message": str(error),
                })
                continue
            except Exception as error:
                failed += 1
                log.system.exception(
                    f'批量清理数据工厂执行记录异常，execution_id={execution_id}，错误：{error}'
                )
                results.append({
                    "execution_id": execution_id,
                    "execution_no": execution.execution_no,
                    "status": "failed",
                    "message": "清理执行记录失败，请查看执行明细",
                })
                continue

            if result.get("fail"):
                failed += 1
                status = "failed"
                message = "存在清理失败明细"
            else:
                succeeded += 1
                status = "success"
                message = result.get("message") or "清理成功"
            results.append({
                "execution_id": execution_id,
                "execution_no": execution.execution_no,
                "status": status,
                "message": message,
                "cleanup_result": result,
            })

        return {
            "total": len(execution_ids),
            "success": succeeded,
            "fail": failed,
            "skipped": skipped,
            "results": results,
        }

    @staticmethod
    def sync_workbench_todo(execution: DataFactoryExecution):
        """待办同步是旁路能力，失败不能改变清理结果。"""
        try:
            from src.apps.task_center.services.workbench.todo import WorkbenchTodoService

            if execution.cleanup_status == DataFactoryCleanupStatusEnum.FAIL.value:
                WorkbenchTodoService.record_data_factory_cleanup_failure(execution)
                WorkbenchTodoService.resolve_data_factory_cleanup_required_todos(execution.id)
            else:
                WorkbenchTodoService.resolve_data_factory_cleanup_todos(execution.id)
        except Exception as error:
            log.system.error(
                f'同步数据工厂清理失败待办异常，execution_id={execution.id}，错误：{error}'
            )

    @classmethod
    def mark_execution_failed(
            cls,
            execution: DataFactoryExecution,
            error: str,
            mark_pending_items: bool = True,
    ) -> None:
        cleanup_time = timezone.now()
        if mark_pending_items:
            CleanupPersistenceService.write(lambda: DataFactoryExecutionItem.objects.filter(
                execution=execution,
                cleanup_status__in=[
                    DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
                    DataFactoryCleanupStatusEnum.SKIPPED.value,
                    DataFactoryCleanupStatusEnum.PENDING_MANUAL.value,
                ],
            ).update(
                cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value,
                cleanup_time=cleanup_time,
                cleanup_error=error,
                update_time=cleanup_time,
            ))
        execution.cleanup_status = DataFactoryCleanupStatusEnum.FAIL.value
        execution.cleanup_time = cleanup_time
        execution.error_message = error
        CleanupPersistenceService.save(execution, ['cleanup_status', 'cleanup_time', 'error_message', 'update_time'])
        transaction.on_commit(lambda: cls.sync_workbench_todo(execution))

    @classmethod
    def cleanup_execution(
            cls,
            execution_id: int,
            force_cleanup: bool = False,
            allow_missing: bool = False,
            defer_resources: bool = False,
            controlled_retry: bool = False,
            created_by: int | None = None,
    ) -> dict:
        execution = DataFactoryExecution.objects.get(id=execution_id)
        if execution.cleanup_status == DataFactoryCleanupStatusEnum.SUCCESS.value and not force_cleanup:
            return {
                'execution_id': execution.id, 'success': 0, 'fail': 0, 'skipped': 0, 'errors': [],
                'already_cleaned': True, 'message': '当前执行记录已清理，无需重复清理',
            }
        if not defer_resources:
            from src.apps.data_factory.services.cleanup.cleanup_schedule import DataFactoryCleanupScheduleService
            failure = None
            task_id = None
            try:
                task_id = DataFactoryCleanupScheduleService.execute(
                    execution, created_by=created_by, controlled_retry=controlled_retry,
                    force_cleanup=force_cleanup, allow_missing=allow_missing)
            except MangoServerError as error:
                DatasourceInfrastructureService.capture_cleanup(error)
                from src.apps.data_factory.exceptions import DATA_FACTORY_CLEANUP_IN_PROGRESS
                if not (isinstance(error, DataFactoryError) and error.code == DATA_FACTORY_CLEANUP_IN_PROGRESS.code):
                    DataFactoryCleanupScheduleService.record_wait_failure(execution_id)
                failure = error.msg
            statuses = list(DataFactoryExecutionItem.objects.filter(execution_id=execution_id).values_list(
                'cleanup_status', flat=True))
            return {
                'execution_id': execution_id, 'cleanup_task_id': task_id,
                'success': statuses.count(DataFactoryCleanupStatusEnum.SUCCESS.value),
                'fail': max(int(failure is not None), statuses.count(DataFactoryCleanupStatusEnum.FAIL.value)),
                'skipped': sum(value in (DataFactoryCleanupStatusEnum.SKIPPED.value,
                                        DataFactoryCleanupStatusEnum.PENDING_MANUAL.value) for value in statuses),
                'errors': [{'error': failure}] if failure else [], 'force_cleanup': force_cleanup,
                'message': (f'工厂执行 {execution_id} 未完成清理：{failure}' if failure else
                            '已按策略清理；保留的数据未删除' if any(value != DataFactoryCleanupStatusEnum.SUCCESS.value
                                                               for value in statuses) else '清理完成'),
            }
        all_items = list(
            DataFactoryExecutionItem.objects
            .select_related('execution', 'template__entity', 'database', 'datasource_binding')
            .filter(execution=execution)
            .order_by('cleanup_order', '-id')
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
            cls.clear_resolved_cleanup_error(execution)
            CleanupPersistenceService.save(execution, ['cleanup_time', 'cleanup_status', 'error_message', 'update_time'])
            transaction.on_commit(lambda: cls.sync_workbench_todo(execution))
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
        resource_only_items = []
        skipped_items = []
        errors = []
        fail = 0
        for item in items:
            if (
                    item.cleanup_strategy == DataFactoryCleanupStrategyEnum.NONE.value
                    and not force_cleanup
            ):
                skipped_items.append(item)
                continue
            try:
                from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService
                resource_state = DataFactoryCleanupResourceService.validate_snapshot(item)
                if resource_state.sql_cleaned:
                    resource_only_items.append(item)
                    continue
                cls.validate_cleanup_item(
                    item,
                    recover_missing_primary=force_cleanup,
                )
            except Exception as error:
                error_message = str(error)
                DatasourceInfrastructureService.capture_cleanup(error)
                errors.append({"item_ids": [item.id], "error": error_message})
                fail += 1
                cls.mark_failed(item, error_message)
                continue
            cleanup_items.append(item)

        success = 0
        pending = 0
        if cleanup_items:
            effective_allow_missing = force_cleanup or allow_missing
            items_by_database: dict[int, list[DataFactoryExecutionItem]] = {}
            for item in cleanup_items:
                try:
                    target = DatasourceTargetService.from_snapshot(item.database, get_insert_snapshot(item))
                except DataFactoryError as error:
                    fail += 1
                    errors.append({"item_ids": [item.id], "error": str(error)})
                    cls.mark_failed(item, str(error))
                    continue
                items_by_database.setdefault(target.cache_key, []).append(item)
            for database_items in items_by_database.values():
                try:
                    cls.cleanup_items_in_database_transaction(
                        database_items,
                        allow_missing=effective_allow_missing,
                    )
                except Exception as error:
                    error_message = str(error)
                    DatasourceInfrastructureService.capture_cleanup(error)
                    errors.append({"item_ids": [item.id for item in database_items], "error": error_message})
                    fail += len(database_items)
                    for item in database_items:
                        cls.mark_failed(item, error_message)
                else:
                    for item in database_items:
                        try:
                            finished = cls.finish_resource_cleanup(item, defer_resources=defer_resources)
                        except Exception as error:
                            DatasourceInfrastructureService.capture_cleanup(error)
                            fail += 1
                            errors.append({'item_ids': [item.id], 'error': str(error)})
                            cls.mark_failed(item, str(error))
                        else:
                            if finished is False:
                                pending += 1
                            else:
                                success += 1

        for item in resource_only_items:
            try:
                finished = cls.finish_resource_cleanup(item, defer_resources=defer_resources)
            except Exception as error:
                fail += 1
                DatasourceInfrastructureService.capture_cleanup(error)
                errors.append({'item_ids': [item.id], 'error': str(error)})
                cls.mark_failed(item, str(error))
            else:
                if finished is False:
                    pending += 1
                else:
                    success += 1

        skipped = 0
        for item in skipped_items:
            cls.mark_skipped(item)
        skipped = len(skipped_items)

        execution.cleanup_time = timezone.now()
        if fail:
            execution.cleanup_status = DataFactoryCleanupStatusEnum.FAIL.value
        elif pending:
            execution.cleanup_status = DataFactoryCleanupStatusEnum.NOT_CLEANED.value
            execution.cleanup_time = None
        elif skipped:
            execution.cleanup_status = DataFactoryCleanupStatusEnum.SKIPPED.value
        else:
            execution.cleanup_status = DataFactoryCleanupStatusEnum.SUCCESS.value
        cls.clear_resolved_cleanup_error(execution)
        CleanupPersistenceService.save(execution)
        transaction.on_commit(lambda: cls.sync_workbench_todo(execution))

        return {
            "execution_id": execution.id,
            "success": success,
            "pending": pending,
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
    def manual_cleanup_item_exists(cls, item: DataFactoryExecutionItem) -> bool:
        """按执行快照中的精确主键检查手动清理数据是否仍然存在。"""
        try:
            from sqlalchemy import MetaData, Table, func, select
        except ImportError as error:
            raise DataFactoryError(DATA_FACTORY_CLEANUP_SQL_INVALID) from error

        entity = cls.get_item_entity(item)
        if not item.database:
            raise DataFactoryError(
                DATA_FACTORY_CLEANUP_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID,
                value=(item.id,),
            )
        binding, recovered = cls.resolve_cleanup_binding(item, entity)
        DataFactoryDatasourceResolver.require_binding_permission(binding)
        if recovered:
            item.datasource_binding = binding
            item.datasource_binding_id = binding.id
            CleanupPersistenceService.save(item, ['datasource_binding', 'update_time'])

        snapshot = get_insert_snapshot(item)
        table_name = snapshot.get('table_name') or entity.table_name
        primary_key = snapshot.get('primary_key') or entity.primary_key
        if not table_name or not primary_key or is_missing_value(item.primary_value):
            raise DataFactoryError(
                DATA_FACTORY_CLEANUP_EXECUTION_CLEANUP_REQUIRED,
                value=(item.id,),
            )

        engine, managed_by_worker = DataFactoryDatasource.get_worker_engine(
            DatasourceTargetService.from_snapshot(item.database, get_insert_snapshot(item)))
        try:
            table = Table(table_name, MetaData(), schema=snapshot['schema_name'] or None, autoload_with=engine)
            primary_column = table.c[primary_key]
            statement = (
                select(func.count())
                .select_from(table)
                .where(primary_column == item.primary_value)
            )
            with engine.connect() as connection:
                def execute_check():
                    count = int(connection.execute(statement).scalar() or 0)
                    return count, {
                        'columns': ['residual_count'],
                        'rows': [{'residual_count': count}],
                        'row_count': 1,
                        'affected_rows': 0,
                    }

                count, _audit_handle = DataFactorySqlExecutionService.execute(
                    connection=connection,
                    statement=statement,
                    binding=item.datasource_binding,
                    execution=item.execution,
                    stage='cleanup_pending_check',
                    callback=execute_check,
                    item=item,
                    entity=entity,
                )
            return count > 0
        finally:
            if not managed_by_worker:
                engine.dispose()

    @classmethod
    def validate_cleanup_item(
            cls,
            item: DataFactoryExecutionItem,
            recover_missing_primary: bool = False,
    ):
        entity = cls.get_item_entity(item)
        snapshot = get_insert_snapshot(item)
        if not item.database:
            raise DataFactoryError(DATA_FACTORY_CLEANUP_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID, value=(item.id,))
        binding, recovered = cls.resolve_cleanup_binding(item, entity)
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=True)
        if recovered:
            item.datasource_binding = binding
            item.datasource_binding_id = binding.id
            CleanupPersistenceService.save(item, ['datasource_binding', 'update_time'])
        if not (snapshot.get('table_name') or entity.table_name):
            raise DataFactoryError(DATA_FACTORY_CLEANUP_ENTITY_CONFIG_REQUIRED, value=(entity.name,))
        if not item.primary_value and recover_missing_primary:
            cls.recover_missing_primary_value(item, entity)
        if not item.primary_value:
            raise DataFactoryError(DATA_FACTORY_CLEANUP_EXECUTION_CLEANUP_REQUIRED, value=(item.id,))

    @classmethod
    def recover_missing_primary_value(cls, item: DataFactoryExecutionItem, entity) -> bool:
        """强制清理历史明细时，仅按已记录的唯一字段精确恢复真实主键。"""
        unique_key = str(getattr(entity, 'unique_key', '') or '')
        lookup_data = item.insert_data if isinstance(item.insert_data, dict) else {}
        fallback_data = item.data if isinstance(item.data, dict) else {}
        lookup_value = lookup_data.get(unique_key, fallback_data.get(unique_key))
        if not unique_key or lookup_value in (None, ''):
            return False

        engine, managed_by_worker = DataFactoryDatasource.get_worker_engine(
            DatasourceTargetService.from_snapshot(item.database, get_insert_snapshot(item)))
        try:
            from sqlalchemy import MetaData, Table, select

            snapshot = get_insert_snapshot(item)
            table_name = snapshot.get('table_name') or entity.table_name
            table = Table(table_name, MetaData(), schema=snapshot['schema_name'] or None, autoload_with=engine)
            primary_columns = list(table.primary_key.columns)
            if len(primary_columns) != 1 or unique_key not in table.c:
                return False
            primary_column = primary_columns[0]
            with engine.connect() as connection:
                statement = (
                    select(primary_column)
                    .where(table.c[unique_key] == lookup_value)
                    .limit(2)
                )

                def execute_lookup():
                    rows = connection.execute(statement).all()
                    return rows, {
                        'columns': [primary_column.name],
                        'rows': [{primary_column.name: row[0]} for row in rows],
                        'row_count': len(rows),
                        'affected_rows': 0,
                    }

                rows, _audit_handle = DataFactorySqlExecutionService.execute(
                    connection=connection,
                    statement=statement,
                    binding=item.datasource_binding,
                    execution=item.execution,
                    stage='cleanup_primary_recovery',
                    callback=execute_lookup,
                    item=item,
                    entity=entity,
                )
            if len(rows) != 1 or is_missing_value(rows[0][0]):
                return False

            primary_value = rows[0][0]
            item.primary_value = str(primary_value)
            item.data = {
                **fallback_data,
                primary_column.name: DataFactoryTypeCast.to_jsonable(primary_value),
            }
            params = dict(item.insert_sql_params or {})
            repaired_snapshot = dict(snapshot)
            repaired_snapshot['primary_key'] = primary_column.name
            params[DATA_FACTORY_INSERT_SNAPSHOT_KEY] = repaired_snapshot
            item.insert_sql_params = params
            CleanupPersistenceService.save(item, [
                'primary_value',
                'data',
                'insert_sql_params',
                'update_time',
            ])
            return True
        finally:
            if not managed_by_worker:
                engine.dispose()

    @classmethod
    def finish_resource_cleanup(cls, item, *, defer_resources=False):
        from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService
        DataFactoryCleanupResourceService.mark_sql_cleaned(item)
        if defer_resources and DataFactoryCleanupResourceService.state(item).snapshots:
            return False
        DataFactoryCleanupResourceService.verify(item)
        cls.mark_success(item)
        return True

    @staticmethod
    def resolve_cleanup_binding(item: DataFactoryExecutionItem, entity):
        """清理仅接受执行时记录的环境绑定，不根据当前配置猜测目标。"""
        if item.datasource_binding_id:
            return item.datasource_binding, False
        raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('执行缺少环境绑定快照，禁止自动清理',))

    @classmethod
    def cleanup_items_in_database_transaction(cls, items: list[DataFactoryExecutionItem], allow_missing: bool = False):
        if not items:
            return
        database_ids = {DatasourceTargetService.from_snapshot(item.database, get_insert_snapshot(item)).cache_key for
                        item in items}
        if len(database_ids) > 1:
            raise DataFactoryError(DATA_FACTORY_CLEANUP_CLEANUP_INVALID)

        database = DatasourceTargetService.from_snapshot(items[0].database, get_insert_snapshot(items[0]))
        engine, managed_by_worker = DataFactoryDatasource.get_worker_engine(database)
        try:
            from sqlalchemy import MetaData
            from src.apps.data_factory.services.sql.sql_execution_audit import SqlExecutionAuditService
            from src.apps.data_factory.services.cleanup.cleanup_resource import DataFactoryCleanupResourceService
            context = DataFactorySqlExecutionService.build_source_context(
                execution=items[0].execution, item=items[0], stage='cleanup')
            with SqlExecutionAuditService.source(context):
                batch_size = min(100, len(items))
                for offset in range(0, len(items), batch_size):
                    batch = items[offset:offset + batch_size]
                    metadata = MetaData()
                    for item in batch:
                        cls.reflect_cleanup_table(item, metadata, engine, database)
                    audit_handles = []
                    committed = False
                    try:
                        with engine.begin() as connection:
                            for item in batch:
                                cls.delete_by_primary_key(
                                    item, allow_missing=allow_missing, engine=engine, connection=connection,
                                    metadata=metadata, audit_handles=audit_handles,
                                )
                        committed = True
                        for item in batch:
                            DataFactoryCleanupResourceService.mark_sql_cleaned(item)
                    except Exception as error:
                        if not committed:
                            DataFactorySqlExecutionService.mark_rolled_back(audit_handles, error)
                        raise
        except ImportError as error:
            raise DataFactoryError(DATA_FACTORY_CLEANUP_SQL_INVALID) from error
        finally:
            if not managed_by_worker:
                engine.dispose()

    @classmethod
    @DataFactorySqlExecutionService.source_for('cleanup_metadata')
    def reflect_cleanup_table(cls, item, metadata, engine, database):
        from sqlalchemy import Table
        snapshot = get_insert_snapshot(item)
        schema = snapshot['schema_name'] or None
        name = snapshot['table_name']
        key = f'{schema}.{name}' if schema else name
        if key in metadata.tables:
            return metadata.tables[key]
        # 反射结束后只按原冻结主键清理，不修改查询或跳过回查。
        table = Table(name, metadata, schema=schema, autoload_with=engine)
        primary = list(table.primary_key.columns)
        if len(primary) != 1 or primary[0].name != snapshot['primary_key']:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('真实表主键与执行快照不一致，禁止清理',))
        return table

    @classmethod
    @DataFactorySqlExecutionService.source_for('cleanup')
    def delete_by_primary_key(
            cls,
            item: DataFactoryExecutionItem,
            allow_missing: bool = False,
            engine=None,
            connection=None,
            metadata=None,
            audit_handles=None,
    ):
        try:
            from sqlalchemy import MetaData, Table, delete, func, select
        except ImportError as error:
            raise DataFactoryError(DATA_FACTORY_CLEANUP_SQL_INVALID_CODE_SQL_INVALID) from error

        entity = cls.get_item_entity(item)
        if not item.database:
            raise DataFactoryError(
                DATA_FACTORY_CLEANUP_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID_CODE_DATABASE_RECORD_EXECUTION_CLEANUP_INVALID,
                value=(item.id,))
        own_engine = engine is None
        managed_by_worker = False
        if engine is None:
            engine, managed_by_worker = DataFactoryDatasource.get_worker_engine(
                DatasourceTargetService.from_snapshot(item.database, get_insert_snapshot(item)))
        metadata = metadata or MetaData()
        local_audit_handles = audit_handles if audit_handles is not None else []
        try:
            snapshot = get_insert_snapshot(item)
            table_name = snapshot.get('table_name') or entity.table_name
            primary_key = snapshot.get('primary_key') or entity.primary_key
            schema = snapshot['schema_name'] or None
            key = f'{schema}.{table_name}' if schema else table_name
            table = metadata.tables.get(key)
            if table is None:
                table = Table(table_name, metadata, schema=schema,
                              autoload_with=connection if connection is not None else engine)
            primary_column = table.c[primary_key]
            primary_value = item.data.get(primary_key) or item.primary_value
            statement = delete(table).where(primary_column == primary_value)
            if connection is None:
                with engine.begin() as connection:
                    result = cls.execute_cleanup_statement(
                        item,
                        connection,
                        statement,
                        local_audit_handles,
                    )
                    cls.validate_delete_result(
                        item,
                        result,
                        table_name,
                        primary_key,
                        primary_value,
                        allow_missing=allow_missing,
                    )
                    cls.validate_no_residual(
                        connection,
                        table,
                        primary_column,
                        primary_value,
                        select,
                        func,
                        item=item,
                        audit_handles=local_audit_handles,
                    )
            else:
                result = cls.execute_cleanup_statement(
                    item,
                    connection,
                    statement,
                    local_audit_handles,
                )
                cls.validate_delete_result(
                    item,
                    result,
                    table_name,
                    primary_key,
                    primary_value,
                    allow_missing=allow_missing,
                )
                cls.validate_no_residual(
                    connection,
                    table,
                    primary_column,
                    primary_value,
                    select,
                    func,
                    item=item,
                    audit_handles=local_audit_handles,
                )
        except Exception as error:
            if audit_handles is None:
                DataFactorySqlExecutionService.mark_rolled_back(local_audit_handles, error)
            raise DataFactoryError(DATA_FACTORY_CLEANUP_SQL_CLEANUP_FAILED, value=(error,)) from error
        finally:
            if own_engine and not managed_by_worker:
                engine.dispose()

    @classmethod
    def execute_cleanup_statement(cls, item, connection, statement, audit_handles):
        binding = getattr(item, 'datasource_binding', None)
        execution = getattr(item, 'execution', None)
        if binding is None or execution is None:
            return connection.execute(statement)

        def execute_delete():
            result = connection.execute(statement)
            return result, {
                'columns': [],
                'rows': [],
                'row_count': 0,
                'affected_rows': max(int(getattr(result, 'rowcount', 0) or 0), 0),
            }

        result, audit_handle = DataFactorySqlExecutionService.execute(
            connection=connection,
            statement=statement,
            binding=binding,
            execution=execution,
            stage='cleanup',
            callback=execute_delete,
            item=item,
        )
        audit_handles.append(audit_handle)
        return result

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
        if isinstance(rowcount, int) and rowcount > 1:
            raise DataFactoryError(DATA_FACTORY_CONFIG_INVALID, value=('主键清理影响多条记录，事务必须回滚',))
        if rowcount == 0 and not allow_missing:
            raise DataFactoryError(DATA_FACTORY_CLEANUP_SQL_RECORD_EXECUTION_CLEANUP_INVALID,
                                   value=(item.id, table_name, primary_key, primary_value))

    @classmethod
    def validate_no_residual(
            cls,
            connection,
            table,
            primary_column,
            primary_value,
            select,
            func,
            item=None,
            audit_handles=None,
    ) -> None:
        """删除后在同一事务内按精确主键复核，防止驱动误报成功或触发器恢复数据。"""
        statement = select(func.count()).select_from(table).where(primary_column == primary_value)
        binding = getattr(item, 'datasource_binding', None)
        execution = getattr(item, 'execution', None)
        if binding is not None and execution is not None:
            def execute_check():
                count = connection.execute(statement).scalar()
                return count, {
                    'columns': ['residual_count'],
                    'rows': [{'residual_count': count}],
                    'row_count': 1,
                    'affected_rows': 0,
                }

            residual_count, audit_handle = DataFactorySqlExecutionService.execute(
                connection=connection,
                statement=statement,
                binding=binding,
                execution=execution,
                stage='residual_check',
                callback=execute_check,
                item=item,
            )
            if audit_handles is not None:
                audit_handles.append(audit_handle)
        else:
            residual_count = connection.execute(statement).scalar()
        if residual_count:
            raise DataFactoryError(DATA_FACTORY_CLEANUP_INVALID,
                                   value=(table.name, primary_column.name, primary_value, residual_count),
                                   )

    @staticmethod
    def record_cleanup_sql(item: DataFactoryExecutionItem, statement, engine):
        cleanup_sql, cleanup_sql_params = DataFactoryCleanup.compile_cleanup_sql(statement, engine.dialect)
        item.cleanup_sql = cleanup_sql
        item.cleanup_sql_params = cleanup_sql_params
        CleanupPersistenceService.save(item, ['cleanup_sql', 'cleanup_sql_params', 'update_time'])

    @staticmethod
    def compile_cleanup_sql(statement, dialect):
        compiled = statement.compile(dialect=dialect)
        return str(compiled), DataFactoryTypeCast.to_jsonable(dict(compiled.params or {}))

    @staticmethod
    def get_item_entity(item: DataFactoryExecutionItem):
        if not item.template_id or not item.template:
            raise DataFactoryError(DATA_FACTORY_CLEANUP_ENTITY_RECORD_TEMPLATE_EXECUTION_CLEANUP_INVALID,
                                   value=(item.id,))
        return item.template.entity

    @staticmethod
    def mark_success(item: DataFactoryExecutionItem):
        item.cleanup_status = DataFactoryCleanupStatusEnum.SUCCESS.value
        item.cleanup_time = timezone.now()
        item.cleanup_error = None
        CleanupPersistenceService.save(item, [
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
        CleanupPersistenceService.save(item, ['cleanup_status', 'cleanup_error', 'cleanup_time', 'update_time'])

    @staticmethod
    def mark_pending_manual(item: DataFactoryExecutionItem):
        item.cleanup_status = DataFactoryCleanupStatusEnum.PENDING_MANUAL.value
        item.cleanup_error = None
        item.cleanup_time = None
        CleanupPersistenceService.save(item, ['cleanup_status', 'cleanup_error', 'cleanup_time', 'update_time'])

    @staticmethod
    def mark_skipped(item: DataFactoryExecutionItem):
        item.cleanup_status = DataFactoryCleanupStatusEnum.SKIPPED.value
        item.cleanup_error = None
        item.cleanup_time = timezone.now()
        CleanupPersistenceService.save(item, ['cleanup_status', 'cleanup_error', 'cleanup_time', 'update_time'])

from datetime import datetime, timezone as datetime_timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from django.utils import timezone
from mangotools.enums import StatusEnum
from rest_framework import serializers

from src.apps.data_factory.api.serializers.template import DataFactoryTemplateSerializer
from src.apps.data_factory.api.views.field import DataFactoryFieldSerializer
from src.apps.data_factory.enums import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryEntityStatusChangeSourceEnum,
    DataFactoryExecutionStatusEnum,
    DataFactoryGeneratorTypeEnum,
    DataFactoryTemplateConfigStatusEnum,
    DataFactoryTemplateUsageScopeEnum,
)
from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.models import DataFactoryField, DataFactoryTemplate
from src.apps.data_factory.schemas.configuration import (
    DataFactoryFieldOverrideRules,
    DataFactoryPostInsertUpdates,
    validate_data_factory_scene_overrides,
)
from src.apps.data_factory.services.case_config_runner import DataFactoryCaseConfigRunner
from src.apps.data_factory.services.cleanup import DataFactoryCleanup
from src.apps.data_factory.services.discover import DataFactoryDiscover
from src.apps.data_factory.services.entity import DataFactoryEntityService
from src.apps.data_factory.services.execution_recovery import DataFactoryExecutionRecovery
from src.apps.data_factory.services.execution_snapshot import (
    DATA_FACTORY_INSERT_SNAPSHOT_KEY,
    build_insert_snapshot,
)
from src.apps.data_factory.services.factory_sql_execution import DataFactorySqlExecutionService
from src.apps.data_factory.services.field import DataFactoryFieldService
from src.apps.data_factory.services.generator import DataFactoryValueGenerator
from src.apps.data_factory.services.runner import DataFactoryRunner
from src.apps.data_factory.services.schema_monitor import DataFactorySchemaMonitorService
from src.apps.data_factory.services.template import DataFactoryTemplateService
from src.apps.data_factory.services.type_cast import DataFactoryTypeCast
from src.common.exceptions import ErrorDefinition
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


# -*- coding: utf-8 -*-


class DataFactoryTypeCastTests(SimpleTestCase):
    def test_cast_basic_types(self):
        self.assertEqual(DataFactoryTypeCast.cast("1", "integer"), 1)
        self.assertEqual(str(DataFactoryTypeCast.cast("12.30", "decimal")), "12.30")
        self.assertEqual(DataFactoryTypeCast.cast("true", "boolean"), True)
        self.assertEqual(DataFactoryTypeCast.cast({"a": 1}, "json"), {"a": 1})


class DataFactoryGeneratedColumnDiscoveryTests(SimpleTestCase):
    def test_mysql_auto_random_is_recognized_as_database_generated(self):
        engine = MagicMock()
        engine.dialect.name = "mysql"
        engine.dialect.identifier_preparer.quote.return_value = "`factory_record`"
        connection = engine.connect.return_value.__enter__.return_value
        connection.dialect = engine.dialect
        connection.execute.return_value.first.return_value = (
            "factory_record",
            "CREATE TABLE `factory_record` (\n"
            "  `mango_id` bigint NOT NULL /*T![auto_rand] AUTO_RANDOM(5) */,\n"
            "  `mango_row_id` bigint NOT NULL AUTO_INCREMENT,\n"
            "  PRIMARY KEY (`mango_id`)\n"
            ")",
        )

        result = DataFactoryDiscover._get_mysql_auto_generated_columns(
            engine,
            "factory_record",
        )

        self.assertEqual(result, {"mango_id", "mango_row_id"})

        normalized = DataFactoryDiscover._normalize_column(
            {
                "name": "mango_id",
                "type": "BIGINT",
                "nullable": False,
                "autoincrement": False,
            },
            ["mango_id"],
            set(),
            0,
            auto_generated_columns=result,
        )
        self.assertTrue(normalized["autoincrement"])
        self.assertEqual(normalized["generator_type"], DataFactoryGeneratorTypeEnum.SKIP.value)


class DataFactoryCleanupAvailabilityTests(SimpleTestCase):
    @staticmethod
    def execution(
            cleanup_status,
            status=DataFactoryExecutionStatusEnum.SUCCESS.value,
            execution_id=1,
    ):
        return SimpleNamespace(
            id=execution_id,
            execution_no=f"DF{execution_id}",
            cleanup_status=cleanup_status,
            status=status,
        )

    def test_failed_cleanup_is_available_after_execution_finished(self):
        execution = self.execution(DataFactoryCleanupStatusEnum.FAIL.value)

        self.assertTrue(DataFactoryCleanup.is_cleanup_required(execution))

    def test_successful_or_skipped_cleanup_is_not_available(self):
        successful = self.execution(DataFactoryCleanupStatusEnum.SUCCESS.value)
        skipped = self.execution(DataFactoryCleanupStatusEnum.SKIPPED.value)

        self.assertFalse(DataFactoryCleanup.is_cleanup_required(successful))
        self.assertFalse(DataFactoryCleanup.is_cleanup_required(skipped))

    def test_active_execution_is_not_available_for_cleanup(self):
        execution = self.execution(
            DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
            status=DataFactoryExecutionStatusEnum.PROCEED.value,
        )

        self.assertFalse(DataFactoryCleanup.is_cleanup_required(execution))

    @patch("src.apps.data_factory.services.cleanup.DataFactoryCleanup.cleanup_execution")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryExecution.objects.get")
    def test_on_demand_cleanup_skips_status_without_cleanup_responsibility(
            self,
            get_execution,
            cleanup_execution,
    ):
        get_execution.return_value = self.execution(DataFactoryCleanupStatusEnum.SUCCESS.value)

        result = DataFactoryCleanup.cleanup_execution_on_demand(1)

        cleanup_execution.assert_not_called()
        self.assertFalse(result["cleanup_required"])
        self.assertEqual(result["skipped"], 1)

    @patch("src.apps.data_factory.services.cleanup.DataFactoryCleanup.cleanup_execution")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryExecution.objects")
    def test_batch_cleanup_isolated_results(self, execution_objects, cleanup_execution):
        cleanable = self.execution(DataFactoryCleanupStatusEnum.FAIL.value, execution_id=1)
        no_cleanup = self.execution(DataFactoryCleanupStatusEnum.SUCCESS.value, execution_id=2)
        execution_objects.filter.return_value = [cleanable, no_cleanup]
        cleanup_execution.return_value = {"success": 1, "fail": 0, "skipped": 0}

        result = DataFactoryCleanup.batch_cleanup_executions([1, 2, 3])

        cleanup_execution.assert_called_once_with(
            1,
            force_cleanup=True,
            allow_missing=True,
            controlled_retry=True,
        )
        self.assertEqual(result["success"], 1)
        self.assertEqual(result["fail"], 1)
        self.assertEqual(result["skipped"], 1)


class DataFactoryEntityServiceTests(SimpleTestCase):
    @staticmethod
    def entity(status_changed_at):
        return SimpleNamespace(
            name='测试实体',
            status_change_source=DataFactoryEntityStatusChangeSourceEnum.SCHEMA_MONITOR.value,
            status_change_reason='表结构发生变化',
            status_changed_at=status_changed_at,
        )

    def test_unavailable_error_values_supports_naive_datetime(self):
        changed_at = datetime(2026, 8, 27, 3, 30, 36)

        values = DataFactoryEntityService.unavailable_error_values(self.entity(changed_at))

        self.assertEqual(values, ('测试实体', '定时表结构巡检', '表结构发生变化', '2026-08-27 03:30:36'))

    def test_unavailable_error_values_converts_aware_datetime(self):
        changed_at = datetime(2026, 8, 26, 19, 30, 36, tzinfo=datetime_timezone.utc)

        values = DataFactoryEntityService.unavailable_error_values(self.entity(changed_at))

        self.assertEqual(values[3], timezone.localtime(changed_at).strftime('%Y-%m-%d %H:%M:%S'))

    def test_unavailable_error_values_supports_empty_datetime(self):
        values = DataFactoryEntityService.unavailable_error_values(self.entity(None))

        self.assertEqual(values[3], '未知')


class DataFactoryGeneratorTests(SimpleTestCase):
    def build_field(self, name, platform_type, generator_type, config=None, nullable=False):
        return DataFactoryField(
            name=name,
            label=name,
            db_type=platform_type,
            platform_type=platform_type,
            nullable=nullable,
            generator_type=generator_type,
            generator_config=config or {},
        )

    def test_build_payload_with_fixed_values(self):
        fields = [
            self.build_field("price", "decimal", DataFactoryGeneratorTypeEnum.FIXED.value, {"value": "19.90"}),
            self.build_field("quantity", "integer", DataFactoryGeneratorTypeEnum.FIXED.value, {"value": 2}),
        ]

        payload = DataFactoryValueGenerator.build_payload(fields)

        self.assertEqual(str(payload["price"]), "19.90")
        self.assertEqual(payload["quantity"], 2)

    def test_dependency_field_reads_context(self):
        field = self.build_field(
            "user_id",
            "integer",
            DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
            {"alias": "用户", "field": "id"},
        )

        payload = DataFactoryValueGenerator.build_payload([field], context={"用户": {"id": 88}})

        self.assertEqual(payload["user_id"], 88)

    def test_required_field_cannot_be_empty(self):
        field = self.build_field("name", "string", DataFactoryGeneratorTypeEnum.FIXED.value, {"value": None})

        with self.assertRaises(Exception):
            DataFactoryValueGenerator.build_payload([field])


class DataFactoryCleanupTests(SimpleTestCase):
    def test_cleanup_strategy_maps_to_distinct_pending_states(self):
        self.assertEqual(
            DataFactoryRunner.cleanup_status_for_strategy(
                DataFactoryCleanupStrategyEnum.EXECUTION_END.value,
            ),
            DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
        )
        self.assertEqual(
            DataFactoryRunner.cleanup_status_for_strategy(
                DataFactoryCleanupStrategyEnum.MANUAL.value,
            ),
            DataFactoryCleanupStatusEnum.PENDING_MANUAL.value,
        )
        self.assertEqual(
            DataFactoryRunner.cleanup_status_for_strategy(
                DataFactoryCleanupStrategyEnum.NONE.value,
            ),
            DataFactoryCleanupStatusEnum.SKIPPED.value,
        )

    @patch(
        'src.apps.task_center.services.workbench.todo.WorkbenchTodoService.'
        'resolve_data_factory_cleanup_required_todos'
    )
    @patch(
        'src.apps.task_center.services.workbench.todo.WorkbenchTodoService.'
        'record_data_factory_cleanup_failure'
    )
    def test_failed_cleanup_syncs_workbench_todo(self, record_todo, resolve_required):
        execution = SimpleNamespace(
            id=12,
            cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value,
        )

        DataFactoryCleanup.sync_workbench_todo(execution)

        record_todo.assert_called_once_with(execution)
        resolve_required.assert_called_once_with(12)

    @patch(
        'src.apps.task_center.services.workbench.todo.WorkbenchTodoService.'
        'resolve_data_factory_cleanup_todos'
    )
    @patch(
        'src.apps.task_center.services.workbench.todo.WorkbenchTodoService.'
        'record_data_factory_cleanup_failure'
    )
    def test_pending_manual_cleanup_only_resolves_old_todos(self, record_todo, resolve_todos):
        execution = SimpleNamespace(
            id=12,
            cleanup_status=DataFactoryCleanupStatusEnum.PENDING_MANUAL.value,
        )

        DataFactoryCleanup.sync_workbench_todo(execution)

        record_todo.assert_not_called()
        resolve_todos.assert_called_once_with(12)
        self.assertEqual(execution.cleanup_status, DataFactoryCleanupStatusEnum.PENDING_MANUAL.value)

    @patch(
        'src.apps.task_center.services.workbench.todo.WorkbenchTodoService.'
        'resolve_data_factory_cleanup_todos'
    )
    def test_successful_cleanup_resolves_workbench_todo(self, resolve_todo):
        execution = SimpleNamespace(
            id=12,
            cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value,
        )

        DataFactoryCleanup.sync_workbench_todo(execution)

        resolve_todo.assert_called_once_with(12)

    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasourceResolver.require_binding_permission")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryCleanup.get_item_entity")
    def test_legacy_delete_type_does_not_block_sql_cleanup(self, get_entity, require_permission):
        get_entity.return_value = SimpleNamespace(
            name="历史实体",
            table_name="t_history",
            primary_key="id",
            delete_type=1,
        )
        item = SimpleNamespace(
            id=99,
            database=SimpleNamespace(),
            datasource_binding_id=7,
            datasource_binding=SimpleNamespace(),
            primary_value="1001",
        )

        DataFactoryCleanup.validate_cleanup_item(item)

        require_permission.assert_called_once_with(item.datasource_binding, write=True)

    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasourceResolver.require_binding_permission")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasourceBinding.objects")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryCleanup.get_item_entity")
    def test_cleanup_recovers_unique_binding_for_legacy_item(
            self,
            get_entity,
            binding_objects,
            require_permission,
    ):
        entity = SimpleNamespace(
            name="历史实体",
            datasource_alias_id=1,
            table_name="t_history",
            primary_key="id",
        )
        binding = SimpleNamespace(id=7)
        queryset = binding_objects.select_related.return_value.filter.return_value.order_by.return_value
        queryset.__getitem__.return_value = [binding]
        get_entity.return_value = entity
        item = SimpleNamespace(
            id=99,
            database=SimpleNamespace(),
            database_id=4,
            datasource_binding_id=None,
            datasource_binding=None,
            primary_value="1001",
            save=MagicMock(),
        )

        DataFactoryCleanup.validate_cleanup_item(item)

        binding_objects.select_related.return_value.filter.assert_called_once_with(
            datasource_alias_id=1,
            database_id=4,
        )
        require_permission.assert_called_once_with(binding, write=True)
        self.assertEqual(item.datasource_binding_id, 7)
        self.assertIs(item.datasource_binding, binding)
        item.save.assert_called_once_with(update_fields=['datasource_binding', 'update_time'])

    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasourceBinding.objects")
    def test_cleanup_rejects_legacy_item_without_matching_binding(self, binding_objects):
        entity = SimpleNamespace(datasource_alias_id=1)
        item = SimpleNamespace(id=99, database_id=4, datasource_binding_id=None)
        queryset = binding_objects.select_related.return_value.filter.return_value.order_by.return_value
        queryset.__getitem__.return_value = []

        with self.assertRaises(DataFactoryError) as error:
            DataFactoryCleanup.resolve_cleanup_binding(item, entity)

        self.assertIn("找不到逻辑数据源", str(error.exception))

    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasourceBinding.objects")
    def test_cleanup_rejects_ambiguous_legacy_bindings(self, binding_objects):
        entity = SimpleNamespace(datasource_alias_id=1)
        item = SimpleNamespace(id=99, database_id=4, datasource_binding_id=None)
        queryset = binding_objects.select_related.return_value.filter.return_value.order_by.return_value
        queryset.__getitem__.return_value = [SimpleNamespace(id=7), SimpleNamespace(id=8)]

        with self.assertRaises(DataFactoryError) as error:
            DataFactoryCleanup.resolve_cleanup_binding(item, entity)

        self.assertIn("存在多个环境绑定", str(error.exception))

    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasourceResolver.require_binding_permission")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasourceBinding.objects")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryCleanup.get_item_entity")
    def test_cleanup_does_not_persist_recovered_binding_without_write_permission(
            self,
            get_entity,
            binding_objects,
            require_permission,
    ):
        entity = SimpleNamespace(
            name="历史实体",
            datasource_alias_id=1,
            table_name="t_history",
            primary_key="id",
        )
        binding = SimpleNamespace(id=7)
        queryset = binding_objects.select_related.return_value.filter.return_value.order_by.return_value
        queryset.__getitem__.return_value = [binding]
        require_permission.side_effect = DataFactoryError(
            ErrorDefinition(code=300, message="当前环境不允许写入")
        )
        get_entity.return_value = entity
        item = SimpleNamespace(
            id=99,
            database=SimpleNamespace(),
            database_id=4,
            datasource_binding_id=None,
            datasource_binding=None,
            primary_value="1001",
            save=MagicMock(),
        )

        with self.assertRaises(DataFactoryError):
            DataFactoryCleanup.validate_cleanup_item(item)

        item.save.assert_not_called()

    @patch("src.apps.data_factory.services.cleanup.DataFactorySqlExecutionService.execute")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasource.get_worker_engine")
    def test_force_cleanup_recovers_historical_primary_key_by_recorded_unique_value(
            self,
            get_worker_engine,
            audit_execute,
    ):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert

        engine = create_engine("sqlite://")
        table = Table(
            "factory_history",
            MetaData(),
            Column("mango_id", Integer, primary_key=True, autoincrement=False),
            Column("title", String(64)),
        )
        table.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(insert(table).values(mango_id=991, title="AUTO_HISTORY_991"))
        get_worker_engine.return_value = (engine, True)
        audit_execute.side_effect = lambda **kwargs: (kwargs["callback"]()[0], MagicMock())
        item = SimpleNamespace(
            id=99,
            database=SimpleNamespace(),
            datasource_binding=SimpleNamespace(),
            execution=SimpleNamespace(),
            primary_value="",
            insert_data={"title": "AUTO_HISTORY_991"},
            data={"title": "AUTO_HISTORY_991"},
            insert_sql_params={
                DATA_FACTORY_INSERT_SNAPSHOT_KEY: {
                    "table_name": "factory_history",
                    "primary_key": "wrong_history_key",
                },
            },
            save=MagicMock(),
        )
        entity = SimpleNamespace(
            table_name="factory_history",
            primary_key="mango_id",
            unique_key="title",
        )

        recovered = DataFactoryCleanup.recover_missing_primary_value(item, entity)

        self.assertTrue(recovered)
        self.assertEqual(item.primary_value, "991")
        self.assertEqual(item.data["mango_id"], 991)
        self.assertEqual(
            item.insert_sql_params[DATA_FACTORY_INSERT_SNAPSHOT_KEY]["primary_key"],
            "mango_id",
        )
        item.save.assert_called_once_with(update_fields=[
            "primary_value",
            "data",
            "insert_sql_params",
            "update_time",
        ])
        engine.dispose()

    @patch("src.apps.data_factory.services.cleanup.DataFactorySqlExecutionService.execute")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasource.get_worker_engine")
    def test_historical_primary_key_recovery_rejects_ambiguous_rows(
            self,
            get_worker_engine,
            audit_execute,
    ):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert

        engine = create_engine("sqlite://")
        table = Table(
            "factory_history_ambiguous",
            MetaData(),
            Column("mango_id", Integer, primary_key=True, autoincrement=False),
            Column("title", String(64)),
        )
        table.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(insert(table), [
                {"mango_id": 991, "title": "AUTO_DUPLICATE"},
                {"mango_id": 992, "title": "AUTO_DUPLICATE"},
            ])
        get_worker_engine.return_value = (engine, True)
        audit_execute.side_effect = lambda **kwargs: (kwargs["callback"]()[0], MagicMock())
        item = SimpleNamespace(
            database=SimpleNamespace(),
            datasource_binding=SimpleNamespace(),
            execution=SimpleNamespace(),
            primary_value="",
            insert_data={"title": "AUTO_DUPLICATE"},
            data={"title": "AUTO_DUPLICATE"},
            insert_sql_params={
                DATA_FACTORY_INSERT_SNAPSHOT_KEY: {
                    "table_name": "factory_history_ambiguous",
                },
            },
            save=MagicMock(),
        )
        entity = SimpleNamespace(
            table_name="factory_history_ambiguous",
            primary_key="mango_id",
            unique_key="title",
        )

        recovered = DataFactoryCleanup.recover_missing_primary_value(item, entity)

        self.assertFalse(recovered)
        self.assertEqual(item.primary_value, "")
        item.save.assert_not_called()
        engine.dispose()

    @patch("src.apps.data_factory.services.cleanup.DataFactoryCleanup.sync_workbench_todo")
    @patch("src.apps.data_factory.services.cleanup.transaction.on_commit")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryExecutionItem.objects")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryExecution.objects.get")
    def test_cleanup_execution_uses_smaller_order_first(
            self,
            get_execution,
            item_objects,
            on_commit,
            sync_workbench_todo,
    ):
        execution = SimpleNamespace(id=12, cleanup_status=0, save=MagicMock())
        get_execution.return_value = execution
        ordered_items = item_objects.select_related.return_value.filter.return_value.order_by
        ordered_items.return_value = []

        DataFactoryCleanup.cleanup_execution(12, defer_resources=True)

        ordered_items.assert_called_once_with("cleanup_order", "-id")
        on_commit.assert_called_once()
        on_commit.call_args.args[0]()
        sync_workbench_todo.assert_called_once_with(execution)

    def test_compile_insert_sql_records_sql_and_params(self):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert

        engine = create_engine("sqlite://")
        table = Table(
            "contract_category",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("name", String(64)),
        )
        statement = insert(table).values(name="订单类型")

        insert_sql, insert_sql_params = DataFactoryRunner.compile_insert_sql(statement, engine.dialect)

        self.assertIn("INSERT INTO contract_category", insert_sql)
        self.assertEqual(insert_sql_params, {"name": "订单类型"})
        engine.dispose()

    def test_compile_cleanup_sql_records_sql_and_params(self):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, delete

        engine = create_engine("sqlite://")
        table = Table(
            "contract_category",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("name", String(64)),
        )
        statement = delete(table).where(table.c.id == 12)

        cleanup_sql, cleanup_sql_params = DataFactoryCleanup.compile_cleanup_sql(statement, engine.dialect)

        self.assertIn("DELETE FROM contract_category", cleanup_sql)
        self.assertEqual(cleanup_sql_params, {"id_1": 12})
        engine.dispose()

    def test_delete_without_matching_row_is_not_successful(self):
        item = SimpleNamespace(id=99)
        result = SimpleNamespace(rowcount=0)

        with self.assertRaises(Exception) as error:
            DataFactoryCleanup.validate_delete_result(item, result, "contract_category", "_id", 12)

        self.assertIn("未命中任何记录", str(error.exception))

    def test_force_cleanup_allows_already_missing_row(self):
        item = SimpleNamespace(id=99)
        result = SimpleNamespace(rowcount=0)

        DataFactoryCleanup.validate_delete_result(
            item,
            result,
            "contract_category",
            "_id",
            12,
            allow_missing=True,
        )

    def test_auto_cleanup_allows_already_missing_row(self):
        item = SimpleNamespace(id=99)
        result = SimpleNamespace(rowcount=0)

        DataFactoryCleanup.validate_delete_result(
            item,
            result,
            "contract_category",
            "_id",
            12,
            allow_missing=True,
        )

    def test_cleanup_across_databases_is_rejected(self):
        items = [
            SimpleNamespace(database_id=1),
            SimpleNamespace(database_id=2),
        ]

        with self.assertRaises(Exception) as error:
            DataFactoryCleanup.cleanup_items_in_database_transaction(items)

        self.assertIn("跨库事务一致性", str(error.exception))

    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasource.get_worker_engine")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryCleanup.get_item_entity")
    def test_cleanup_uses_immutable_storage_snapshot(self, get_entity, get_worker_engine):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert, select

        engine = create_engine("sqlite://")
        actual_table = Table(
            "actual_table",
            MetaData(),
            Column("actual_id", Integer, primary_key=True),
            Column("name", String(64)),
        )
        actual_table.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(insert(actual_table).values(actual_id=12, name="AUTO测试数据"))
        get_worker_engine.return_value = (engine, True)
        get_entity.return_value = SimpleNamespace(table_name="renamed_table", primary_key="renamed_id")
        item = SimpleNamespace(
            id=99,
            database=SimpleNamespace(),
            data={"actual_id": 12},
            primary_value="12",
            insert_sql_params={
                DATA_FACTORY_INSERT_SNAPSHOT_KEY: {
                    "table_name": "actual_table",
                    "primary_key": "actual_id",
                },
            },
            cleanup_sql=None,
            cleanup_sql_params={},
            save=MagicMock(),
        )

        DataFactoryCleanup.delete_by_primary_key(item)

        with engine.connect() as connection:
            self.assertEqual(connection.execute(select(actual_table.c.actual_id)).all(), [])
        engine.dispose()

    @patch("src.apps.data_factory.services.cleanup.DataFactorySqlExecutionService.execute")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryDatasource.get_worker_engine")
    @patch("src.apps.data_factory.services.cleanup.DataFactoryCleanup.get_item_entity")
    def test_cleanup_and_residual_check_use_unified_sql_audit(
            self,
            get_entity,
            get_worker_engine,
            execute_sql,
    ):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert

        engine = create_engine("sqlite://")
        table = Table(
            "factory_cleanup_audit",
            MetaData(),
            Column("id", Integer, primary_key=True),
            Column("name", String(64)),
        )
        table.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(insert(table).values(id=12, name="AUTO清理审计"))
        get_worker_engine.return_value = (engine, True)
        get_entity.return_value = SimpleNamespace(
            table_name="factory_cleanup_audit",
            primary_key="id",
        )
        stages = []

        def execute_with_audit(**kwargs):
            stages.append(kwargs["stage"])
            value, _audit_result = kwargs["callback"]()
            return value, SimpleNamespace(record=SimpleNamespace(id=len(stages)))

        execute_sql.side_effect = execute_with_audit
        item = SimpleNamespace(
            id=99,
            database=SimpleNamespace(),
            data={"id": None},
            primary_value="12",
            insert_sql_params={
                DATA_FACTORY_INSERT_SNAPSHOT_KEY: {
                    "table_name": "factory_cleanup_audit",
                    "primary_key": "id",
                },
            },
            datasource_binding=SimpleNamespace(id=7),
            execution=SimpleNamespace(id=18),
        )

        DataFactoryCleanup.delete_by_primary_key(item)

        self.assertEqual(stages, ["cleanup", "residual_check"])
        engine.dispose()

    def test_execution_snapshot_records_actual_storage(self):
        entity = SimpleNamespace(
            id=31,
            datasource_alias_id=7,
            table_name="t_task_info",
            primary_key="id",
        )
        binding = SimpleNamespace(id=9, environment=0, database_id=3)

        snapshot = build_insert_snapshot(entity, binding)

        self.assertEqual(snapshot["table_name"], "t_task_info")
        self.assertEqual(snapshot["primary_key"], "id")
        self.assertEqual(snapshot["database_id"], 3)


class DataFactoryRunnerPersistenceTests(SimpleTestCase):
    def test_generated_non_primary_column_recovers_auto_random_primary_key(self):
        from sqlalchemy import Column, Integer, MetaData, String, Table, select

        table = Table(
            "factory_auto_random",
            MetaData(),
            Column("mango_id", Integer, primary_key=True, autoincrement=False),
            Column("mango_row_id", Integer, autoincrement=True),
            Column("title", String(64)),
        )
        query_result = MagicMock()
        query_result.mappings.return_value.all.return_value = [{
            "mango_id": 7205759403792793686,
            "mango_row_id": 86,
            "title": "AUTO_LOCKED_86",
        }]
        connection = MagicMock()
        connection.execute.return_value = query_result
        created = {"title": "AUTO_LOCKED_86"}

        DataFactoryRunner.merge_generated_values(
            connection=connection,
            table=table,
            result=SimpleNamespace(inserted_primary_key=(None,), lastrowid=86),
            created=created,
            payload_fields={"title"},
            unique_key="",
            select=select,
        )

        self.assertEqual(created["mango_row_id"], 86)
        self.assertEqual(created["mango_id"], 7205759403792793686)

    def test_lastrowid_is_not_assigned_to_non_autoincrement_primary_key(self):
        from sqlalchemy import Column, Integer, MetaData, String, Table, select

        table = Table(
            "factory_external_primary",
            MetaData(),
            Column("external_id", Integer, primary_key=True, autoincrement=False),
            Column("title", String(64)),
        )
        created = {"title": "AUTO_EXTERNAL"}

        DataFactoryRunner.merge_generated_values(
            connection=MagicMock(),
            table=table,
            result=SimpleNamespace(inserted_primary_key=(None,), lastrowid=86),
            created=created,
            payload_fields={"title"},
            unique_key="",
            select=select,
        )

        self.assertNotIn("external_id", created)

    @patch("src.apps.data_factory.services.runner_parts.persistence.DataFactoryDatasource.get_worker_engine")
    def test_insert_maps_generated_value_to_actual_database_primary_key(self, get_worker_engine):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

        engine = create_engine("sqlite://")
        table = Table(
            "factory_generated_key",
            MetaData(),
            Column("actual_id", Integer, primary_key=True, autoincrement=True),
            Column("cleanup_id", Integer, nullable=True),
            Column("name", String(64)),
        )
        table.metadata.create_all(engine)
        get_worker_engine.return_value = (engine, True)
        entity = SimpleNamespace(
            table_name="factory_generated_key",
            primary_key="actual_id",
            unique_key="",
        )

        result = DataFactoryRunner.insert(
            entity,
            SimpleNamespace(schema_name="", db_type=DataSourceTypeEnum.SQLITE.value),
            {"name": "AUTO主键映射验证"},
        )

        self.assertEqual(result["created"]["actual_id"], 1)
        self.assertIsNone(result["created"]["cleanup_id"])
        engine.dispose()

    @patch("src.apps.data_factory.services.runner_parts.persistence.DataFactoryDatasource.get_worker_engine")
    def test_insert_rejects_mismatched_cleanup_primary_key_before_writing(self, get_worker_engine):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select

        engine = create_engine("sqlite://")
        table = Table(
            "factory_invalid_key",
            MetaData(),
            Column("actual_id", Integer, primary_key=True, autoincrement=True),
            Column("cleanup_id", Integer, nullable=True),
            Column("name", String(64)),
        )
        table.metadata.create_all(engine)
        get_worker_engine.return_value = (engine, True)
        entity = SimpleNamespace(
            name="错误主键实体",
            table_name="factory_invalid_key",
            primary_key="cleanup_id",
            unique_key="",
        )

        with self.assertRaises(DataFactoryError):
            DataFactoryRunner.insert(entity, SimpleNamespace(schema_name="", db_type=DataSourceTypeEnum.SQLITE.value), {"name": "不应写入"})

        with engine.connect() as connection:
            self.assertEqual(connection.execute(select(table.c.actual_id)).all(), [])
        engine.dispose()

    @patch("src.apps.data_factory.services.runner_parts.persistence.DataFactoryDatasource.get_worker_engine")
    def test_execution_item_failure_rolls_back_business_insert(self, get_worker_engine):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, select

        engine = create_engine("sqlite://")
        table = Table(
            "factory_test_data",
            MetaData(),
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(64)),
        )
        table.metadata.create_all(engine)
        get_worker_engine.return_value = (engine, True)
        entity = SimpleNamespace(table_name="factory_test_data", primary_key="id")

        with self.assertRaises(DataFactoryError):
            DataFactoryRunner.insert(
                entity,
                SimpleNamespace(schema_name="", db_type=DataSourceTypeEnum.SQLITE.value),
                {"name": "AUTO回滚验证"},
                before_commit=MagicMock(side_effect=RuntimeError("执行明细保存失败")),
            )

        with engine.connect() as connection:
            self.assertEqual(connection.execute(select(table.c.id)).all(), [])
        engine.dispose()

    @patch('src.apps.data_factory.services.factory_sql_execution.DatasourceTargetService.resolve')
    @patch(
        "src.apps.data_factory.services.factory_sql_execution."
        "SqlExecutionAuditService.finish_success"
    )
    @patch(
        "src.apps.data_factory.services.factory_sql_execution."
        "SqlExecutionAuditService.start"
    )
    def test_factory_sql_reuses_business_connection_and_records_source(
            self,
            audit_start,
            audit_finish,
            resolve_target,
    ):
        from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert

        engine = create_engine("sqlite://")
        table = Table(
            "factory_audit_data",
            MetaData(),
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("name", String(64)),
        )
        table.metadata.create_all(engine)
        handle = SimpleNamespace(record=SimpleNamespace(id=91))
        audit_start.return_value = handle
        execution = SimpleNamespace(
            id=18,
            execution_no="DFAUDIT18",
            project_product_id=3,
            source_type=2,
            source_id=51,
            stage=1,
        )
        binding = SimpleNamespace(
            environment=0,
            datasource_alias_id=7,
            database_id=9,
        )
        statement = insert(table).values(name="AUTO审计数据")

        with engine.begin() as connection:
            def execute_insert():
                result = connection.execute(statement)
                return result.inserted_primary_key[0], {
                    "columns": [],
                    "rows": [],
                    "row_count": 0,
                    "affected_rows": result.rowcount,
                }

            primary_key, returned_handle = DataFactorySqlExecutionService.execute(
                connection=connection,
                statement=statement,
                binding=binding,
                execution=execution,
                stage="create",
                callback=execute_insert,
                template=SimpleNamespace(id=110),
                entity=SimpleNamespace(id=34),
                alias="状态",
            )

        self.assertEqual(primary_key, 1)
        self.assertIs(returned_handle, handle)
        source_context = audit_start.call_args.kwargs["source_context"]
        self.assertEqual(source_context["execution_id"], 18)
        self.assertEqual(source_context["case_source_id"], 51)
        self.assertEqual(source_context["template_id"], 110)
        self.assertEqual(source_context["entity_id"], 34)
        self.assertEqual(source_context["source_stage"], "create")
        audit_finish.assert_called_once()
        engine.dispose()

    @patch("src.apps.data_factory.services.cleanup.DataFactoryCleanup.cleanup_execution")
    def test_failed_scene_forces_cleanup_of_all_created_nodes(self, cleanup_execution):
        execution = SimpleNamespace(id=88)

        DataFactoryRunner.cleanup_failed_execution(execution, RuntimeError("子表创建失败"))

        cleanup_execution.assert_called_once_with(
            88,
            force_cleanup=True,
            allow_missing=True,
        )


class DataFactoryExecutionRecoveryTests(SimpleTestCase):
    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryCleanup.sync_workbench_todo")
    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryCleanup.mark_pending_manual")
    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryCleanup.manual_cleanup_item_exists")
    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryExecutionItem.objects")
    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryExecution.objects")
    def test_existing_manual_cleanup_data_is_recorded_as_pending_not_failed(
            self,
            execution_objects,
            item_objects,
            item_exists,
            mark_pending_manual,
            sync_todo,
    ):
        execution = SimpleNamespace(
            id=66,
            cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value,
            error_message=DataFactoryExecutionRecovery.LEGACY_OVERDUE_ERROR,
            save=MagicMock(),
        )
        item = SimpleNamespace(
            id=77,
            cleanup_strategy=DataFactoryCleanupStrategyEnum.MANUAL.value,
            cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value,
            cleanup_error=DataFactoryExecutionRecovery.LEGACY_OVERDUE_ERROR,
        )
        ordered = (
            execution_objects.filter.return_value.filter.return_value
            .distinct.return_value.order_by.return_value
        )
        ordered.__getitem__.return_value = [execution]
        item_objects.select_related.return_value.filter.return_value.order_by.return_value = [item]
        item_exists.return_value = True
        mark_pending_manual.side_effect = lambda target: setattr(
            target,
            'cleanup_status',
            DataFactoryCleanupStatusEnum.PENDING_MANUAL.value,
        )

        result = DataFactoryExecutionRecovery.reconcile_manual_cleanup_states()

        self.assertEqual(result, {'pending': 1, 'resolved': 0})
        self.assertEqual(execution.cleanup_status, DataFactoryCleanupStatusEnum.PENDING_MANUAL.value)
        self.assertIsNone(execution.error_message)
        mark_pending_manual.assert_called_once_with(item)
        sync_todo.assert_called_once_with(execution)

    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryCleanup.sync_workbench_todo")
    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryCleanup.mark_success")
    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryCleanup.manual_cleanup_item_exists")
    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryExecutionItem.objects")
    @patch("src.apps.data_factory.services.execution_recovery.DataFactoryExecution.objects")
    def test_missing_manual_cleanup_data_is_reconciled_as_success(
            self,
            execution_objects,
            item_objects,
            item_exists,
            mark_success,
            sync_todo,
    ):
        execution = SimpleNamespace(id=66, cleanup_status=2, error_message=None, save=MagicMock())
        item = SimpleNamespace(
            id=77,
            cleanup_strategy=DataFactoryCleanupStrategyEnum.MANUAL.value,
            cleanup_status=DataFactoryCleanupStatusEnum.PENDING_MANUAL.value,
            cleanup_error=None,
        )
        ordered = (
            execution_objects.filter.return_value.filter.return_value
            .distinct.return_value.order_by.return_value
        )
        ordered.__getitem__.return_value = [execution]
        item_objects.select_related.return_value.filter.return_value.order_by.return_value = [item]
        item_exists.return_value = False
        mark_success.side_effect = lambda target: setattr(
            target,
            'cleanup_status',
            DataFactoryCleanupStatusEnum.SUCCESS.value,
        )

        result = DataFactoryExecutionRecovery.reconcile_manual_cleanup_states()

        self.assertEqual(result, {'pending': 0, 'resolved': 1})
        self.assertEqual(execution.cleanup_status, DataFactoryCleanupStatusEnum.SUCCESS.value)
        mark_success.assert_called_once_with(item)
        sync_todo.assert_called_once_with(execution)


class DataFactoryCaseConfigRunnerTests(SimpleTestCase):
    @patch("src.apps.data_factory.services.case_config_runner.DataFactoryCleanup.cleanup_execution",
           return_value={'fail': 1})
    def test_auto_cleanup_failure_is_propagated(self, cleanup):
        runner = DataFactoryCaseConfigRunner.__new__(DataFactoryCaseConfigRunner)
        runner.auto_cleanup_execution_ids = [2968]
        runner.logger = MagicMock()
        runner.user_id = 4

        with self.assertRaises(Exception) as error:
            runner.cleanup()

        self.assertIn("execution_id=2968", str(error.exception))
        cleanup.assert_called_once_with(2968, created_by=4, force_cleanup=True, allow_missing=True)
        runner.logger.error.assert_called_once()


class DataFactoryPreviewTests(SimpleTestCase):
    def test_scene_item_reference_reuses_root_generated_primary_key(self):
        source_field = SimpleNamespace(name="id", platform_type="integer")
        source_fields = MagicMock()
        source_fields.filter.return_value.first.return_value = source_field
        target_field = SimpleNamespace(
            name="risk_state_id",
            label="risk_state_id",
            platform_type="integer",
            generator_type=DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
            generator_config={"dependency_entity_id": 34, "field": "id"},
            nullable=False,
            primary_key=False,
            max_length=None,
            enum_values=[],
        )
        target_fields = MagicMock()
        target_fields.all.return_value.order_by.return_value = [target_field]
        root_entity = SimpleNamespace(datafactoryfield_set=source_fields)
        child_entity = SimpleNamespace(datafactoryfield_set=target_fields)
        child_template = SimpleNamespace(entity=child_entity, name="评分")
        item = SimpleNamespace(id=109, name="评分", child_template=child_template)
        template = SimpleNamespace(name="状态")
        overrides = {
            "risk_state_id": {
                "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                "generator_config": {"source_node": "root", "source_field": "id"},
            },
        }
        nodes = [{
            "node": "root",
            "alias": "状态",
            "entity": root_entity,
            "item": None,
        }]

        with patch.object(DataFactoryRunner, "get_template_items", return_value=[item]), patch.object(
                DataFactoryRunner,
                "build_scene_node_registry",
                return_value=nodes,
        ):
            prepared = DataFactoryRunner.prepare_scene_item_overrides(template, item, overrides)

        effective_fields = DataFactoryRunner.build_effective_fields([target_field], prepared)
        payload = DataFactoryValueGenerator.build_payload(
            effective_fields,
            context={"状态": {"id": 1001}},
        )

        self.assertEqual(payload["risk_state_id"], 1001)
        self.assertEqual(
            prepared["risk_state_id"]["generator_config"]["alias"],
            "状态",
        )

    def test_scene_item_reference_rejects_later_sibling(self):
        source_field = SimpleNamespace(name="id", platform_type="integer")
        source_fields = MagicMock()
        source_fields.filter.return_value.first.return_value = source_field
        target_field = SimpleNamespace(name="source_id", platform_type="integer")
        target_fields = MagicMock()
        target_fields.all.return_value.order_by.return_value = [target_field]
        current = SimpleNamespace(
            id=101,
            name="当前项",
            child_template=SimpleNamespace(entity=SimpleNamespace(datafactoryfield_set=target_fields)),
        )
        later = SimpleNamespace(id=102, name="后续项")
        nodes = [{"node": "root", "alias": "主节点", "item": None}, {
            "node": "item:101",
            "aliases": ["item:当前项"],
            "alias": "当前项",
            "item": current,
            "entity": SimpleNamespace(),
        }, {
                     "node": "item:102",
                     "aliases": ["item:后续项"],
                     "alias": "后续项",
                     "item": later,
                     "entity": SimpleNamespace(datafactoryfield_set=source_fields),
                 }]
        overrides = {
            "source_id": {
                "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                "generator_config": {"source_node": "item:102", "source_field": "id"},
            },
        }

        with patch.object(DataFactoryRunner, "get_template_items", return_value=[current, later]), patch.object(
                DataFactoryRunner,
                "build_scene_node_registry",
                return_value=nodes,
        ):
            with self.assertRaises(DataFactoryError):
                DataFactoryRunner.prepare_scene_item_overrides(
                    SimpleNamespace(name="场景"),
                    current,
                    overrides,
                )

    def test_mcp_can_update_entity_cleanup_config(self):
        from src.interfaces.mcp.tools.data_factory.entity import register_entity_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_entity_tools(registry)
        updated = {"id": 59, "delete_type": 2, "primary_key": "id", "cleanup_order": 10}

        with patch(
                "src.interfaces.mcp.tools.data_factory.entity.DataFactoryEntityService.update",
                return_value=updated,
        ) as update_entity, patch(
            "src.interfaces.mcp.tools.data_factory.entity.mcp_current_user_id",
            return_value=4,
        ):
            result = registry.tools["update_data_factory_entity"](
                entity_id=59,
                primary_key="id",
                cleanup_order=10,
            )

        self.assertTrue(result["success"])
        update_entity.assert_called_once_with(
            59,
            {"id": 59, "primary_key": "id", "delete_type": 2, "cleanup_order": 10},
            update_user_id=4,
        )

    def test_mcp_can_update_entity_module(self):
        from src.interfaces.mcp.tools.data_factory.entity import register_entity_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_entity_tools(registry)
        updated = {"id": 59, "project_product": 3, "module": 217, "delete_type": 2}

        with patch(
                "src.interfaces.mcp.tools.data_factory.entity.DataFactoryEntityService.update",
                return_value=updated,
        ) as update_entity, patch(
            "src.interfaces.mcp.tools.data_factory.entity.mcp_current_user_id",
            return_value=4,
        ):
            result = registry.tools["update_data_factory_entity"](
                entity_id=59,
                project_product_id=3,
                module_id=217,
            )

        self.assertTrue(result["success"])
        update_entity.assert_called_once_with(
            59,
            {"id": 59, "project_product": 3, "module": 217, "delete_type": 2},
            update_user_id=4,
        )

    def test_mcp_status_update_records_mcp_source(self):
        from src.interfaces.mcp.tools.data_factory.entity import register_entity_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_entity_tools(registry)
        entity = SimpleNamespace(
            status=StatusEnum.FAIL.value,
            status_change_source=DataFactoryEntityStatusChangeSourceEnum.MCP.value,
            status_change_reason_code="mcp_disabled",
            status_change_reason="MCP 手动停用实体",
            status_changed_at=None,
            status_changed_by=None,
            status_change_reference_type="mcp_tool",
            status_change_reference_id=None,
        )
        with (
            patch(
                "src.interfaces.mcp.tools.data_factory.entity.DataFactoryEntityService.update",
                return_value={"id": 59},
            ),
            patch(
                "src.interfaces.mcp.tools.data_factory.entity.mcp_current_user_id",
                return_value=4,
            ),
            patch(
                "src.interfaces.mcp.tools.data_factory.entity.DataFactoryEntityService.change_status",
                return_value={"entity": entity},
            ) as change_status,
        ):
            result = registry.tools["update_data_factory_entity"](
                entity_id=59,
                status=StatusEnum.FAIL.value,
            )

        self.assertTrue(result["success"])
        change_status.assert_called_once_with(
            entity_id=59,
            status=StatusEnum.FAIL.value,
            source=DataFactoryEntityStatusChangeSourceEnum.MCP.value,
            reason_code="mcp_disabled",
            reason="MCP 手动停用实体",
            operator_id=4,
            source_record_type="mcp_tool",
            restore_invalidated_templates=False,
        )

    def test_field_preview_service_generates_fixed_value(self):
        result = DataFactoryFieldService.preview_values([
            {
                "name": "contract_id",
                "platform_type": "string",
                "generator_type": DataFactoryGeneratorTypeEnum.FIXED.value,
                "generator_config": {"value": "2082405000000003134"},
            }
        ])

        self.assertEqual(result["payload"]["contract_id"], "2082405000000003134")
        self.assertTrue(result["fields"][0]["valid"])

    def test_case_config_preview_uses_shared_template_preview(self):
        from src.interfaces.mcp.tools.data_factory.case_config import register_case_config_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_case_config_tools(registry)
        expected = {"success": True, "data": {"template_id": 134}}

        with patch(
                "src.interfaces.mcp.tools.data_factory.case_config._preview_data_factory_template_result",
                return_value=expected,
        ) as preview:
            result = registry.tools["preview_data_factory_case_config"](
                template_id=134,
                test_env=0,
                test_object_id=7,
                user_id=4,
                field_overrides={
                    "contract_id": {
                        "generator_type": 1,
                        "generator_config": {"value": "2082405000000003134"},
                    }
                },
            )

        self.assertEqual(result, expected)
        preview.assert_called_once_with(
            template_id=134,
            overrides={
                "contract_id": {
                    "generator_type": 1,
                    "generator_config": {"value": "2082405000000003134"},
                }
            },
            context={},
            test_object_id=7,
            test_env=0,
            user_id=4,
        )

    def test_shared_template_preview_returns_business_error_message(self):
        from src.interfaces.mcp.tools.data_factory.helpers import _preview_data_factory_template_result

        message = '测试对象不存在或已删除，请使用存在的测试对象id查询'
        with (
            patch(
                'src.interfaces.mcp.tools.data_factory.helpers.DataFactoryQuerySelector.data_factory_template',
            ) as template_queryset,
            patch(
                'src.interfaces.mcp.tools.data_factory.helpers.DataFactoryPreviewService.preview_template',
                side_effect=DataFactoryError(ErrorDefinition(code=300, message=message)),
            ),
        ):
            template_queryset.return_value.get.return_value = SimpleNamespace(id=134)
            result = _preview_data_factory_template_result(
                template_id=134,
                test_object_id=6104,
                test_env=0,
                user_id=4,
            )

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], message)
        self.assertEqual(result['error_code'], '300')

    def test_template_preview_forwards_output_config_to_shared_service(self):
        from src.interfaces.mcp.tools.data_factory.template import register_template_tools

        class ToolRegistry:
            def __init__(self):
                self.tools = {}

            def tool(self):
                def register(func):
                    self.tools[func.__name__] = func
                    return func

                return register

        registry = ToolRegistry()
        register_template_tools(registry)
        expected = {"success": True, "data": {"template_id": 134}}
        output_config = [{"field": "contract_id", "key": "id"}]
        post_insert_updates = [{
            "target_node": "root",
            "target_field": "score_id",
            "source_node": "item:score",
            "source_field": "id",
            "sort": 10,
        }]

        with patch(
                "src.interfaces.mcp.tools.data_factory.template._preview_data_factory_template_result",
                return_value=expected,
        ) as preview:
            result = registry.tools["preview_data_factory_template"](
                template_id=134,
                output_config=output_config,
                post_insert_updates=post_insert_updates,
            )

        self.assertEqual(result, expected)
        preview.assert_called_once_with(
            template_id=134,
            overrides={},
            output_config=output_config,
            post_insert_updates=post_insert_updates,
            context={},
            test_object_id=None,
            test_env=None,
            user_id=None,
        )

    def test_build_dependency_tree_includes_fields_and_status(self):
        node = DataFactoryRunner.build_dependency_tree(
            template=None,
            entity=None,
            alias="订单类型角色",
            action="create",
            fields=[{"name": "role_id", "valid": False}],
            missing_fields=[{"field": "role_id", "message": "必填字段生成结果为空"}],
        )

        self.assertEqual(node["status"], "warning")
        self.assertEqual(node["missing_count"], 1)
        self.assertEqual(node["fields"][0]["name"], "role_id")

    def test_collect_preview_missing_fields_includes_dependencies(self):
        result = DataFactoryRunner.collect_preview_missing_fields(
            template={"id": 1, "name": "订单类型"},
            entity={"id": 10, "name": "contract_category", "table_name": "contract_category"},
            missing_fields=[],
            dependencies=[
                {
                    "template": {"id": 2, "name": "订单类型角色"},
                    "entity": {
                        "id": 11,
                        "name": "contract_category_role",
                        "table_name": "contract_category_role",
                    },
                    "missing_fields": [{"field": "role_id", "message": "必填字段生成结果为空"}],
                    "dependencies": [],
                }
            ],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["field"], "role_id")
        self.assertEqual(result[0]["path"], "订单类型 / 订单类型角色")


class DataFactoryTemplateSerializerTests(SimpleTestCase):
    def test_post_insert_update_schema_rejects_arbitrary_sql(self):
        with self.assertRaises(Exception):
            DataFactoryPostInsertUpdates.model_validate([{
                "target_node": "root",
                "target_field": "score_id",
                "source_node": "item:评分",
                "source_field": "id",
                "sql": "UPDATE any_table SET value = 1",
            }])

    def test_post_insert_update_schema_accepts_structured_mapping(self):
        result = DataFactoryPostInsertUpdates.model_validate([{
            "target_node": "root",
            "target_field": "current_score_result_id",
            "source_node": "item:评分",
            "source_field": "id",
            "sort": 10,
        }]).model_dump()

        self.assertEqual(result[0]["target_node"], "root")
        self.assertEqual(result[0]["source_node"], "item:评分")

    def test_post_insert_update_only_updates_generated_primary_key_record(self):
        from sqlalchemy import Column, Integer, MetaData, Table, create_engine, insert, select

        engine = create_engine("sqlite:///:memory:")
        metadata = MetaData()
        table = Table(
            "risk_state",
            metadata,
            Column("id", Integer, primary_key=True),
            Column("score_id", Integer, nullable=True),
        )
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(insert(table), [{"id": 1001}, {"id": 1002}])

        entity = SimpleNamespace(table_name="risk_state", primary_key="id")
        with patch(
                "src.apps.data_factory.services.runner_parts.scene.DataFactoryDatasource.get_worker_engine",
                return_value=(engine, True),
        ):
            affected_rows = DataFactoryRunner.update_created_record(
                entity,
                SimpleNamespace(schema_name=''),
                "score_id",
                2001,
                1001,
            )

        with engine.connect() as connection:
            rows = connection.execute(select(table).order_by(table.c.id)).mappings().all()
        self.assertEqual(affected_rows, 1)
        self.assertEqual(rows[0]["score_id"], 2001)
        self.assertIsNone(rows[1]["score_id"])
        engine.dispose()

    def test_entity_module_mismatch_raises_data_factory_error(self):
        serializer = DataFactoryTemplateSerializer()
        attrs = {
            "project_product": SimpleNamespace(id=3),
            "module": SimpleNamespace(id=217, project_product_id=3),
            "entity": SimpleNamespace(id=18, project_product_id=3, module_id=213),
            "name": "文件信息表场景",
        }

        with self.assertRaises(DataFactoryError) as error:
            serializer.validate(attrs)

        self.assertEqual(error.exception.msg, "实体不属于当前模块")


class DataFactoryCaseConfigSerializerTests(SimpleTestCase):
    def test_api_case_serializer_reuses_common_internal_template_validation(self):
        from src.apps.auto_api.api.serializers.api_case_data_factory import ApiCaseDataFactorySerializer
        from src.apps.data_factory.api.views.case_config import DataFactoryCaseConfigSerializer

        attrs = {
            "source_type": DataFactoryCaseSourceTypeEnum.API_CASE.value,
            "source_id": 1,
            "template": SimpleNamespace(usage_scope=DataFactoryTemplateUsageScopeEnum.INTERNAL.value),
            "field_overrides": {},
        }

        for serializer_class in [DataFactoryCaseConfigSerializer, ApiCaseDataFactorySerializer]:
            with self.subTest(serializer=serializer_class.__name__):
                with self.assertRaises(serializers.ValidationError):
                    serializer_class().validate(dict(attrs))


class DataFactoryFieldSerializerTests(SimpleTestCase):
    def test_dependency_field_can_save_without_template_id(self):
        serializer = DataFactoryFieldSerializer()

        result = serializer.validate({
            "name": "user_id",
            "db_type": "bigint",
            "platform_type": "integer",
            "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
            "generator_config": {"dependency_entity_id": 12, "field": "id"},
        })
        self.assertEqual(result["generator_config"]["dependency_entity_id"], 12)
        self.assertEqual(result["generator_config"]["field"], "id")

    def test_dependency_field_rejects_template_id_in_entity_rule(self):
        serializer = DataFactoryFieldSerializer()

        with self.assertRaises(serializers.ValidationError):
            serializer.validate({
                "name": "user_id",
                "db_type": "bigint",
                "platform_type": "integer",
                "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                "generator_config": {"dependency_entity_id": 12, "field": "id", "template_id": 99},
            })

    def test_dependency_override_accepts_template_id(self):
        result = DataFactoryFieldOverrideRules.model_validate({
            "user_id": {
                "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                "generator_config": {
                    "dependency_entity_id": 12,
                    "field": "id",
                    "template_id": 99,
                    "strategy": "reuse_or_create",
                },
            }
        }).model_dump()

        self.assertEqual(result["user_id"]["generator_config"]["template_id"], 99)

    def test_dependency_override_accepts_scene_node_reference(self):
        result = DataFactoryFieldOverrideRules.model_validate({
            "risk_state_id": {
                "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                "generator_config": {
                    "source_node": "root",
                    "source_field": "id",
                },
            }
        }).model_dump()

        config = result["risk_state_id"]["generator_config"]
        self.assertEqual(config["source_node"], "root")
        self.assertEqual(config["source_field"], "id")

    def test_dependency_override_rejects_scene_node_create_always(self):
        with self.assertRaises(Exception):
            DataFactoryFieldOverrideRules.model_validate({
                "risk_state_id": {
                    "generator_type": DataFactoryGeneratorTypeEnum.DEPENDENCY_FIELD.value,
                    "generator_config": {
                        "source_node": "root",
                        "source_field": "id",
                        "strategy": "create_always",
                    },
                }
            })

    def test_scene_override_accepts_main_and_items(self):
        result = validate_data_factory_scene_overrides({
            "__main__": {
                "name": {
                    "generator_type": DataFactoryGeneratorTypeEnum.FIXED.value,
                    "generator_config": {"value": "主表"},
                },
            },
            "__items__": {
                "20": {
                    "category_id": {
                        "generator_type": DataFactoryGeneratorTypeEnum.FIXED.value,
                        "generator_config": {"value": 1},
                    },
                },
            },
        })

        self.assertEqual(result["__main__"]["name"]["generator_config"]["value"], "主表")
        self.assertEqual(result["__items__"]["20"]["category_id"]["generator_config"]["value"], 1)

    def test_random_range_must_be_valid(self):
        serializer = DataFactoryFieldSerializer()

        with self.assertRaises(serializers.ValidationError):
            serializer.validate({
                "name": "amount",
                "db_type": "decimal",
                "platform_type": "decimal",
                "generator_type": DataFactoryGeneratorTypeEnum.RANDOM_DECIMAL.value,
                "generator_config": {"min": 20, "max": 10},
            })


class DataFactorySchemaMonitorTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        # 巡检单元测试隔离数据源解析与待办持久化；解析契约由 DatasourceTarget 测试覆盖。
        def metadata_target(binding):
            binding.database.cache_key = binding.database.id
            return binding.database
        self.enterContext(patch(
            'src.apps.data_factory.services.schema_monitor.DatasourceTargetService.for_metadata',
            side_effect=metadata_target,
        ))
        self.enterContext(patch(
            'src.apps.data_factory.services.schema_monitor.DatasourceTargetService.resolve',
            side_effect=lambda binding, **_: binding.database,
        ))
        self.enterContext(patch.object(DataFactorySchemaMonitorService, '_record_workbench_todo'))
        self.enterContext(patch.object(DataFactorySchemaMonitorService, '_reconcile_workbench_reviews'))

    def test_validation_binding_filter_uses_configured_environments(self):
        bindings = [
            SimpleNamespace(id=1, environment=0, test_object_id=None),
            SimpleNamespace(id=2, environment=2, test_object_id=None),
            SimpleNamespace(id=3, environment=3, test_object_id=None),
        ]

        with patch.object(
                DataFactorySchemaMonitorService,
                "configured_validation_environments",
                return_value=[0, 3],
        ):
            result = DataFactorySchemaMonitorService.filter_validation_bindings(bindings)

        self.assertEqual([binding.id for binding in result], [1, 3])

    def test_validation_binding_filter_defaults_to_all_bindings(self):
        bindings = [
            SimpleNamespace(id=1, environment=0, test_object_id=None),
            SimpleNamespace(id=2, environment=2, test_object_id=None),
        ]

        with patch.object(
                DataFactorySchemaMonitorService,
                "configured_validation_environments",
                return_value=None,
        ):
            result = DataFactorySchemaMonitorService.filter_validation_bindings(bindings)

        self.assertEqual(result, bindings)

    def test_entity_activation_only_checks_configured_environments(self):
        entity = SimpleNamespace(
            id=57,
            name="文件信息",
            table_name="t_file_info",
            primary_key="id",
            unique_key="",
            schema_name="",
            datasource_alias_id=8,
            datasource_alias=SimpleNamespace(status=StatusEnum.SUCCESS.value),
        )
        test_binding = SimpleNamespace(
            id=21,
            database_id=12,
            environment=0,
            test_object_id=None,
            database=SimpleNamespace(id=12),
        )
        production_binding = SimpleNamespace(
            id=22,
            database_id=13,
            environment=2,
            test_object_id=None,
            database=SimpleNamespace(id=13),
        )
        columns = [{
            "name": "id",
            "db_type": "BIGINT",
            "nullable": False,
            "primary_key": True,
            "autoincrement": True,
            "max_length": None,
        }]

        with (
            patch("src.apps.data_factory.services.schema_monitor.DataFactoryEntity.objects") as entity_objects,
            patch(
                "src.apps.data_factory.services.schema_monitor.DataFactoryDatasourceBinding.objects") as binding_objects,
            patch.object(DataFactorySchemaMonitorService, "configured_validation_environments", return_value=[0]),
            patch.object(
                DataFactorySchemaMonitorService,
                "entity_signature",
                return_value=DataFactorySchemaMonitorService.columns_signature(columns),
            ),
            patch(
                "src.apps.data_factory.services.schema_monitor.DataFactoryDatasourceResolver.require_binding_permission"
            ) as require_permission,
            patch.object(DataFactoryDiscover, "get_table_schema", return_value={"columns": columns}),
        ):
            entity_objects.select_related.return_value.get.return_value = entity
            binding_objects.select_related.return_value.filter.return_value.order_by.return_value = [
                test_binding,
                production_binding,
            ]

            result = DataFactorySchemaMonitorService.validate_entity_activation(entity.id)

        self.assertEqual(result["checked_binding_ids"], [test_binding.id])
        require_permission.assert_called_once_with(test_binding, write=False)

    def test_entity_key_validation_detects_mismatched_primary_and_unique_keys(self):
        entity = SimpleNamespace(primary_key="mango_row_id", unique_key="title")
        schema = {
            "primary_keys": ["mango_id"],
            "columns": [{"name": "mango_id", "primary_key": True}],
            "indexes": [],
        }

        differences = DataFactorySchemaMonitorService.describe_key_differences(entity, schema)

        self.assertEqual([item["field"] for item in differences], ["清理主键", "唯一键"])
        self.assertEqual(differences[0]["actual"], "mango_id")

    def test_entity_key_validation_accepts_database_constraints(self):
        entity = SimpleNamespace(primary_key="mango_id", unique_key="title")
        schema = {
            "primary_keys": ["mango_id"],
            "columns": [{"name": "mango_id", "primary_key": True}],
            "indexes": [{"unique": True, "column_names": ["title"]}],
        }

        self.assertEqual(
            DataFactorySchemaMonitorService.describe_key_differences(entity, schema),
            [],
        )

    def test_template_activation_environments_use_global_selection(self):
        bindings = [
            SimpleNamespace(environment=0, test_object_id=None),
            SimpleNamespace(environment=2, test_object_id=None),
            SimpleNamespace(environment=3, test_object_id=None),
        ]
        template = SimpleNamespace(
            entity=SimpleNamespace(
                datasource_alias=SimpleNamespace(
                    datafactorydatasourcebinding_set=SimpleNamespace(
                        all=lambda: bindings,
                    )
                )
            )
        )

        with patch(
                "src.apps.data_factory.services.template.SystemConfigService.get_data_factory_validation_environments",
                return_value=[0, 3],
        ):
            environments = DataFactoryTemplateService.activation_environments(template)

        self.assertEqual(environments, [0, 3])

    def test_disable_entity_records_schema_monitor_audit_context(self):
        with patch(
                "src.apps.data_factory.services.schema_monitor.DataFactoryEntityService.change_status",
                return_value={"invalidated_template_count": 2},
        ) as change_status:
            invalidated_count = DataFactorySchemaMonitorService.disable_entity(
                57,
                binding_ids=[21],
                differences=[{
                    "database_id": 12,
                    "items": [{"field": "file_id", "change_type": "configured_field_removed"}],
                }],
                source_record_id=987,
            )

        self.assertEqual(invalidated_count, 2)
        change_status.assert_called_once_with(
            entity_id=57,
            status=StatusEnum.FAIL.value,
            source=DataFactoryEntityStatusChangeSourceEnum.SCHEMA_MONITOR.value,
            reason_code="schema_changed",
            reason="定时表结构巡检检测到数据库表结构已发生变化，涉及字段：file_id",
            source_record_type="schedule_fire",
            source_record_id=987,
            context={
                "job_key": "scan_data_factory_entity_field_updates",
                "binding_ids": [21],
                "database_ids": [12],
                "differences": [{
                    "database_id": 12,
                    "items": [{"field": "file_id", "change_type": "configured_field_removed"}],
                }],
            },
            invalidate_templates=True,
        )

    def test_signature_normalizes_mysql_metadata_and_ignores_generation_rules(self):
        saved_columns = [{
            "name": "id",
            "db_type": "INTEGER",
            "platform_type": "integer",
            "nullable": False,
            "primary_key": True,
            "autoincrement": True,
            "max_length": None,
            "enum_values": [],
        }, {
            "name": "status",
            "db_type": "TINYINT",
            "platform_type": "integer",
            "nullable": False,
            "primary_key": False,
            "autoincrement": False,
            "max_length": None,
            "enum_values": [0, 1],
        }, {
            "name": "created_at",
            "db_type": "DATETIME",
            "platform_type": "datetime",
            "nullable": False,
            "primary_key": False,
            "autoincrement": False,
            "max_length": None,
            "enum_values": [],
        }, {
            "name": "remark",
            "db_type": 'TEXT COLLATE "UTF8MB4_UNICODE_CI"',
            "platform_type": "string",
            "nullable": True,
            "primary_key": False,
            "autoincrement": False,
            "max_length": None,
            "enum_values": [],
        }]
        mysql_columns = [{
            "name": "id",
            "db_type": "INT(11) UNSIGNED",
            "platform_type": "integer",
            "nullable": False,
            "primary_key": True,
            "autoincrement": True,
            "max_length": None,
            "enum_values": [],
        }, {
            "name": "status",
            "db_type": "TINYINT(1)",
            "platform_type": "boolean",
            "nullable": False,
            "primary_key": False,
            "autoincrement": False,
            "max_length": None,
            "enum_values": [],
        }, {
            "name": "created_at",
            "db_type": "DATETIME(6)",
            "platform_type": "datetime",
            "nullable": False,
            "primary_key": False,
            "autoincrement": False,
            "max_length": None,
            "enum_values": [],
        }, {
            "name": "remark",
            "db_type": "TEXT",
            "platform_type": "string",
            "nullable": True,
            "primary_key": False,
            "autoincrement": False,
            "max_length": 65535,
            "enum_values": [],
        }]

        self.assertEqual(
            DataFactorySchemaMonitorService.columns_signature(saved_columns),
            DataFactorySchemaMonitorService.columns_signature(mysql_columns),
        )

    def test_optional_database_field_is_also_a_schema_change(self):
        differences = DataFactorySchemaMonitorService.describe_incompatible_differences(
            expected=(("id", "BIGINT", False, True, True, None),),
            actual=(
                ("id", "BIGINT", False, True, True, None),
                ("remark", "VARCHAR", True, False, False, 64),
            ),
            actual_columns=[{
                "name": "remark",
                "nullable": True,
                "default": None,
                "autoincrement": False,
                "generated": False,
            }],
        )

        self.assertEqual(differences[0]["change_type"], "field_added")

    def test_scan_disables_entity_when_mysql_schema_changes(self):
        entity = SimpleNamespace(
            id=57,
            name="文件信息",
            table_name="t_file_info",
            datasource_alias_id=8,
        )
        database = SimpleNamespace(id=12, password="secret")
        binding = SimpleNamespace(id=21, database_id=12, datasource_alias_id=8, database=database)
        expected = (("id", "BIGINT", False, True, True, None),)
        changed_columns = [{
            "name": "id",
            "db_type": "BIGINT",
            "platform_type": "integer",
            "nullable": False,
            "primary_key": True,
            "autoincrement": True,
            "max_length": None,
            "enum_values": [],
        }, {
            "name": "new_column",
            "db_type": "VARCHAR(32)",
            "platform_type": "string",
            "nullable": False,
            "primary_key": False,
            "autoincrement": False,
            "default": None,
            "generated": False,
            "max_length": 32,
            "enum_values": [],
        }]

        with (
            patch("src.apps.data_factory.services.schema_monitor.DataFactoryEntity.objects") as entity_objects,
            patch(
                "src.apps.data_factory.services.schema_monitor.DataFactoryDatasourceBinding.objects") as binding_objects,
            patch.object(DataFactorySchemaMonitorService, "entity_signatures", return_value={57: expected}),
            patch.object(
                DataFactoryDiscover,
                "get_mysql_table_schemas",
                return_value={"t_file_info": {"columns": changed_columns}},
            ),
            patch.object(DataFactorySchemaMonitorService, "disable_entity", return_value=3) as disable_entity,
        ):
            entity_objects.select_related.return_value.filter.return_value = [entity]
            binding_objects.select_related.return_value.filter.return_value = [binding]

            result = DataFactorySchemaMonitorService.scan(source_record_id=987)

        self.assertEqual(result["changed_entity_count"], 1)
        self.assertEqual(result["observed_changed_entity_count"], 1)
        self.assertEqual(result["detected_changed_entity_count"], 1)
        self.assertFalse(result["auto_disable_blocked"])
        self.assertEqual(result["invalidated_template_count"], 3)
        self.assertEqual(result["failed_binding_count"], 0)
        disable_entity.assert_called_once_with(
            57,
            binding_ids=[21],
            differences=[{
                "database_id": 12,
                "items": [{
                    "field": "new_column",
                    "change_type": "required_field_added",
                    "expected": None,
                    "actual": ("VARCHAR", False, False, False, 32),
                }],
            }],
            source_record_id=987,
        )

    def test_scan_only_uses_configured_environments(self):
        entity = SimpleNamespace(
            id=57,
            name="文件信息",
            table_name="t_file_info",
            datasource_alias_id=8,
        )
        test_database = SimpleNamespace(id=12, password="secret")
        production_database = SimpleNamespace(id=13, password="secret")
        test_binding = SimpleNamespace(
            id=21,
            database_id=12,
            datasource_alias_id=8,
            environment=0,
            test_object_id=None,
            database=test_database,
        )
        production_binding = SimpleNamespace(
            id=22,
            database_id=13,
            datasource_alias_id=8,
            environment=2,
            test_object_id=None,
            database=production_database,
        )
        columns = [{
            "name": "id",
            "db_type": "BIGINT",
            "nullable": False,
            "primary_key": True,
            "autoincrement": True,
            "max_length": None,
        }]
        expected = DataFactorySchemaMonitorService.columns_signature(columns)

        with (
            patch("src.apps.data_factory.services.schema_monitor.DataFactoryEntity.objects") as entity_objects,
            patch(
                "src.apps.data_factory.services.schema_monitor.DataFactoryDatasourceBinding.objects") as binding_objects,
            patch.object(DataFactorySchemaMonitorService, "configured_validation_environments", return_value=[0]),
            patch.object(DataFactorySchemaMonitorService, "entity_signatures", return_value={57: expected}),
            patch.object(
                DataFactoryDiscover,
                "get_mysql_table_schemas",
                return_value={"t_file_info": {"columns": columns}},
            ) as get_schemas,
            patch.object(DataFactorySchemaMonitorService, "disable_entity") as disable_entity,
        ):
            entity_objects.select_related.return_value.filter.return_value = [entity]
            binding_objects.select_related.return_value.filter.return_value = [
                test_binding,
                production_binding,
            ]

            result = DataFactorySchemaMonitorService.scan()

        self.assertEqual(result["scanned_binding_count"], 1)
        self.assertEqual(result["scanned_database_count"], 1)
        get_schemas.assert_called_once_with(test_database, [entity.table_name])
        disable_entity.assert_not_called()

    def test_scan_does_not_disable_entity_when_database_is_unavailable(self):
        entity = SimpleNamespace(
            id=57,
            name="文件信息",
            table_name="t_file_info",
            datasource_alias_id=8,
        )
        database = SimpleNamespace(id=12, password="secret")
        binding = SimpleNamespace(id=21, database_id=12, datasource_alias_id=8, database=database)

        with (
            patch("src.apps.data_factory.services.schema_monitor.DataFactoryEntity.objects") as entity_objects,
            patch(
                "src.apps.data_factory.services.schema_monitor.DataFactoryDatasourceBinding.objects") as binding_objects,
            patch.object(DataFactorySchemaMonitorService, "entity_signatures", return_value={57: ()}),
            patch.object(
                DataFactoryDiscover,
                "get_mysql_table_schemas",
                side_effect=Exception("连接失败 secret"),
            ),
            patch.object(DataFactorySchemaMonitorService, "disable_entity") as disable_entity,
        ):
            entity_objects.select_related.return_value.filter.return_value = [entity]
            binding_objects.select_related.return_value.filter.return_value = [binding]

            result = DataFactorySchemaMonitorService.scan()

        self.assertEqual(result["changed_entity_count"], 0)
        self.assertEqual(result["failed_binding_count"], 1)
        self.assertNotIn("secret", result["errors"][0]["error"])
        disable_entity.assert_not_called()

    def test_scan_blocks_abnormal_bulk_disable(self):
        entities = [
            SimpleNamespace(
                id=index,
                name=f"实体{index}",
                table_name=f"table_{index}",
                datasource_alias_id=8,
            )
            for index in range(1, 13)
        ]
        database = SimpleNamespace(id=12, password="secret")
        binding = SimpleNamespace(id=21, database_id=12, datasource_alias_id=8, database=database)
        expected = {
            entity.id: (("id", "BIGINT", False, True, True, None),)
            for entity in entities
        }

        with (
            patch("src.apps.data_factory.services.schema_monitor.DataFactoryEntity.objects") as entity_objects,
            patch(
                "src.apps.data_factory.services.schema_monitor.DataFactoryDatasourceBinding.objects") as binding_objects,
            patch.object(DataFactorySchemaMonitorService, "entity_signatures", return_value=expected),
            patch.object(DataFactoryDiscover, "get_mysql_table_schemas", return_value={}),
            patch.object(DataFactorySchemaMonitorService, "disable_entity") as disable_entity,
        ):
            entity_objects.select_related.return_value.filter.return_value = entities
            binding_objects.select_related.return_value.filter.return_value = [binding]

            result = DataFactorySchemaMonitorService.scan()

        self.assertEqual(result["detected_changed_entity_count"], 12)
        self.assertEqual(result["changed_entity_count"], 0)
        self.assertTrue(result["auto_disable_blocked"])
        self.assertIn("12/12", result["safety_message"])
        disable_entity.assert_not_called()

    def test_template_fails_before_execution_when_related_entity_is_disabled(self):
        root = SimpleNamespace(
            id=1,
            entity=SimpleNamespace(name="主表", status=StatusEnum.SUCCESS.value),
        )
        child = SimpleNamespace(
            id=2,
            entity=SimpleNamespace(name="关联表", status=StatusEnum.FAIL.value),
        )
        item = SimpleNamespace(child_template=child)

        with patch.object(
                DataFactoryRunner,
                "get_template_items",
                side_effect=lambda template: [item] if template.id == 1 else [],
        ):
            with self.assertRaises(DataFactoryError) as error:
                DataFactoryRunner.require_template_entities_available(root)

        self.assertIn("关联表", error.exception.msg)

    def test_template_fails_before_execution_when_template_is_disabled(self):
        template = SimpleNamespace(
            id=1,
            name="任务场景",
            status=StatusEnum.FAIL.value,
            config_status=DataFactoryTemplateConfigStatusEnum.READY.value,
            entity=SimpleNamespace(status=StatusEnum.SUCCESS.value),
        )

        with self.assertRaises(DataFactoryError) as error:
            DataFactoryRunner.require_template_entities_available(template)

        self.assertIn("场景模板已停用", error.exception.msg)

    def test_template_fails_before_execution_when_config_is_incomplete(self):
        template = SimpleNamespace(
            id=1,
            name="任务场景",
            status=StatusEnum.SUCCESS.value,
            config_status=DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value,
            entity=SimpleNamespace(status=StatusEnum.SUCCESS.value),
        )

        with self.assertRaises(DataFactoryError) as error:
            DataFactoryRunner.require_template_entities_available(template)

        self.assertIn("配置未通过完整性校验", error.exception.msg)


class DataFactoryTemplateStatusTests(SimpleTestCase):
    def test_enabling_template_must_validate_first(self):
        template = MagicMock(
            id=101,
            status=StatusEnum.FAIL.value,
            entity=MagicMock(),
        )
        with (
            patch.object(
                DataFactoryTemplate.objects,
                "select_related",
            ) as select_related,
            patch.object(DataFactoryTemplateService, "validate_activation") as validate_activation,
        ):
            select_related.return_value.get.return_value = template

            result = DataFactoryTemplateService.set_status(101, StatusEnum.SUCCESS.value, test_env=2)

        validate_activation.assert_called_once_with(template, 2)
        self.assertEqual(result.status, StatusEnum.SUCCESS.value)
        template.save.assert_called_once()


class DataFactoryDiscoverTests(SimpleTestCase):
    def test_extract_comment_enum_options(self):
        options = DataFactoryDiscover.extract_comment_enum_options("是否有效，1 有效，0 无效", "integer")

        self.assertEqual(options, [
            {"label": "有效", "value": 1},
            {"label": "无效", "value": 0},
        ])

    def test_extract_comment_enum_options_with_compact_separators(self):
        self.assertEqual(
            DataFactoryDiscover.extract_comment_enum_options("订单类型状态 0.禁用状态 1.启用状态", "integer"),
            [
                {"label": "禁用状态", "value": 0},
                {"label": "启用状态", "value": 1},
            ],
        )
        self.assertEqual(
            DataFactoryDiscover.extract_comment_enum_options("是否签约倒签 0.不是 1.是 2.未知", "integer"),
            [
                {"label": "不是", "value": 0},
                {"label": "是", "value": 1},
                {"label": "未知", "value": 2},
            ],
        )

    def test_extract_comment_enum_options_with_parentheses_and_equals(self):
        self.assertEqual(
            DataFactoryDiscover.extract_comment_enum_options("状态（0=无效，1=有效）", "integer"),
            [
                {"label": "无效", "value": 0},
                {"label": "有效", "value": 1},
            ],
        )
        self.assertEqual(
            DataFactoryDiscover.extract_comment_enum_options("状态 0（无效） 1（有效）", "integer"),
            [
                {"label": "无效", "value": 0},
                {"label": "有效", "value": 1},
            ],
        )

    def test_db_enum_options_use_comment_labels(self):
        self.assertEqual(
            DataFactoryDiscover.extract_enum_options("ENUM('0','1')", "状态：0无效，1有效", "enum"),
            [
                {"label": "无效", "value": "0"},
                {"label": "有效", "value": "1"},
            ],
        )

    def test_comment_enum_options_drive_enum_generator_config(self):
        column = {
            "name": "valid",
            "type": "TINYINT",
            "comment": "是否有效，1 有效，0 无效",
            "nullable": False,
            "autoincrement": False,
        }

        result = DataFactoryDiscover._normalize_column(column, [], set(), 0)

        self.assertEqual(result["generator_type"], DataFactoryGeneratorTypeEnum.ENUM.value)
        self.assertEqual(result["enum_values"], [1, 0])
        self.assertEqual(result["generator_config"]["options"], [
            {"label": "有效", "value": 1},
            {"label": "无效", "value": 0},
        ])

from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.db import connections
from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.data_factory.enums import (
    DataFactoryCleanupStatusEnum as CleanupStatus, DataFactoryCleanupStrategyEnum as Strategy,
    DataFactoryExecutionStatusEnum as ExecutionStatus,
)
from src.apps.data_factory.models import Database, DataFactoryExecution, DataFactoryExecutionItem
from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector as Selector
from src.apps.data_factory.services.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.services.datasource_wait import DatasourceWaitService
from src.apps.data_factory.services.execution_capacity import DatasourceExecutionCapacityService as Capacity
from src.apps.system.enums.executor import ExecutorTaskTypeEnum, ExecutorTaskStatusEnum as TaskStatus
from src.apps.task_center.models import ExecutorTask


class CleanupBacklogQueryTests(TestCase):
    """只在临时 SQLite 建表验证真实查询；不运行迁移、不访问环境库。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.directory = TemporaryDirectory(prefix='mango-backlog-')
        cls.alias = 'isolated_backlog'
        config = deepcopy(connections['default'].settings_dict)
        config.update(ENGINE='django.db.backends.sqlite3', NAME=str(Path(cls.directory.name) / 'control.db'),
                      USER='', PASSWORD='', HOST='', PORT='', OPTIONS={}, TIME_ZONE=None)
        connections.databases[cls.alias] = config
        cls.connection = connections[cls.alias]
        cls.models = [Database, DataFactoryExecution, DataFactoryExecutionItem, ExecutorTask]
        with cls.connection.schema_editor() as editor:
            for model in cls.models:
                editor.create_model(model)
        cls.connection.disable_constraint_checking()

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        del connections.databases[cls.alias]
        delattr(connections._connections, cls.alias)
        cls.directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        for model in reversed(self.models):
            model.objects.using(self.alias).all()._raw_delete(self.alias)
        self.execution = DataFactoryExecution.objects.using(self.alias).create(
            execution_no='AUTO_BACKLOG', project_product_id=1, status=ExecutionStatus.SUCCESS.value)
        for model in self.models:
            guard = patch.object(model, 'objects', model.objects.db_manager(self.alias))
            guard.start()
            self.addCleanup(guard.stop)

    def item(self, **values):
        return DataFactoryExecutionItem.objects.create(execution_id=self.execution.id, database_id=1,
            **{'cleanup_strategy': Strategy.EXECUTION_END.value, 'alias': 'AUTO', **values})

    def task(self, **values):
        return ExecutorTask.objects.create(task_type=ExecutorTaskTypeEnum.DATA_FACTORY_CLEANUP.value,
            business_id=self.execution.id, expired_at=timezone.now(), **values)

    def test_live_fixtures_are_not_backlog_and_queued_sql_es_items_are(self):
        items = [self.item(), self.item(cleanup_resources={'sql_done': True})]
        self.assertEqual(Selector.cleanup_backlog([1], 100), 0)
        self.task(status=TaskStatus.PENDING.value)
        self.assertEqual(Selector.cleanup_backlog([1], 100), 2)
        # 重复历史任务不应重复计算子表/关联表明细。
        self.task(status=TaskStatus.FAILED.value)
        self.assertEqual(Selector.cleanup_backlog([1], 100), 2)
        items[0].cleanup_status = CleanupStatus.SUCCESS.value
        items[0].save()
        self.assertEqual(Selector.cleanup_backlog([1], 100), 1)

    def test_failed_cleanup_counts_without_task_and_intentional_retention_does_not(self):
        self.item(cleanup_status=CleanupStatus.FAIL.value)
        self.item(cleanup_strategy=Strategy.MANUAL.value)
        self.item(cleanup_strategy=Strategy.NONE.value)
        self.assertEqual(Selector.cleanup_backlog([1], 100), 1)
        self.execution.status = ExecutionStatus.FAIL.value
        self.execution.save()
        self.item()
        self.assertEqual(Selector.cleanup_backlog([1], 100), 2)
        self.assertEqual(Selector.cleanup_backlog([1], 1), 1)
        self.assertEqual(Selector.cleanup_backlog([2], 100), 0)

    def test_shared_es_backlog_is_visible_even_when_mysql_instance_differs(self):
        self.item(cleanup_resources={'version': 1, 'sql_cleaned': True,
            'snapshots': [{'connection_id': 9}, {'connection_id': 9}]})
        task = self.task(status=TaskStatus.RUNNING.value)
        self.assertEqual(Selector.cleanup_backlog([9], 100, resource_connection_ids=[9]), 1)
        self.assertEqual(Selector.cleanup_backlog([8], 100, resource_connection_ids=[8]), 0)
        task.status = TaskStatus.SUCCESS.value
        task.save()
        self.assertEqual(Selector.cleanup_backlog([9], 100, resource_connection_ids=[9]), 1)


class CleanupBacklogAdmissionTests(SimpleTestCase):
    def test_only_new_fixture_waits_and_resumes_without_sql_permit_or_retry(self):
        policy = DatasourcePerformancePolicy()
        policy.mysql.cleanup_backlog_limit = 2
        one = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        alias = SimpleNamespace(id=2, db_type=0, host='mysql.example.com', port=3306)
        other = SimpleNamespace(id=3, db_type=0, host='other.example.com', port=3306)
        group = Governor.target_policy(one, policy)[2]
        with patch.object(Governor, 'policy', return_value=policy), \
                patch.object(Capacity, 'targets_by_scope', return_value={(1, 0): {group: one}}), \
                patch.object(Selector, 'performance_targets', return_value=[one, alias, other]), \
                patch.object(Selector, 'cleanup_backlog', side_effect=[2, 1]) as backlog, \
                patch.object(DatasourceWaitService, 'pause') as pause, \
                patch.object(Governor, 'acquire') as acquire:
            Capacity.wait_for_cleanup_backlog(1, 0)
        self.assertEqual(backlog.call_args.args, ([1, 2], 2))
        pause.assert_called_once_with(1)
        acquire.assert_not_called()

    def test_wait_propagates_stop_and_control_failure_without_creating_data(self):
        from django.db import OperationalError
        from src.apps.data_factory.exceptions import DataFactoryError
        from src.apps.data_factory.services.infrastructure import DatasourceInfrastructureService as Infrastructure
        policy = DatasourcePerformancePolicy()
        one = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        group = Governor.target_policy(one, policy)[2]
        with patch.object(Governor, 'policy', return_value=policy), \
                patch.object(Capacity, 'targets_by_scope', return_value={(1, 0): {group: one}}), \
                patch.object(Selector, 'performance_targets', return_value=[one]), \
                patch.object(Selector, 'cleanup_backlog', side_effect=OperationalError('example unavailable')), \
                Infrastructure.scope():
            with self.assertRaises(DataFactoryError) as error:
                Capacity.wait_for_cleanup_backlog(1, 0)
            self.assertEqual(error.exception.code, 34185)
            self.assertEqual(Infrastructure.current()[0].code, 34185)

    def test_long_backlog_wait_keeps_existing_owner_and_stop_interrupts_new_fixture(self):
        policy = DatasourcePerformancePolicy()
        one = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        group = Governor.target_policy(one, policy)[2]
        with patch.object(Governor, 'policy', return_value=policy), \
                patch.object(Capacity, 'targets_by_scope', return_value={(1, 0): {group: one}}), \
                patch.object(Selector, 'performance_targets', return_value=[one]), \
                patch.object(Selector, 'cleanup_backlog', side_effect=[100] * 45 + [0]), \
                patch.object(DatasourceWaitService, 'pause') as pause:
            Capacity.wait_for_cleanup_backlog(1, 0)
            self.assertEqual(pause.call_count, 45)
        with patch.object(Governor, 'policy', return_value=policy), \
                patch.object(Capacity, 'targets_by_scope', return_value={(1, 0): {group: one}}), \
                patch.object(Selector, 'performance_targets', return_value=[one]), \
                patch.object(Selector, 'cleanup_backlog', return_value=100), \
                patch.object(DatasourceWaitService, 'pause', side_effect=InterruptedError('AUTO stop')):
            with self.assertRaises(InterruptedError):
                Capacity.wait_for_cleanup_backlog(1, 0)

    def test_root_entries_wait_before_execution_record_and_previews_do_not(self):
        from src.apps.data_factory.services.runner import DataFactoryRunner
        template = SimpleNamespace(project_product_id=1)
        for method in (DataFactoryRunner.run_template, DataFactoryRunner.debug_run_template):
            with self.subTest(entry=method.__name__), \
                    patch.object(DataFactoryRunner, 'get_template', return_value=template), \
                    patch.object(DataFactoryRunner, 'require_template_entities_available'), \
                    patch.object(Capacity, 'wait_for_fixture', side_effect=InterruptedError('AUTO stop')) as wait, \
                    patch('src.apps.data_factory.services.runner_parts.execution.DataFactoryExecution.objects.create') as create:
                with self.assertRaises(InterruptedError):
                    method(1, test_object_id=1, **({'source_type': 4} if method.__name__ == 'run_template' else {}))
                wait.assert_called_once_with(template, 1)
                create.assert_not_called()

    def test_policy_no_longer_contains_case_lifecycle_limit(self):
        from pydantic import ValidationError
        budget = DatasourcePerformancePolicy().mysql
        self.assertNotIn('case_concurrency', budget.model_dump())
        self.assertNotIn('api_concurrency', budget.model_dump())
        self.assertNotIn('api_requests_per_second', budget.model_dump())
        from src.apps.data_factory.schemas.performance import DatasourceGovernorState
        from src.apps.data_factory.enums.performance import DatasourcePermitKindEnum
        self.assertNotIn('api_tokens', DatasourceGovernorState().model_dump())
        self.assertEqual({kind.value for kind in DatasourcePermitKindEnum}, {'operation', 'connection'})
        self.assertEqual(budget.cleanup_backlog_limit, 100)
        for value in (0, -1, True, '100'):
            with self.assertRaises(ValidationError):
                DatasourcePerformancePolicy.model_validate({'mysql': {'cleanup_backlog_limit': value}}, strict=True)

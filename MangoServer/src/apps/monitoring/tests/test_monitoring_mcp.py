import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.test import SimpleTestCase, override_settings
from pydantic import ValidationError

from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.exceptions import MonitoringError
from src.apps.monitoring.models import MonitoringTask, MonitoringReport
from src.apps.monitoring.schemas.task import MonitoringTaskCreate, MonitoringTaskPatch
from src.apps.monitoring.selectors.task import MonitoringTaskSelector
from src.apps.monitoring.services.task_log import MonitoringTaskLogService
from src.apps.monitoring.services.task_mutation import MonitoringTaskMutationService as Mutation
from src.apps.test_center.models import NoticeGroup, ProjectProduct
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


class MonitoringMcpServiceTests(SimpleTestCase):
    def test_log_path_repair_is_scoped_idempotent_and_does_not_change_runtime_state(self):
        from src.apps.monitoring.services.log_path import MonitoringLogPathService
        from django.core.management import call_command
        import io

        tasks = [self.create() for _ in range(4)]
        originals = [None, '', '  ', 'monitoring/logs/existing.log']
        for task, path in zip(tasks, originals):
            MonitoringTask.objects.filter(id=task.id).update(log_path=path, status=MonitoringTaskStatusEnum.FAILED.value,
                                                           exit_code=-1, pid=None)
        before = list(MonitoringTask.objects.order_by('id').values())
        output = io.StringIO()
        call_command('repair_monitoring_log_paths', task_ids=[tasks[0].id, tasks[1].id], stdout=output)
        self.assertIn('仅预览', output.getvalue())
        self.assertEqual(list(MonitoringTask.objects.order_by('id').values()), before)
        selected = [tasks[0].id, tasks[1].id, tasks[3].id]
        result = MonitoringLogPathService.repair_missing(selected, apply=True)
        self.assertEqual(result, {'missing': 2, 'repaired': 2})
        after = list(MonitoringTask.objects.order_by('id').values())
        for old, new in zip(before, after):
            if old['id'] in selected and old['log_path'] in (None, ''):
                self.assertRegex(new['log_path'], r'^monitoring/logs/[0-9a-f]{32}\.log$')
            else:
                self.assertEqual(new['log_path'], old['log_path'])
            self.assertEqual({key: value for key, value in old.items() if key != 'log_path'},
                             {key: value for key, value in new.items() if key != 'log_path'})
        self.assertEqual(MonitoringLogPathService.repair_missing(selected, apply=True)['repaired'], 0)
        output = io.StringIO()
        call_command('repair_monitoring_log_paths', apply=True, stdout=output)
        self.assertIn('已补齐 1 个', output.getvalue())

    def setUp(self):
        self.alias = 'monitoring_mcp'
        self.db = DatabaseWrapper({
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'USER': '', 'PASSWORD': '',
            'HOST': '', 'PORT': '', 'OPTIONS': {}, 'TIME_ZONE': None, 'AUTOCOMMIT': True,
            'CONN_MAX_AGE': 0, 'CONN_HEALTH_CHECKS': False, 'ATOMIC_REQUESTS': False,
        }, alias=self.alias)
        self.db.ensure_connection()
        connections[self.alias] = self.db
        self.addCleanup(self.close)
        for model in (MonitoringTask, MonitoringReport, ProjectProduct, NoticeGroup):
            with self.db.cursor() as cursor:
                columns = ', '.join(f'"{field.column}" {field.db_type(self.db)}'
                                    + (' PRIMARY KEY' if field.primary_key else '') for field in model._meta.concrete_fields)
                cursor.execute(f'CREATE TABLE "{model._meta.db_table}" ({columns})')
            mocked = patch.object(model, 'objects', model.objects.using(self.alias))
            mocked.start()
            self.addCleanup(mocked.stop)
        for target, value in ((PermissionMenuService, False),):
            mocked = patch.object(target, 'is_effective_super_admin', return_value=value)
            mocked.start()
            self.addCleanup(mocked.stop)
        for method, value in (('can_view_all_project_data', False), ('project_product_ids_for_user', {1})):
            mocked = patch.object(ProjectProductScopeService, method, return_value=value)
            mocked.start()
            self.addCleanup(mocked.stop)
        config = patch('src.apps.system.services.system_config.SystemConfigService.get_environment_display_names', return_value={})
        config.start()
        self.addCleanup(config.stop)
        ProjectProduct.objects.bulk_create([ProjectProduct(id=1, project_id=1, name='示例产品'),
                                            ProjectProduct(id=2, project_id=2, name='其他产品')])
        NoticeGroup.objects.bulk_create([NoticeGroup(id=1, project_id=1, name='示例通知组'),
                                        NoticeGroup(id=2, project_id=2, name='其他通知组')])
        self.user = SimpleNamespace(id=7)

    def close(self):
        del connections[self.alias]
        self.db.connection.close()

    def create(self, **values):
        return Mutation.create(self.user, 1, MonitoringTaskCreate(name='示例脚本', script_content='print("ok")', **values))

    def test_create_and_partial_update_do_not_start_script(self):
        task = self.create()
        self.assertEqual(task.status, MonitoringTaskStatusEnum.QUEUED.value)
        self.assertTrue(task.log_path.startswith('monitoring/logs/'))
        original_path = task.log_path
        updated = Mutation.update.__wrapped__(Mutation, self.user, task.id, MonitoringTaskPatch(description='新说明'))
        self.assertEqual(updated.script_content, 'print("ok")')
        self.assertEqual(updated.log_path, original_path)
        self.assertEqual(updated.update_user_id, 7)
        self.assertEqual(updated.status, MonitoringTaskStatusEnum.QUEUED.value)

    def test_scope_and_notification_project_checks(self):
        for product in (2, 999):
            with self.assertRaises(MonitoringError):
                Mutation.create(self.user, product, MonitoringTaskCreate(name='示例', script_content='pass'))
        with self.assertRaises(MonitoringError):
            self.create(is_notice=1, notice_group_id=2)
        with self.assertRaises(MonitoringError):
            self.create(is_notice=1)
        task = self.create(is_notice=1, notice_group_id=1)
        with self.assertRaises(MonitoringError):
            Mutation.update.__wrapped__(Mutation, self.user, task.id, MonitoringTaskPatch(notice_group_id=None))
        MonitoringTask.objects.filter(id=task.id).update(project_product_id=2)
        self.assertEqual(MonitoringTaskSelector.visible(self.user).count(), 0)
        for action in (lambda: MonitoringTaskSelector.get(self.user, task.id),
                       lambda: Mutation.update.__wrapped__(Mutation, self.user, task.id, MonitoringTaskPatch(name='修改')),
                       lambda: Mutation.start(self.user, task.id),
                       lambda: Mutation.stop.__wrapped__(Mutation, self.user, task.id)):
            with self.assertRaises(MonitoringError):
                action()

    def test_runtime_fields_and_invalid_values_are_rejected(self):
        for values in ({'pid': 123}, {'status': 1}, {'log_path': '/example.log'}, {'project_product_id': 2},
                       {'script_content': '  '}, {'test_env': 999}, {'is_notice': 3}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                MonitoringTaskPatch(**values)
        task = self.create()
        with self.assertRaises(MonitoringError):
            Mutation.update.__wrapped__(Mutation, self.user, task.id, MonitoringTaskPatch(script_content=None))

    def test_start_reuses_control_service_and_stop_only_sets_desired_state(self):
        task = self.create()
        with patch('src.apps.monitoring.services.task_mutation.MonitoringTaskControlService.request_start', return_value=task) as start:
            Mutation.start(self.user, task.id)
            self.assertEqual(start.call_args.args[0].id, task.id)
        stopped = Mutation.stop.__wrapped__(Mutation, self.user, task.id)
        self.assertEqual(stopped.status, MonitoringTaskStatusEnum.STOPPED.value)

    def test_logs_are_bounded_and_cannot_read_outside_log_root(self):
        task = self.create()
        with tempfile.TemporaryDirectory() as directory, override_settings(MONITORING_LOG_DIR=directory):
            path = Path(directory) / Path(task.log_path).name
            path.write_text('line\n' * 20000, encoding='utf-8')
            result = MonitoringTaskLogService.tail(self.user, task.id, 2)
            self.assertEqual(result['lines'], ['line', 'line'])
            self.assertTrue(result['truncated'])
            MonitoringTask.objects.filter(id=task.id).update(log_path=str(Path(directory).parent / 'outside.log'))
            with self.assertRaises(MonitoringError):
                MonitoringTaskLogService.tail(self.user, task.id)

    def test_current_failure_reason_survives_missing_file_and_is_not_reused_after_restart(self):
        from django.utils import timezone
        from src.apps.monitoring.services.task_diagnostic import MonitoringTaskDiagnosticService

        task = self.create()
        task.status = MonitoringTaskStatusEnum.FAILED.value
        task.exit_code = 1
        task.stopped_at = timezone.now()
        task.save(update_fields=['status', 'exit_code', 'stopped_at'])
        MonitoringTaskDiagnosticService.record(task, "ModuleNotFoundError: No module named 'example_missing_package'; token=example-secret")
        with tempfile.TemporaryDirectory() as directory, override_settings(MONITORING_LOG_DIR=directory):
            result = MonitoringTaskLogService.tail(self.user, task.id)
            self.assertIn('example_missing_package', '\n'.join(result['lines']))
            self.assertNotIn('example-secret', '\n'.join(result['lines']))
            task.stopped_at = timezone.now()
            task.save(update_fields=['stopped_at'])
            self.assertIsNone(MonitoringTaskSelector.failure_reason(task))
            result = MonitoringTaskLogService.tail(self.user, task.id)
            self.assertIn('历史记录未保存', '\n'.join(result['lines']))

    def test_log_endpoint_preserves_line_array_and_uses_diagnostic_fallback(self):
        from src.apps.monitoring.api.views.monitoring_task import MonitoringTaskViews
        from django.http import QueryDict

        task = self.create()
        request = SimpleNamespace(query_params=QueryDict(f'id={task.id}&limit=500'), user=SimpleNamespace(user_obj=self.user))
        with patch.object(MonitoringTaskLogService, 'read_task', return_value={'lines': ['[ERROR] 示例启动失败']}) as read:
            response = MonitoringTaskViews().logs(request)
        self.assertEqual(response.data['data'], ['[ERROR] 示例启动失败\n'])
        self.assertEqual(read.call_args.args[0].id, task.id)

from types import SimpleNamespace
from unittest.mock import patch

from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext

from src.apps.task_center.api.serializers.tasks import TasksSerializers
from src.apps.task_center.constants import TASK_FINE_TUNING_FIELDS
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.models import ScheduledTaskGroup, ScheduledTaskGroupModule, Tasks, TimeTasks
from src.apps.task_center.services.scheduling.task_group import ScheduledTaskGroupService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.task_center.services.selection.save_validation import ScheduledTaskSaveValidationService as Validation
from src.apps.test_center.models import Project, ProjectProduct, ProductModule
from src.apps.user.models import User


class TaskFineTuningTests(SimpleTestCase):
    def setUp(self):
        self.alias = 'task_fine_tuning'
        self.db = DatabaseWrapper({
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'USER': '', 'PASSWORD': '',
            'HOST': '', 'PORT': '', 'OPTIONS': {}, 'TIME_ZONE': None, 'AUTOCOMMIT': True,
            'CONN_MAX_AGE': 0, 'CONN_HEALTH_CHECKS': False, 'ATOMIC_REQUESTS': False,
        }, alias=self.alias)
        self.db.ensure_connection()
        connections[self.alias] = self.db
        self.addCleanup(self.close)
        config = patch('src.apps.system.services.system_config.SystemConfigService.get_environment_display_names', return_value={})
        config.start()
        self.addCleanup(config.stop)
        models = (User, Project, ProjectProduct, ProductModule, TimeTasks, Tasks, ScheduledTaskGroup,
                  ScheduledTaskGroupModule, Tasks.timing_strategies.through, ScheduledTaskGroup.timing_strategies.through)
        with self.db.cursor() as cursor:
            for model in models:
                columns = ', '.join(f'"{field.column}" {field.db_type(self.db)}'
                                    + (' PRIMARY KEY' if field.primary_key else '') for field in model._meta.concrete_fields)
                cursor.execute(f'CREATE TABLE "{model._meta.db_table}" ({columns})')
        for model in models:
            mock = patch.object(model, 'objects', model.objects.using(self.alias))
            mock.start()
            self.addCleanup(mock.stop)
        User.objects.bulk_create([User(id=index, username=f'user{index}@example.com', name=f'负责人{index}') for index in (1, 2, 3)])
        Project.objects.bulk_create([Project(id=1, name='示例项目')])
        ProjectProduct.objects.bulk_create([ProjectProduct(id=1, project_id=1, name='示例产品')])
        ProductModule.objects.bulk_create([ProductModule(id=index, project_product_id=1, name=f'模块{index}', level=1) for index in (1, 2)])
        self.modules = list(ProductModule.objects.order_by('id'))
        TimeTasks.objects.bulk_create([TimeTasks(id=1, name='示例策略', cron='0 0 * * *')])
        ScheduledTaskGroup.objects.bulk_create([ScheduledTaskGroup(
            id=1, project_product_id=1, name='示例任务组', test_envs=[1], case_types=[1],
            execution_scenes=['routine_regression'], case_people_id=1, status=0,
        )])
        self.group = ScheduledTaskGroup.objects.get(id=1)
        self.group.timing_strategies.set([1])
        ScheduledTaskGroupService._sync_members(self.group, self.modules[:1], 1)
        self.task = Tasks.objects.get()

    def close(self):
        del connections[self.alias]
        self.db.connection.close()

    def serializer(self, data):
        serializer = TasksSerializers(self.task, data=data, partial=True)
        serializer.fields['case_people'].queryset = User.objects
        serializer.fields['update_user'].queryset = User.objects
        return serializer

    def test_three_fields_are_accepted_and_only_changed_columns_are_written(self):
        with patch.object(ApiConcurrencyService, 'platform_limit', return_value=10):
            serializer = self.serializer({'id': self.task.id, 'api_concurrency_limit': 2,
                                          'case_people': 2, 'report_retention_policy': 'abnormal_only'})
            self.assertTrue(serializer.is_valid(), serializer.errors)
        with CaptureQueriesContext(self.db) as queries:
            task = Validation.update_group_task.__wrapped__(Validation, self.task, serializer.validated_data)
        self.assertEqual((task.api_concurrency_limit, task.case_types, task.case_people_id, task.report_retention_policy),
                         (2, [1], 2, 'abnormal_only'))
        sql = next(row['sql'] for row in queries if row['sql'].startswith('UPDATE'))
        self.assertNotIn('"test_envs"', sql)
        self.assertNotIn('"timing_strategies"', sql)
        self.assertNotIn('"name"', sql)
        self.assertNotIn('"case_types"', sql)

    def test_common_and_readonly_fields_are_rejected_not_silently_ignored(self):
        for key, value in {'name': '改名', 'test_envs': [2], 'timing_strategies': [1], 'project_product': 1,
                           'module': 2, 'execution_scenes': [], 'status': 1, 'is_notice': 1,
                           'notice_group': None, 'task_group': None, 'task_group_revision': 100,
                           'case_types': [0]}.items():
            with self.subTest(field=key), self.assertRaises(TaskCenterError):
                self.serializer({key: value}).is_valid(raise_exception=True)

    def test_group_update_and_repeated_sync_preserve_all_fine_tuning(self):
        Tasks.objects.filter(id=self.task.id).update(api_concurrency_limit=3, case_types=[0], case_people_id=2,
                                                   report_retention_policy='abnormal_only')
        payload = dict(project_product_id=1, name='组公共配置已修改', module_ids=[1, 2], timing_strategies=[1],
                       test_envs=[0], case_types=[2], execution_scenes=['routine_regression'],
                       case_people=3, status=0, is_notice=0, fail_notice=0)
        with patch.object(ScheduledTaskGroupService, 'serialize', return_value={}):
            ScheduledTaskGroupService.update.__wrapped__(ScheduledTaskGroupService, 1, payload, 3)
        self.group.refresh_from_db()
        for _ in range(2):
            ScheduledTaskGroupService._sync_members(self.group, self.modules, 3)
        self.task.refresh_from_db()
        self.assertEqual(self.task.case_types, [2])
        self.assertEqual(self.task.case_people_id, 2)
        self.assertEqual(self.task.api_concurrency_limit, 3)
        self.assertEqual(self.task.report_retention_policy, 'abnormal_only')
        self.assertEqual(self.task.test_envs, [0])
        new_task = Tasks.objects.get(module_id=2)
        self.assertEqual(new_task.case_types, [2])
        self.assertEqual(new_task.case_people_id, 3)
        self.assertIsNone(new_task.api_concurrency_limit)

    def test_sync_sql_never_rewrites_independent_columns(self):
        with CaptureQueriesContext(self.db) as queries:
            ScheduledTaskGroupService._sync_members(self.group, self.modules[:1], 2)
        sql = next(row['sql'] for row in queries if row['sql'].startswith('UPDATE "tasks"'))
        for field in TASK_FINE_TUNING_FIELDS:
            self.assertNotIn(f'"{field}"', sql)
        self.assertNotIn('"case_people_id"', sql)

    def test_sync_preserves_child_disable_and_respects_group_disable(self):
        member = ScheduledTaskGroupModule.objects.get(task_id=self.task.id)
        member.child_enabled = False
        member.save(update_fields=['child_enabled'])
        self.group.status = 1
        ScheduledTaskGroupService._sync_members(self.group, self.modules[:1], 1)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 0)
        member.refresh_from_db()
        self.assertFalse(member.child_enabled)
        member.child_enabled = True
        member.save(update_fields=['child_enabled'])
        self.group.status = 0
        ScheduledTaskGroupService._sync_members(self.group, self.modules[:1], 1)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 0)
        self.group.status = 1
        ScheduledTaskGroupService._sync_members(self.group, self.modules[:1], 1)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 1)

    def test_fine_patch_preserves_group_changes_made_since_original_read(self):
        Tasks.objects.filter(id=self.task.id).update(name='并发修改后的名称', test_envs=[2])
        result = Validation.update_group_task.__wrapped__(Validation, self.task, {'report_retention_policy': 'abnormal_only'})
        self.assertEqual(result.name, '并发修改后的名称')
        self.assertEqual(result.test_envs, [2])

    def test_invalid_cases_and_concurrency_still_reject(self):
        with self.assertRaises(TaskCenterError):
            self.serializer({'case_types': [99]}).is_valid(raise_exception=True)
        with patch.object(ApiConcurrencyService, 'platform_limit', return_value=2), self.assertRaises(TaskCenterError):
            self.serializer({'api_concurrency_limit': 3}).is_valid(raise_exception=True)

    def test_retention_only_remains_supported(self):
        serializer = self.serializer({'report_retention_policy': 'abnormal_only'})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_enabled_type_change_is_rejected_even_if_matching_cases_exist(self):
        self.task.status = 1
        with patch('src.apps.task_center.services.selection.save_validation.ScheduledTaskCaseSelectionService.select', return_value=[object()]):
            with self.assertRaises(TaskCenterError):
                Validation.validate_group_update({'case_types': [0]}, self.task)

    def test_legacy_module_endpoints_cannot_overwrite_or_delete_group_children(self):
        from src.apps.task_center.services.selection.module_full_config import ModuleFullTaskConfigService as Legacy
        for action, args in ((Legacy.update_row, (self.task.id, {})), (Legacy.delete_row, (self.task.id,)),
                             (Legacy.replace, (1, []))):
            with self.subTest(action=action.__name__), self.assertRaises(TaskCenterError):
                action.__wrapped__(Legacy, *args)

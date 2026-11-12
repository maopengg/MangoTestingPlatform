from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from src.apps.task_center.api.views.task_group import ScheduledTaskGroupTriggerViews, ScheduledTaskGroupViews
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.services.scheduling.fire import ScheduleFireService
from src.apps.task_center.services.scheduling.task_group_execution import ScheduledTaskGroupExecutionService
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class ScheduleFireDeduplicationTests(SimpleTestCase):
    def create_fire(self, kind):
        now = timezone.now()
        if kind == 'test_suite':
            return ScheduleFireService.create_test_suite_fire(
                SimpleNamespace(id=10, name='测试任务'), SimpleNamespace(id=24), 5, now,
            )
        return ScheduleFireService.create_system_fire(
            source_type=ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            business_key='cleanup', task_name='清理任务', planned_at=now,
        )

    def test_only_existing_fire_key_is_treated_as_duplicate(self):
        for kind in ('test_suite', 'system'):
            with (
                self.subTest(kind=kind),
                patch('src.apps.task_center.services.scheduling.fire.transaction.atomic', side_effect=nullcontext),
                patch('src.apps.task_center.services.scheduling.fire.ScheduleFire.objects') as fires,
            ):
                fires.create.side_effect = IntegrityError('duplicate key')
                fires.filter.return_value.exists.return_value = True

                self.assertEqual(self.create_fire(kind), (None, False))
                fires.filter.assert_called_once_with(fire_key=fires.create.call_args.kwargs['fire_key'])

    def test_other_integrity_errors_are_not_silently_skipped(self):
        for kind in ('test_suite', 'system'):
            with (
                self.subTest(kind=kind),
                patch('src.apps.task_center.services.scheduling.fire.transaction.atomic', side_effect=nullcontext),
                patch('src.apps.task_center.services.scheduling.fire.ScheduleFire.objects') as fires,
            ):
                error = IntegrityError('different constraint')
                fires.create.side_effect = error
                fires.filter.return_value.exists.return_value = False

                with self.assertRaises(IntegrityError) as raised:
                    self.create_fire(kind)
                self.assertIs(raised.exception, error)


class TaskGroupManualTriggerTests(SimpleTestCase):
    def test_all_children_and_environments_trigger_even_when_disabled(self):
        group = SimpleNamespace(id=7, test_envs=[0, 1], status=0)
        tasks = [SimpleNamespace(id=10, status=0), SimpleNamespace(id=11, status=1)]
        with (
            patch('src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroup.objects') as groups,
            patch('src.apps.task_center.services.scheduling.task_group_execution.Tasks.objects') as task_manager,
            patch.object(ScheduledTaskGroupExecutionService, 'prepare') as prepare,
            patch.object(ScheduledTaskGroupExecutionService, 'try_finalize') as finalize,
            patch(
                'src.apps.task_center.services.scheduling.dispatch.ScheduleDispatchService.dispatch_fire') as dispatch,
        ):
            groups.filter.return_value.first.return_value = group
            task_manager.filter.return_value.order_by.return_value = tasks
            prepare.side_effect = [
                (SimpleNamespace(id=20), [SimpleNamespace(id=1), SimpleNamespace(id=2)]),
                (SimpleNamespace(id=21), [SimpleNamespace(id=3), SimpleNamespace(id=4)]),
            ]
            dispatch.side_effect = [100, None, 101, 102]
            result = ScheduledTaskGroupExecutionService.trigger_manual(7)

        self.assertEqual(result, {'task_count': 2, 'execution_count': 2,
                                  'generated_count': 3, 'failed_count': 1})
        task_manager.filter.assert_called_once_with(task_group=group)
        self.assertEqual(dispatch.call_count, 4)
        self.assertEqual([call.args[0] for call in finalize.call_args_list], [20, 21])
        self.assertEqual([call.args[3] for call in prepare.call_args_list], [0, 1])
        for call in prepare.call_args_list:
            self.assertIsNone(call.args[1])
            self.assertEqual(call.args[2], tasks)
            self.assertTrue(call.kwargs['execution_key'].startswith('manual:group:7:'))

    def test_repeat_manual_trigger_uses_independent_batches(self):
        with (
            patch('src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroup.objects') as groups,
            patch('src.apps.task_center.services.scheduling.task_group_execution.Tasks.objects') as tasks,
            patch.object(ScheduledTaskGroupExecutionService, 'prepare',
                         return_value=(SimpleNamespace(id=1), [])) as prepare,
            patch.object(ScheduledTaskGroupExecutionService, 'try_finalize'),
        ):
            groups.filter.return_value.first.return_value = SimpleNamespace(id=7, test_envs=[0])
            tasks.filter.return_value.order_by.return_value = [SimpleNamespace(id=10)]
            ScheduledTaskGroupExecutionService.trigger_manual(7)
            ScheduledTaskGroupExecutionService.trigger_manual(7)
        self.assertNotEqual(prepare.call_args_list[0].kwargs['execution_key'],
                            prepare.call_args_list[1].kwargs['execution_key'])

    def test_missing_or_empty_group_is_rejected(self):
        with patch(
                'src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroup.objects') as groups:
            groups.filter.return_value.first.return_value = None
            with self.assertRaises(TaskCenterError):
                ScheduledTaskGroupExecutionService.trigger_manual(7)
        with (
            patch('src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroup.objects') as groups,
            patch('src.apps.task_center.services.scheduling.task_group_execution.Tasks.objects') as tasks,
        ):
            groups.filter.return_value.first.return_value = SimpleNamespace(id=7)
            tasks.filter.return_value.order_by.return_value = []
            with self.assertRaises(TaskCenterError):
                ScheduledTaskGroupExecutionService.trigger_manual(7)

    def test_manual_fire_key_does_not_collide_with_scheduled_fire(self):
        with (
            patch('src.apps.task_center.services.scheduling.fire.transaction.atomic', return_value=MagicMock()),
            patch('src.apps.task_center.services.scheduling.fire.ScheduleFire.objects') as fires,
        ):
            from django.utils import timezone
            now = timezone.now()
            task = SimpleNamespace(id=10, name='测试任务')
            ScheduleFireService.create_test_suite_fire(task, SimpleNamespace(id=1), 0, now)
            ScheduleFireService.create_test_suite_fire(task, None, 0, now,
                                                       group_execution=SimpleNamespace(id=20))
            ScheduleFireService.create_test_suite_fire(task, None, 0, now,
                                                       group_execution=SimpleNamespace(id=21))
        keys = [call.kwargs['fire_key'] for call in fires.create.call_args_list]
        self.assertEqual(len(set(keys)), 3)
        self.assertEqual(fires.create.call_args.kwargs['extra_data'],
                         {'test_env': 0, 'trigger_mode': 'manual'})

    def test_endpoint_requires_login_and_execute_permission(self):
        view = ScheduledTaskGroupTriggerViews.as_view({'get': 'trigger'})
        for granted in (None, {'timing.tasks'}, {'timing.tasks:change'}):
            request = APIRequestFactory().get('/api/system/tasks/groups/trigger', {'id': 7})
            if granted is not None:
                force_authenticate(request, user=SimpleNamespace(user_obj=SimpleNamespace(id=42)))
            with (
                patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False),
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=granted or set()),
                patch.object(ScheduledTaskGroupViews, '_group') as scope,
                patch.object(ScheduledTaskGroupExecutionService, 'trigger_manual',
                             return_value={'generated_count': 2}) as trigger,
            ):
                response = view(request)
            if granted == {'timing.tasks:change'}:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['data']['generated_count'], 2)
                self.assertEqual(response['Cache-Control'], 'no-store')
                scope.assert_called_once()
                self.assertEqual(scope.call_args.args[1], 7)
                trigger.assert_called_once_with(7)
            else:
                self.assertTrue(response.status_code in (401, 403) or response.data.get('code') != 200)
                scope.assert_not_called()
                trigger.assert_not_called()

    def test_endpoint_cannot_trigger_an_out_of_scope_group(self):
        view = ScheduledTaskGroupTriggerViews.as_view({'get': 'trigger'})
        request = APIRequestFactory().get('/api/system/tasks/groups/trigger', {'id': 7})
        force_authenticate(request, user=SimpleNamespace(user_obj=SimpleNamespace(id=42)))
        with (
            patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False),
            patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'timing.tasks:change'}),
            patch('src.apps.task_center.api.views.task_group.ScheduledTaskGroup.objects') as groups,
            patch.object(ProjectProductScopeService, 'has_project_product', return_value=False) as scope,
            patch.object(ScheduledTaskGroupExecutionService, 'trigger_manual') as trigger,
        ):
            groups.filter.return_value.first.return_value = SimpleNamespace(project_product_id=99)
            response = view(request)
        scope.assert_called_once()
        self.assertEqual(scope.call_args.args[1], 99)
        self.assertNotEqual(response.data['code'], 200)
        trigger.assert_not_called()

    def test_head_and_post_do_not_trigger_execution(self):
        view = ScheduledTaskGroupTriggerViews.as_view({'get': 'trigger'})
        for method in ('head', 'post'):
            request = getattr(APIRequestFactory(), method)('/api/system/tasks/groups/trigger?id=7')
            force_authenticate(request, user=SimpleNamespace(user_obj=SimpleNamespace(id=42)))
            with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True), \
                    patch.object(ScheduledTaskGroupExecutionService, 'trigger_manual') as trigger:
                response = view(request)
            self.assertEqual(response.status_code, 405)
            trigger.assert_not_called()

    def test_invalid_query_id_does_not_trigger_execution(self):
        view = ScheduledTaskGroupTriggerViews.as_view({'get': 'trigger'})
        for params in ({}, {'id': 'invalid'}):
            request = APIRequestFactory().get('/api/system/tasks/groups/trigger', params)
            force_authenticate(request, user=SimpleNamespace(user_obj=SimpleNamespace(id=42)))
            with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True), \
                    patch.object(ScheduledTaskGroupExecutionService, 'trigger_manual') as trigger:
                response = view(request)
            self.assertEqual(response.data['code'], 39018)
            trigger.assert_not_called()

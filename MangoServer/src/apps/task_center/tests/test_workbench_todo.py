from contextlib import contextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from django.db import OperationalError
from django.test import SimpleTestCase
from django.utils import timezone

from src.apps.auto_api.enums import ApiAuthRefreshModeEnum
from src.apps.auto_api.models import ApiCaseRelease
from src.apps.auto_ui.enums import UiAuthRefreshModeEnum
from src.apps.data_factory.enums import DataFactoryCleanupStatusEnum
from src.apps.task_center.enums import (
    WorkbenchTodoEventTypeEnum,
    WorkbenchTodoSeverityEnum,
    WorkbenchTodoSourceTypeEnum,
    WorkbenchTodoStatusEnum,
)
from src.apps.task_center.models import WorkbenchTodo
from src.apps.task_center.services.workbench.todo import WorkbenchTodoService
from src.apps.user.services.credential import UserCredentialService


class WorkbenchTodoServiceTests(SimpleTestCase):
    def setUp(self):
        patcher = patch('src.apps.system.services.system_config.SystemConfigService.get_environment_display_names',
                        return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def auth_config(expires_at, refresh_mode=0):
        return SimpleNamespace(
            id=17,
            name='生产授权',
            project_product_id=23,
            test_env=0,
            refresh_mode=refresh_mode,
            expire_notice_minutes=0,
            token_ttl=1440,
            expires_at=expires_at,
            last_refresh_time=None,
            last_refresh_error=None,
            update_time=timezone.now(),
        )

    def test_manual_auth_creates_warning_within_default_notice_window(self):
        config = self.auth_config(timezone.now() + timedelta(minutes=30))
        with patch.object(WorkbenchTodoService, '_upsert', return_value=object()) as upsert:
            result = WorkbenchTodoService._record_auth_expiry(
                config,
                WorkbenchTodoSourceTypeEnum.UI_AUTH.value,
                '前端授权',
                0,
            )

        self.assertIsNotNone(result)
        defaults = upsert.call_args.args[1]
        self.assertEqual(defaults['event_type'], WorkbenchTodoEventTypeEnum.AUTH_EXPIRING.value)
        self.assertEqual(defaults['severity'], WorkbenchTodoSeverityEnum.WARNING.value)

    def test_manual_auth_outside_default_notice_window_is_skipped(self):
        config = self.auth_config(timezone.now() + timedelta(days=2))
        with patch.object(WorkbenchTodoService, '_upsert') as upsert:
            result = WorkbenchTodoService._record_auth_expiry(
                config,
                WorkbenchTodoSourceTypeEnum.UI_AUTH.value,
                '前端授权',
                0,
            )

        self.assertIsNone(result)
        upsert.assert_not_called()

    def test_expired_auth_uses_danger_semantics(self):
        config = self.auth_config(timezone.now() - timedelta(minutes=5))
        with patch.object(WorkbenchTodoService, '_upsert', return_value=object()) as upsert:
            WorkbenchTodoService._record_auth_expiry(
                config,
                WorkbenchTodoSourceTypeEnum.UI_AUTH.value,
                '前端授权',
                0,
            )

        defaults = upsert.call_args.args[1]
        self.assertEqual(defaults['event_type'], WorkbenchTodoEventTypeEnum.AUTH_EXPIRED.value)
        self.assertEqual(defaults['severity'], WorkbenchTodoSeverityEnum.DANGER.value)
        self.assertIn('已于', defaults['summary'])

    def test_api_manual_auth_never_creates_expiry_todo(self):
        config = self.auth_config(
            timezone.now() - timedelta(days=1),
            refresh_mode=ApiAuthRefreshModeEnum.MANUAL.value,
        )
        config.last_refresh_time = timezone.now() - timedelta(hours=23, minutes=30)
        with patch.object(WorkbenchTodoService, '_upsert') as upsert:
            result = WorkbenchTodoService._record_auth_expiry(
                config,
                WorkbenchTodoSourceTypeEnum.API_AUTH.value,
                '服务授权',
                ApiAuthRefreshModeEnum.MANUAL.value,
            )

        self.assertIsNone(result)
        upsert.assert_not_called()

    def test_api_expire_notice_auth_still_creates_expiry_todo(self):
        config = self.auth_config(
            timezone.now() - timedelta(minutes=5),
            refresh_mode=ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
        )
        with patch.object(WorkbenchTodoService, '_upsert', return_value=object()) as upsert:
            result = WorkbenchTodoService._record_auth_expiry(
                config,
                WorkbenchTodoSourceTypeEnum.API_AUTH.value,
                '服务授权',
                ApiAuthRefreshModeEnum.MANUAL.value,
            )

        self.assertIsNotNone(result)
        defaults = upsert.call_args.args[1]
        self.assertEqual(defaults['event_type'], WorkbenchTodoEventTypeEnum.AUTH_EXPIRED.value)

    def test_owners_use_all_project_product_owners(self):
        first_owner = SimpleNamespace(id=3, name='负责人甲', username='owner-a')
        second_owner = SimpleNamespace(id=4, name='负责人乙', username='owner-b')
        todo = SimpleNamespace(project_product=SimpleNamespace(owners=[first_owner, second_owner]))

        self.assertEqual(
            WorkbenchTodoService._owner_payloads(todo),
            [
                {'id': 3, 'name': '负责人甲', 'username': 'owner-a'},
                {'id': 4, 'name': '负责人乙', 'username': 'owner-b'},
            ],
        )

    def test_unconfigured_product_has_no_owner(self):
        todo = SimpleNamespace(project_product=SimpleNamespace(owners=[]))

        self.assertEqual(
            WorkbenchTodoService._owner_payloads(todo),
            [],
        )

    def test_notify_owner_sends_email_to_each_email_owner(self):
        first_owner = SimpleNamespace(id=3, name='负责人甲', username='Owner@Example.com')
        second_owner = SimpleNamespace(id=4, name='负责人乙', username='owner-b@example.com')
        todo = SimpleNamespace(
            id=11,
            title='服务授权即将到期',
            summary='授权将在 30 分钟后到期，请提前更新。',
            project_product=SimpleNamespace(
                owners=[first_owner, second_owner],
                name='开放平台',
                project=SimpleNamespace(name='示例项目'),
            ),
        )

        with patch.object(
                WorkbenchTodoService,
                '_notification_url',
                return_value='https://example.com/#/index',
        ), patch.object(UserCredentialService, 'send_email') as send_email:
            result = WorkbenchTodoService._notify_owner(todo)

        self.assertTrue(result)
        self.assertEqual(send_email.call_count, 2)
        self.assertEqual(
            [call.kwargs['email'] for call in send_email.call_args_list],
            ['owner@example.com', 'owner-b@example.com'],
        )
        self.assertIn('服务授权即将到期', send_email.call_args.kwargs['subject'])
        self.assertIn('https://example.com/#/index', send_email.call_args.kwargs['content'])

    def test_notify_owner_skips_non_email_username(self):
        owner = SimpleNamespace(id=3, name='负责人甲', username='owner-a')
        todo = SimpleNamespace(
            project_product=SimpleNamespace(
                owners=[owner],
            ),
        )

        with patch.object(UserCredentialService, 'send_email') as send_email:
            result = WorkbenchTodoService._notify_owner(todo)

        self.assertFalse(result)
        send_email.assert_not_called()

    def test_ui_auth_risk_notifies_configured_notice_group_once(self):
        config = SimpleNamespace(
            id=17,
            refresh_mode=UiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
            notice_group_id=9,
            expire_notice_sent_at=None,
        )

        with patch(
                'src.apps.auto_ui.services.ui_auth.UiAuthManager.claim_expire_notice',
                return_value=True,
        ) as claim_notice, patch(
            'src.apps.task_center.services.workbench.todo.NoticeMain'
        ) as notice_main:
            result = WorkbenchTodoService._notify_auth_notice_group(
                config,
                WorkbenchTodoSourceTypeEnum.UI_AUTH.value,
                '前端授权即将到期：生产环境',
                '授权将在 30 分钟后到期，请提前更新。',
            )

        self.assertTrue(result)
        claim_notice.assert_called_once_with(17, ANY)
        notice_main.assert_called_once_with(9)
        notice_main.return_value.notice_monitoring.assert_called_once()

    def test_api_auth_risk_skips_notice_group_after_notice_was_sent(self):
        config = SimpleNamespace(
            id=18,
            refresh_mode=ApiAuthRefreshModeEnum.EXPIRE_NOTICE.value,
            notice_group_id=10,
            expire_notice_sent_at=timezone.now(),
        )

        with patch(
                'src.apps.auto_api.services.base.api_base_test_setup.auth_manager.'
                'ApiAuthManager.claim_expire_notice'
        ) as claim_notice, patch(
            'src.apps.task_center.services.workbench.todo.NoticeMain'
        ) as notice_main:
            result = WorkbenchTodoService._notify_auth_notice_group(
                config,
                WorkbenchTodoSourceTypeEnum.API_AUTH.value,
                '服务授权即将到期：生产环境',
                '授权将在 30 分钟后到期，请提前更新。',
            )

        self.assertFalse(result)
        claim_notice.assert_not_called()
        notice_main.assert_not_called()

    def test_upsert_notifies_owner_once_when_todo_is_created(self):
        todo = SimpleNamespace()
        with patch.object(
                WorkbenchTodo.objects,
                'get_or_create',
                return_value=(todo, True),
        ), patch.object(WorkbenchTodoService, '_notify_owner') as notify_owner:
            result = WorkbenchTodoService._upsert('new-risk-key', {'title': '新的风险'})

        self.assertIs(result, todo)
        notify_owner.assert_called_once_with(todo)

    def test_upsert_can_create_todo_without_email_notification(self):
        todo = SimpleNamespace()
        with patch.object(
                WorkbenchTodo.objects,
                'get_or_create',
                return_value=(todo, True),
        ), patch.object(WorkbenchTodoService, '_notify_owner') as notify_owner:
            result = WorkbenchTodoService._upsert(
                'silent-risk-key',
                {'title': '无需邮件的待办'},
                notify_owner=False,
            )

        self.assertIs(result, todo)
        notify_owner.assert_not_called()

    def test_upsert_does_not_notify_again_when_todo_is_already_pending(self):
        todo = SimpleNamespace(
            status=WorkbenchTodoStatusEnum.PENDING.value,
            handled_by=None,
            handled_by_id=None,
            handled_at=None,
            handle_note=None,
            save=Mock(),
        )
        with patch.object(
                WorkbenchTodo.objects,
                'get_or_create',
                return_value=(todo, False),
        ), patch.object(WorkbenchTodoService, '_notify_owner') as notify_owner:
            WorkbenchTodoService._upsert('existing-risk-key', {'title': '持续存在的风险'})

        notify_owner.assert_not_called()

    def test_upsert_reopens_automatically_resolved_risk(self):
        todo = SimpleNamespace(
            status=WorkbenchTodoStatusEnum.HANDLED.value,
            handled_by=None,
            handled_by_id=None,
            handled_at=timezone.now(),
            handle_note='已恢复',
            save=Mock(),
        )
        with patch.object(
                WorkbenchTodo.objects,
                'get_or_create',
                return_value=(todo, False),
        ), patch.object(WorkbenchTodoService, '_notify_owner') as notify_owner:
            WorkbenchTodoService._upsert('risk-key', {'title': '风险再次出现'})

        self.assertEqual(todo.status, WorkbenchTodoStatusEnum.PENDING.value)
        self.assertIsNone(todo.handled_by)
        self.assertIsNone(todo.handled_at)
        self.assertIsNone(todo.handle_note)
        notify_owner.assert_called_once_with(todo)

    def test_upsert_keeps_manually_handled_same_event_closed(self):
        todo = SimpleNamespace(
            status=WorkbenchTodoStatusEnum.HANDLED.value,
            handled_by_id=7,
            details={'difference_fingerprint': 'same'},
            save=Mock(),
        )
        with patch.object(
                WorkbenchTodo.objects,
                'get_or_create',
                return_value=(todo, False),
        ):
            result = WorkbenchTodoService._upsert(
                'risk-key',
                {'title': '同一结构风险', 'details': {'difference_fingerprint': 'same'}},
            )

        self.assertIs(result, todo)
        todo.save.assert_not_called()

    def test_upsert_reopens_manually_handled_event_when_schema_difference_changes(self):
        todo = SimpleNamespace(
            status=WorkbenchTodoStatusEnum.HANDLED.value,
            handled_by_id=7,
            handled_by=object(),
            handled_at=timezone.now(),
            handle_note='已确认',
            details={'difference_fingerprint': 'old'},
            save=Mock(),
        )
        defaults = {
            'title': '新的结构风险',
            'details': {'difference_fingerprint': 'new'},
        }
        with patch.object(
                WorkbenchTodo.objects,
                'get_or_create',
                return_value=(todo, False),
        ), patch.object(WorkbenchTodoService, '_notify_owner') as notify_owner:
            WorkbenchTodoService._upsert('risk-key', defaults)

        self.assertEqual(todo.status, WorkbenchTodoStatusEnum.PENDING.value)
        self.assertIsNone(todo.handled_by)
        self.assertEqual(todo.details['difference_fingerprint'], 'new')
        todo.save.assert_called_once()
        notify_owner.assert_called_once_with(todo)

    def test_configured_manual_events_can_be_marked_handled(self):
        review_todo = SimpleNamespace(
            status=WorkbenchTodoStatusEnum.PENDING.value,
            event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_REVIEW.value,
        )
        invalid_todo = SimpleNamespace(
            status=WorkbenchTodoStatusEnum.PENDING.value,
            event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_INVALID.value,
        )
        cleanup_todo = SimpleNamespace(
            status=WorkbenchTodoStatusEnum.PENDING.value,
            event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_FAILED.value,
        )
        cleanup_required_todo = SimpleNamespace(
            status=WorkbenchTodoStatusEnum.PENDING.value,
            event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_REQUIRED.value,
        )

        self.assertTrue(WorkbenchTodoService.can_mark_handled(review_todo))
        self.assertTrue(WorkbenchTodoService.can_mark_handled(cleanup_todo))
        self.assertFalse(WorkbenchTodoService.can_mark_handled(invalid_todo))
        self.assertFalse(WorkbenchTodoService.can_mark_handled(cleanup_required_todo))

    def test_record_cleanup_failure_includes_partial_result_and_errors(self):
        occurred_at = timezone.now()
        execution = SimpleNamespace(
            id=42,
            cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value,
            cleanup_time=occurred_at,
            update_time=occurred_at,
            execution_no='DF-20260826-42',
            project_product_id=8,
            module_id=9,
            template_id=11,
            template=SimpleNamespace(name='订单数据场景'),
            workbench_cleanup_items=[
                SimpleNamespace(
                    id=1,
                    alias='订单',
                    cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value,
                    cleanup_error=None,
                ),
                SimpleNamespace(
                    id=2,
                    alias='订单明细',
                    cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value,
                    cleanup_error='事务回滚',
                    cleanup_time=occurred_at,
                    database_id=21,
                    database=SimpleNamespace(
                        id=21,
                        display_name='订单测试库',
                        name='contract_test',
                    ),
                    datasource_binding=SimpleNamespace(environment=0),
                    template=SimpleNamespace(
                        entity=SimpleNamespace(table_name='contract_detail'),
                    ),
                ),
            ],
        )
        todo = SimpleNamespace(event_key='cleanup-risk')
        with patch.object(WorkbenchTodoService, '_upsert', return_value=todo) as upsert:
            result = WorkbenchTodoService.record_data_factory_cleanup_failure(execution)

        self.assertIs(result, todo)
        event_key, defaults = upsert.call_args.args
        self.assertIn('data-factory:execution:42:cleanup-failed:', event_key)
        self.assertEqual(
            defaults['event_type'],
            WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_FAILED.value,
        )
        self.assertEqual(defaults['details']['failed_count'], 1)
        self.assertEqual(defaults['details']['success_count'], 1)
        self.assertEqual(defaults['details']['errors'][0]['error'], '事务回滚')
        self.assertEqual(defaults['details']['errors'][0]['database_name'], '订单测试库')
        self.assertEqual(defaults['details']['errors'][0]['environment_name'], '测试环境')
        self.assertEqual(defaults['details']['errors'][0]['table_name'], 'contract_detail')

    def test_record_cleanup_failure_ignores_non_failed_execution(self):
        execution = SimpleNamespace(cleanup_status=DataFactoryCleanupStatusEnum.SUCCESS.value)

        with patch.object(WorkbenchTodoService, '_upsert') as upsert:
            result = WorkbenchTodoService.record_data_factory_cleanup_failure(execution)

        self.assertIsNone(result)
        upsert.assert_not_called()

    def test_reconcile_cleanup_only_records_failures_and_retires_manual_todos(self):
        from src.apps.data_factory.models import DataFactoryExecution

        execution = SimpleNamespace(id=43, cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value)
        executions = Mock()
        executions.filter.return_value.prefetch_related.return_value = [execution]
        stale_todos = Mock()
        stale_todos.exclude.return_value = stale_todos
        todo = SimpleNamespace(event_key='cleanup-failed')
        with (
            patch.object(DataFactoryExecution.objects, 'select_related', return_value=executions),
            patch.object(WorkbenchTodo.objects, 'filter', return_value=stale_todos) as todo_filter,
            patch.object(WorkbenchTodoService, 'record_data_factory_cleanup_failure', return_value=todo) as record,
            patch.object(WorkbenchTodoService, '_resolve_queryset', return_value=6) as resolve,
        ):
            result = WorkbenchTodoService.reconcile_data_factory_cleanup_todos()

        executions.filter.assert_called_once_with(cleanup_status=DataFactoryCleanupStatusEnum.FAIL.value)
        record.assert_called_once_with(execution)
        self.assertIn(
            WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_REQUIRED.value,
            todo_filter.call_args.kwargs['event_type__in'],
        )
        stale_todos.exclude.assert_called_once_with(event_key__in={'cleanup-failed'})
        resolve.assert_called_once_with(stale_todos, ANY)
        self.assertEqual(result['resolved_data_factory_cleanup_todo_count'], 6)
        self.assertEqual(result['data_factory_cleanup_todo_count'], 1)

    def test_visible_queryset_hides_existing_pending_manual_cleanup_todos(self):
        queryset = Mock()
        queryset.exclude.return_value.prefetch_related.return_value = queryset
        with (
            patch.object(WorkbenchTodo.objects, 'select_related', return_value=queryset),
            patch(
                'src.apps.task_center.services.workbench.todo.PermissionMenuService.'
                'is_effective_super_admin',
                return_value=True,
            ),
        ):
            result = WorkbenchTodoService.visible_queryset(SimpleNamespace(id=1))

        queryset.exclude.assert_called_once_with(
            event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_CLEANUP_REQUIRED.value,
            status=WorkbenchTodoStatusEnum.PENDING.value,
        )
        self.assertIs(result, queryset)

    def test_pending_manual_execution_does_not_create_failure_todo(self):
        execution = SimpleNamespace(cleanup_status=DataFactoryCleanupStatusEnum.PENDING_MANUAL.value)
        with patch.object(WorkbenchTodoService, '_upsert') as upsert:
            self.assertIsNone(WorkbenchTodoService.record_data_factory_cleanup_failure(execution))
        upsert.assert_not_called()

    def test_reconcile_prepublication_todos_aggregates_one_todo_per_product(self):
        occurred_at = timezone.now()
        release_queryset = Mock()
        values_queryset = Mock()
        release_queryset.values.return_value.order_by.return_value = values_queryset
        values_queryset.iterator.return_value = [
            {
                'api_case__project_product_id': 23,
                'api_case_id': 101,
                'api_case__name': '创建订单',
                'api_case__module_id': 31,
                'api_case__module__name': '订单管理',
                'revision_id': 501,
                'revision__revision_no': 2,
                'create_time': occurred_at,
            },
            {
                'api_case__project_product_id': 23,
                'api_case_id': 102,
                'api_case__name': '取消订单',
                'api_case__module_id': 31,
                'api_case__module__name': '订单管理',
                'revision_id': 502,
                'revision__revision_no': 1,
                'create_time': occurred_at,
            },
        ]
        stale_todos = Mock()

        with patch.object(
                ApiCaseRelease.objects,
                'filter',
                return_value=release_queryset,
        ), patch.object(
            WorkbenchTodo.objects,
            'filter',
            return_value=stale_todos,
        ), patch.object(
            WorkbenchTodoService,
            '_upsert',
        ) as upsert, patch.object(
            WorkbenchTodoService,
            '_resolve_queryset',
            return_value=0,
        ):
            result = WorkbenchTodoService.reconcile_api_case_prepublication_todos()

        upsert.assert_called_once()
        event_key, defaults = upsert.call_args.args
        self.assertEqual(event_key, 'api-case:prepublication:product:23')
        self.assertEqual(defaults['source_id'], 23)
        self.assertEqual(defaults['details']['prepublication_count'], 2)
        self.assertIn('当前有 2 个', defaults['summary'])
        self.assertFalse(upsert.call_args.kwargs['notify_owner'])
        stale_todos.exclude.assert_called_once_with(event_key__in={event_key})
        self.assertEqual(result['api_case_prepublication_todo_count'], 1)

    def test_reconcile_prepublication_todos_closes_product_todo_when_empty(self):
        release_queryset = Mock()
        values_queryset = Mock()
        release_queryset.filter.return_value = release_queryset
        release_queryset.values.return_value.order_by.return_value = values_queryset
        values_queryset.iterator.return_value = []
        stale_todos = Mock()
        scoped_stale_todos = stale_todos.filter.return_value

        with patch.object(
                ApiCaseRelease.objects,
                'filter',
                return_value=release_queryset,
        ), patch.object(
            WorkbenchTodo.objects,
            'filter',
            return_value=stale_todos,
        ), patch.object(
            WorkbenchTodoService,
            '_upsert',
        ) as upsert, patch.object(
            WorkbenchTodoService,
            '_resolve_queryset',
            return_value=1,
        ) as resolve:
            result = WorkbenchTodoService.reconcile_api_case_prepublication_todos(
                project_product_ids={23},
            )

        upsert.assert_not_called()
        release_queryset.filter.assert_called_once_with(
            api_case__project_product_id__in={23},
        )
        stale_todos.filter.assert_called_once_with(source_id__in={23})
        resolve.assert_called_once_with(scoped_stale_todos, ANY)
        self.assertEqual(result['resolved_api_case_prepublication_todo_count'], 1)

    def test_mark_schema_review_handled_records_user(self):
        todo = SimpleNamespace(
            id=31,
            status=WorkbenchTodoStatusEnum.PENDING.value,
            event_type=WorkbenchTodoEventTypeEnum.DATA_FACTORY_SCHEMA_REVIEW.value,
            handled_by=None,
            handled_at=None,
            handle_note=None,
            details={'differences': [{'field': 'contract_id', 'change': 'type'}]},
        )
        user = SimpleNamespace(id=9)
        queryset = Mock()
        queryset.update.return_value = 1
        with patch.object(WorkbenchTodo.objects, 'filter', return_value=queryset) as query:
            result = WorkbenchTodoService.mark_handled(todo, user, '已核对结构变化')

        self.assertTrue(result)
        query.assert_called_once_with(
            id=31,
            status=WorkbenchTodoStatusEnum.PENDING.value,
            event_type__in=WorkbenchTodoService.MANUAL_HANDLING_EVENT_TYPES,
        )
        self.assertEqual(todo.status, WorkbenchTodoStatusEnum.HANDLED.value)
        self.assertIs(todo.handled_by, user)
        self.assertEqual(todo.handle_note, '已核对结构变化')
        self.assertTrue(todo.details['difference_fingerprint'])

    def test_resolve_queryset_marks_risk_handled_by_system(self):
        queryset = Mock()
        pending_queryset = queryset.filter.return_value
        pending_queryset.update.return_value = 2

        resolved_count = WorkbenchTodoService._resolve_queryset(queryset, '系统自动检测：已恢复。')

        self.assertEqual(resolved_count, 2)
        pending_queryset.update.assert_called_once()
        update_values = pending_queryset.update.call_args.kwargs
        self.assertEqual(update_values['status'], WorkbenchTodoStatusEnum.HANDLED.value)
        self.assertIsNone(update_values['handled_by'])
        self.assertEqual(update_values['handle_note'], '系统自动检测：已恢复。')

    @patch('src.apps.task_center.services.workbench.todo.time.sleep')
    @patch('src.apps.task_center.services.workbench.todo.random.uniform', return_value=0)
    def test_resolve_queryset_retries_mysql_deadlock(self, _uniform, sleep):
        queryset = Mock()
        pending_queryset = queryset.filter.return_value
        pending_queryset.update.side_effect = [
            OperationalError(1213, 'Deadlock found when trying to get lock'),
            2,
        ]

        resolved_count = WorkbenchTodoService._resolve_queryset(queryset, '系统自动检测：已恢复。')

        self.assertEqual(resolved_count, 2)
        self.assertEqual(pending_queryset.update.call_count, 2)
        sleep.assert_called_once_with(WorkbenchTodoService.DEADLOCK_BASE_DELAY_SECONDS)

    def test_resolve_queryset_does_not_retry_other_database_errors(self):
        queryset = Mock()
        pending_queryset = queryset.filter.return_value
        pending_queryset.update.side_effect = OperationalError(2013, 'Lost connection')

        with self.assertRaises(OperationalError):
            WorkbenchTodoService._resolve_queryset(queryset, '系统自动检测：已恢复。')

        pending_queryset.update.assert_called_once()

    def test_reconcile_todos_skips_when_another_process_holds_lock(self):
        @contextmanager
        def unavailable_lock():
            yield False

        with patch.object(
                WorkbenchTodoService,
                '_reconcile_lock',
                side_effect=unavailable_lock,
        ), patch.object(WorkbenchTodoService, 'reconcile_auth_todos') as reconcile_auth:
            result = WorkbenchTodoService.reconcile_todos()

        self.assertEqual(result, {'reconciliation_skipped': True})
        reconcile_auth.assert_not_called()

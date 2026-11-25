"""Case 附属清理台账删除；仅使用隔离内存库，不运行被测清理。"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import models
from django.db.models.deletion import ProtectedError, get_candidate_relations_to_delete
from django.test import SimpleTestCase
from django.http import QueryDict
from django.utils import timezone

from src.apps.auto_api.enums.resource_cleanup import ApiResourceCleanupStatus as State
from src.apps.auto_api.enums.callback import CallbackRunStatus
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiCase, ApiCaseExecutionResource, ApiCaseExecutionTrace
from src.apps.auto_api.models import ApiCaseCallbackRun, ApiMockConfig, ApiMockRequestLog
from src.apps.auto_api.selectors.resource_cleanup import ApiResourceCleanupSelector
from src.apps.auto_api.services.api_case.mutation_io import ApiCaseMutationService
from src.apps.auto_api.tests import test_case_list_execution as fixtures
from src.apps.task_center.models import TasksDetails
from src.common.responses.model_crud import ModelCRUD


class CaseResourceDeletionTests(SimpleTestCase):
    restore_connection = fixtures.CaseListExecutionQueryTests.restore_connection
    publish = fixtures.CaseListExecutionQueryTests.publish
    report_detail = fixtures.CaseListExecutionQueryTests.report_detail
    trace = fixtures.CaseListExecutionQueryTests.trace

    def setUp(self):
        fixtures.CaseListExecutionQueryTests.setUp(self)
        self.memory.connection.create_collation('utf8mb4_bin', lambda a, b: (a > b) - (a < b))
        with self.memory.schema_editor() as editor:
            for model in (TasksDetails, ApiCaseExecutionResource, ApiMockConfig, ApiCaseCallbackRun, ApiMockRequestLog):
                editor.create_model(model)
        self.memory.disable_constraint_checking()
        tables = set(self.memory.introspection.table_names())
        # 不创建无关 App 表，Collector 仍使用真实外键规则处理夹具中的所有关联。
        relation_patch = patch('django.db.models.deletion.get_candidate_relations_to_delete',
            side_effect=lambda opts: [relation for relation in get_candidate_relations_to_delete(opts)
                if relation.related_model._meta.db_table in tables])
        relation_patch.start()
        self.addCleanup(relation_patch.stop)
        self.execution = self.trace(self.revision.id)

    def callback(self, status=CallbackRunStatus.PASSED, finished=True):
        suffix = str(ApiCaseCallbackRun.objects.count())
        mock = ApiMockConfig.objects.create(project_product=self.product, name='回调Mock',
            mock_key='mock' + suffix, method=1, path='/callback')
        run = ApiCaseCallbackRun.objects.create(case=self.case, trace=self.execution, mock_config=mock,
            execution_key='execution' + suffix, rule_key='callback' + suffix, test_env=0,
            dependency_digest='digest', correlation_value=suffix, correlation_key='key' + suffix,
            deadline=timezone.now(), status=status.value, finished_at=timezone.now() if finished else None)
        log = ApiMockRequestLog.objects.create(mock_config=mock, callback_run=run,
            trace_id='delivery' + suffix, method=1, request_path='/callback')
        return mock, run, log

    def resource(self, status=State.CLEANED.value):
        return ApiCaseExecutionResource.objects.create(case=self.case, trace=self.execution,
            step_id=1, parameter_id=2, test_env=0, rule_key=str(ApiCaseExecutionResource.objects.count()),
            rule={}, proof={}, status=status)

    def test_delete_case_removes_cleaned_ledger_and_preserves_trace_and_report(self):
        self.publish()
        detail = self.report_detail(status=0)
        resource = self.resource()
        case_id = self.case.id
        self.case.delete()
        self.assertFalse(ApiCase.objects.filter(id=case_id).exists())
        self.assertFalse(ApiCaseExecutionResource.objects.filter(id=resource.id).exists())
        self.assertTrue(ApiCaseExecutionTrace.objects.filter(id=self.execution.id).exists())
        detail.refresh_from_db()
        self.assertEqual(detail.case_id, case_id)
        self.assertIsNone(detail.api_case_revision_id)

    def test_all_unfinished_states_keep_case_and_cleaned_records(self):
        cleaned = self.resource()
        pending = self.resource()
        for status in State:
            if status == State.CLEANED:
                continue
            pending.status = status.value
            pending.save(update_fields=['status'])
            with self.subTest(status=status.value), self.assertRaises(AutoApiError) as caught:
                self.case.delete()
            self.assertIn('暂不能删除用例', caught.exception.msg)
            self.assertTrue(ApiCase.objects.filter(id=self.case.id).exists())
            self.assertTrue(ApiCaseExecutionResource.objects.filter(id=cleaned.id).exists())
            self.assertTrue(ApiCaseExecutionResource.objects.filter(id=pending.id).exists())

    def test_later_delete_failure_rolls_back_ledger_and_report_detachment(self):
        detail = self.report_detail(status=0)
        resource = self.resource()
        with patch.object(models.Model, 'delete', side_effect=ProtectedError('blocked elsewhere', set())):
            with self.assertRaises(ProtectedError):
                self.case.delete()
        self.assertTrue(ApiCaseExecutionResource.objects.filter(id=resource.id).exists())
        detail.refresh_from_db()
        self.assertEqual(detail.api_case_revision_id, self.revision.id)

    def test_mutation_entry_uses_same_deletion_rule(self):
        resource = self.resource()
        ApiCaseMutationService.delete(self.case.id)
        self.assertFalse(ApiCaseExecutionResource.objects.filter(id=resource.id).exists())

    def test_deletion_does_not_touch_another_case_ledger(self):
        other = ApiCase.objects.create(project_product=self.product, module=self.case.module,
            case_people=self.case.case_people, name='另一个Case')
        resource = self.resource()
        ApiCaseExecutionResource.objects.filter(id=resource.id).update(case=other)
        self.case.delete()
        self.assertTrue(ApiCaseExecutionResource.objects.filter(id=resource.id, case=other).exists())

    def test_batch_delete_rolls_back_first_case_when_second_has_unfinished_resources(self):
        first_id = self.case.id
        cleaned = self.resource()
        other = ApiCase.objects.create(project_product=self.product, module=self.case.module,
            case_people=self.case.case_people, name='清理尚未完成')
        pending = self.resource(State.FAILED.value)
        ApiCaseExecutionResource.objects.filter(id=pending.id).update(case=other)
        crud = ModelCRUD()
        crud.model = ApiCase
        crud.has_instance_data_scope_permission = Mock(return_value=True)
        crud.capture_config_snapshot = Mock(return_value=SimpleNamespace(snapshot={}))
        crud.record_config_delete = Mock()
        response = crud.delete(SimpleNamespace(query_params=QueryDict(f'id[]={first_id}&id[]={other.id}')))
        self.assertEqual(response.data['code'], 31233)
        self.assertTrue(ApiCase.objects.filter(id=first_id).exists())
        self.assertTrue(ApiCaseExecutionResource.objects.filter(id=cleaned.id).exists())
        self.assertTrue(ApiCaseExecutionResource.objects.filter(id=pending.id).exists())

    def test_delete_preview_includes_cleaned_ledger_and_unfinished_blocker(self):
        from src.interfaces.mcp.tools.api.helper_parts.impact import _api_case_delete_impact
        self.resource()
        preview = _api_case_delete_impact(self.case.id)
        self.assertTrue(preview['can_delete'])
        self.assertEqual(preview['will_delete']['cleaned_resource_records'], 1)
        self.resource(State.FAILED.value)
        preview = _api_case_delete_impact(self.case.id)
        self.assertFalse(preview['can_delete'])
        self.assertEqual(preview['references']['unfinished_resource_record_count'], 1)
        self.assertTrue(any('尚未清理并验证' in value for value in preview['blockers']))

    def test_case_deletion_cascades_all_completed_callback_statuses_and_deliveries(self):
        for status in (CallbackRunStatus.PASSED, CallbackRunStatus.FAILED,
                       CallbackRunStatus.TIMEOUT, CallbackRunStatus.CANCELLED):
            self.callback(status)
        self.case.delete()
        self.assertEqual(ApiCaseCallbackRun.objects.count(), 0)
        self.assertEqual(ApiMockRequestLog.objects.count(), 0)
        self.assertEqual(ApiMockConfig.objects.count(), 4)
        self.assertTrue(ApiCaseExecutionTrace.objects.filter(id=self.execution.id).exists())

    def test_waiting_and_incomplete_callback_evidence_prevent_case_deletion(self):
        cleaned = self.resource()
        _, run, log = self.callback(CallbackRunStatus.WAITING, finished=False)
        for status, finished, active in ((CallbackRunStatus.WAITING.value, None, None),
                (CallbackRunStatus.PASSED.value, None, None),
                (CallbackRunStatus.PASSED.value, timezone.now(), 'still-active')):
            ApiCaseCallbackRun.objects.filter(id=run.id).update(status=status, finished_at=finished, active_key=active)
            with self.subTest(status=status, active=active), self.assertRaises(AutoApiError) as caught:
                self.case.delete()
            self.assertEqual(caught.exception.code, 31238)
            self.assertTrue(ApiCaseExecutionResource.objects.filter(id=cleaned.id).exists())
            self.assertTrue(ApiMockRequestLog.objects.filter(id=log.id).exists())

    def test_mock_deletion_cascades_completed_callbacks_but_preserves_case_and_trace(self):
        mock, run, log = self.callback()
        mock.delete()
        self.assertFalse(ApiCaseCallbackRun.objects.filter(id=run.id).exists())
        self.assertFalse(ApiMockRequestLog.objects.filter(id=log.id).exists())
        self.assertTrue(ApiCase.objects.filter(id=self.case.id).exists())
        self.assertTrue(ApiCaseExecutionTrace.objects.filter(id=self.execution.id).exists())

    def test_waiting_callback_prevents_mock_and_delivery_deletion(self):
        mock, run, log = self.callback(CallbackRunStatus.WAITING, finished=False)
        with self.assertRaises(AutoApiError) as caught:
            mock.delete()
        self.assertEqual(caught.exception.code, 31238)
        self.assertTrue(ApiMockConfig.objects.filter(id=mock.id).exists())
        self.assertTrue(ApiMockRequestLog.objects.filter(id=log.id).exists())

    def test_mock_failure_rolls_back_completed_callback_and_delivery_deletion(self):
        mock, run, log = self.callback()
        with patch.object(models.Model, 'delete', side_effect=ProtectedError('other blocker', set())):
            with self.assertRaises(ProtectedError):
                mock.delete()
        self.assertTrue(ApiCaseCallbackRun.objects.filter(id=run.id).exists())
        self.assertTrue(ApiMockRequestLog.objects.filter(id=log.id).exists())

    def test_preview_includes_completed_callbacks_and_waiting_blocker(self):
        from src.interfaces.mcp.tools.api.helper_parts.impact import _api_case_delete_impact
        self.callback()
        preview = _api_case_delete_impact(self.case.id)
        self.assertTrue(preview['can_delete'])
        self.assertEqual(preview['will_delete']['completed_callback_records'], 1)
        self.callback(CallbackRunStatus.WAITING, finished=False)
        preview = _api_case_delete_impact(self.case.id)
        self.assertFalse(preview['can_delete'])
        self.assertEqual(preview['references']['unfinished_callback_record_count'], 1)

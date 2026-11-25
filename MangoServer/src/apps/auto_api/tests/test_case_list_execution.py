from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_api.models import ApiCase, ApiCaseRelease, ApiCaseRevision, ApiCaseExecutionTrace, ApiHeaders
from src.apps.auto_api.selectors.case_list_execution import ApiCaseListExecutionSelector as Selector
from src.apps.auto_api.services.execution.cases.list_execution import ApiCaseListExecutionService as Service
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.test_center.models import Project, ProjectProduct, ProductModule, TestSuite, TestSuiteDetails, ExecutionResult
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.user.models import User


class CaseListExecutionQueryTests(SimpleTestCase):
    """只使用独立内存数据库，不生成迁移、不连接业务库。"""
    def setUp(self):
        from src.apps.auto_api import models as api_models
        from src.apps.data_factory.models import DataFactoryCaseConfig
        self.original_connection = connections['default']
        self.memory = DatabaseWrapper({'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:',
            'TIME_ZONE': None, 'CONN_HEALTH_CHECKS': False, 'CONN_MAX_AGE': 0, 'OPTIONS': {},
            'AUTOCOMMIT': True}, alias='case-list-only-memory')
        connections['case-list-only-memory'] = self.memory
        self.cache_override = override_settings(CACHES={'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
        self.cache_override.enable()
        self.addCleanup(self.cache_override.disable)
        self.addCleanup(self.restore_connection)
        with self.memory.schema_editor() as editor:
            for model in (User, Project, ProjectProduct, ProductModule, ApiCase,
                api_models.ApiCaseDetailed, api_models.ApiCaseDetailedParameter, ApiCaseRevision,
                ApiCaseExecutionTrace, ApiCaseRelease, ApiHeaders, api_models.ApiInfo,
                api_models.ApiInfoHttpConfig, api_models.ApiInfoGrpcConfig,
                api_models.ApiInfoMcpConfig, api_models.ApiInfoWebSocketConfig,
                DataFactoryCaseConfig, TestSuite, TestSuiteDetails, ExecutionResult):
                editor.create_model(model)
        self.memory.disable_constraint_checking()
        connections['default'] = self.memory
        project = Project.objects.create(name='列表执行项目')
        self.product = ProjectProduct.objects.create(project=project, name='列表执行产品')
        module = ProductModule.objects.create(project_product=self.product, name='列表模块')
        user = User.objects.create(name='测试用户', username='list_execution', password='unused')
        self.case = ApiCase.objects.create(project_product=self.product, module=module, case_people=user,
                                           name='版本隔离用例', status=TaskEnum.FAIL.value)
        self.revision = ApiCaseRevision.objects.create(api_case=self.case, revision_no=1, payload={}, checksum='frozen')

    def restore_connection(self):
        connections['default'] = self.original_connection
        del connections['case-list-only-memory']
        self.memory.close()

    def trace(self, revision=None, *, env=0, status=1, started=None, **summary):
        import uuid
        return ApiCaseExecutionTrace.objects.create(case_id=self.case.id, test_env=env,
            trace_id=uuid.uuid4().hex, source_type=4, status=status, started_at=started or timezone.now(),
            summary={'case_revision_id': revision, **summary})

    def row(self, env=0):
        row = Selector.annotate(ApiCase.objects.filter(pk=self.case.pk), env).get()
        self.assertEqual(Selector.collect([self.case.id], env)[self.case.id], Selector.presentation(row, env))
        return row

    def publish(self):
        return ApiCaseRelease.objects.create(api_case=self.case, revision=self.revision,
                                             version_no=1, version_label='V1', status='published')

    def test_published_result_ignores_editing_and_other_environment(self):
        self.publish()
        passed = self.trace(self.revision.id)
        self.trace(self.revision.id, status=0, execution_source='editing')
        self.trace(self.revision.id, env=1, status=0)
        row = self.row()
        self.assertEqual(row.list_status, 1)
        self.assertEqual(row.list_trace_id, passed.trace_id)
        self.assertEqual(self.row(1).list_status, 0)
        self.assertIsNone(self.row(2).list_status)

    def test_hover_queries_each_existing_version_in_selected_environment(self):
        from src.apps.auto_api.selectors.case_configuration import ApiCaseConfigurationSelector
        self.publish()
        candidate = ApiCaseRevision.objects.create(api_case=self.case, revision_no=2, payload={}, checksum='new')
        ApiCaseRelease.objects.create(api_case=self.case, revision=candidate, status='prepublished',
                                     is_current=False, version_no=2, version_label='r2')
        fingerprint = Selector.editing_fingerprints([self.case.id])[self.case.id]
        self.trace(editing_fingerprint=fingerprint, execution_source='editing', status=0)
        self.trace(candidate.id, status=3)
        self.trace(self.revision.id, status=1)
        self.trace(candidate.id, env=1, status=0)
        with patch.object(ApiCaseConfigurationSelector, 'scoped_cases', return_value=ApiCase.objects.all()):
            rows = Selector.version_results(self.case.id, 0, user=object())
            self.assertEqual([row['publication_status'] for row in rows], ['unpublished', 'prepublished', 'published'])
            self.assertEqual([row['status'] for row in rows], [0, None, 1])
            self.assertEqual([row['label'] for row in rows], ['未发布（编辑态）', '预发布 r2', '已发布 V1'])
            empty = Selector.version_results(self.case.id, 2, user=object())
            self.assertTrue(all(row['status'] is None for row in empty))

    def test_hover_omits_absent_releases_and_honors_product_scope(self):
        from src.apps.auto_api.selectors.case_configuration import ApiCaseConfigurationSelector
        from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
        user = SimpleNamespace(id=123)
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
             patch.object(ProjectProductScopeService, 'can_view_all_project_data', return_value=False), \
             patch.object(ProjectProductScopeService, 'project_product_ids_for_user', return_value={self.product.id}):
            rows = Selector.version_results(self.case.id, 0, user=user)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['publication_status'], 'unpublished')
            self.assertIsNone(Selector.version_results(self.case.id, 0, user=None))
            with patch.object(ProjectProductScopeService, 'project_product_ids_for_user', return_value=set()):
                self.assertIsNone(Selector.version_results(self.case.id, 0, user=user))

    def test_candidate_uses_exact_revision_not_old_publication(self):
        old = self.publish()
        old.is_current = False
        old.save(update_fields=['is_current'])
        revision = ApiCaseRevision.objects.create(api_case=self.case, revision_no=2, payload={}, checksum='candidate')
        ApiCaseRelease.objects.create(api_case=self.case, revision=revision,
                                     version_no=2, version_label='r2', status='prepublished')
        self.trace(self.revision.id)
        self.assertEqual(self.row().list_version, 'prepublished')
        self.assertIsNone(self.row().list_status)
        self.trace(revision.id, status=0)
        self.assertEqual(self.row().list_status, 0)

    def test_running_trace_keeps_previous_completed_result(self):
        self.publish()
        old = self.trace(self.revision.id, status=1, started=timezone.now() - timedelta(minutes=5))
        newest = self.trace(self.revision.id, status=3)
        old.finished_at = timezone.now()
        old.save()
        self.assertEqual(self.row().list_trace_id, old.trace_id)
        self.assertEqual(self.row().list_status, 1)
        self.assertTrue(self.row().list_active)
        newest.status = TaskEnum.FAIL.value
        newest.save(update_fields=['status'])
        self.assertEqual(self.row().list_trace_id, newest.trace_id)
        self.assertEqual(self.row().list_status, 0)

    def test_editing_result_survives_configuration_and_runtime_changes(self):
        fingerprint = Selector.editing_fingerprints([self.case.id])[self.case.id]
        self.trace(editing_fingerprint=fingerprint, execution_source='editing')
        self.assertEqual(self.row().list_status, 1)
        ApiCase.objects.filter(pk=self.case.id).update(status=3)
        self.assertEqual(self.row().list_status, 1)
        ApiCase.objects.filter(pk=self.case.id).update(front_custom=[{'code': 'changed'}])
        self.assertEqual(self.row().list_status, 1)
        self.assertEqual(Selector.presentation(self.row(), 0)['state'], 'executed')
        self.assertEqual(Selector.filter_results(Selector.annotate(ApiCase.objects.all(), 0), ['2']).count(), 0)

    def test_headers_do_not_change_editing_result(self):
        header = ApiHeaders.objects.create(project_product=self.product, key='X-Test', value='1', status=1)
        fingerprint = Selector.editing_fingerprints([self.case.id])[self.case.id]
        self.trace(editing_fingerprint=fingerprint)
        self.assertEqual(self.row().list_status, 1)
        header.status = 0
        header.save()
        self.assertEqual(self.row().list_status, 1)
        ApiHeaders.objects.create(project_product=self.product, key='X-Unrelated', value='other', status=0)
        self.assertEqual(self.row().list_status, 1)

    def test_result_filter_before_pagination_and_empty_state(self):
        self.publish()
        self.trace(self.revision.id, status=0)
        queryset = Selector.annotate(ApiCase.objects.all(), 0)
        self.assertEqual(Selector.filter_results(queryset, ['0']).count(), 1)
        self.assertEqual(Selector.filter_results(queryset, ['1']).count(), 0)
        self.assertEqual(Selector.filter_results(queryset, ['2']).count(), 0)
        self.assertEqual(Selector.filter_results(queryset, ['not_run']).count(), 0)
        self.assertEqual(Selector.filter_results(Selector.annotate(ApiCase.objects.all(), 1), ['not_run']).count(), 1)
        self.assertEqual(Selector.filter_results(Selector.annotate(ApiCase.objects.all(), 1), ['2']).count(), 1)

    def test_debug_or_partial_runs_never_replace_complete_result(self):
        self.publish()
        whole = self.trace(self.revision.id)
        self.trace(self.revision.id, status=0, partial_execution=True)
        debug = self.trace(self.revision.id, status=0)
        debug.source_type = 5
        debug.save()
        self.assertEqual(self.row().list_trace_id, whole.trace_id)

    def report_detail(self, *, status=6):
        suite = TestSuite.objects.create(id=100, project_product=self.product, user=self.case.case_people,
                                         test_env=0, status=status, is_notice=0)
        return TestSuiteDetails.objects.create(test_suite=suite, project_product=self.product,
            type=TestCaseTypeEnum.API.value, case_id=self.case.id, test_env=0, status=status, retry=1,
            api_case_revision=self.revision, summary_data={'meta': {
                'dispatch_started_at': (timezone.now() - timedelta(minutes=2)).isoformat()}})

    def test_report_blocked_status_overrides_stale_running_trace(self):
        self.publish()
        detail = self.report_detail()
        trace = self.trace(self.revision.id, status=3)
        trace.test_suite_detail_id = detail.id
        trace.test_suite_id = detail.test_suite_id
        trace.save()
        row = self.row()
        self.assertEqual(row.list_status, 0)
        self.assertFalse(row.list_active)

    def test_retry_of_report_detail_does_not_pollute_previous_trace(self):
        self.publish()
        detail = self.report_detail(status=3)
        trace = self.trace(self.revision.id, status=0)
        trace.test_suite_detail_id = detail.id
        trace.test_suite_id = detail.test_suite_id
        trace.save()
        detail.summary_data['meta']['dispatch_started_at'] = (timezone.now() + timedelta(minutes=1)).isoformat()
        detail.save()
        self.assertEqual(self.row().list_status, 0)

    def test_warning_comes_from_exact_execution_record_not_trace_failure_flag(self):
        self.publish()
        trace = self.trace(self.revision.id, status=0)
        ExecutionResult.objects.create(source_type='page', target_type='api_case', target_id=self.case.id,
                                       trace_id=trace.trace_id, revision_id=self.revision.id, test_env=0, status=4)
        self.assertEqual(self.row().list_status, 4)

    def test_cross_environment_results_choose_latest_matching_version_and_report_actual_environment(self):
        self.publish()
        self.trace(self.revision.id, env=0, started=timezone.now() - timedelta(minutes=2))
        latest = self.trace(self.revision.id, env=1, status=0)
        row = self.row(None)
        self.assertEqual(row.list_trace_id, latest.trace_id)
        self.assertEqual(row.list_status, 0)
        self.assertEqual(Selector.presentation(row, None)['test_env'], 1)
        self.assertEqual(self.row(0).list_status, 1)
        self.assertEqual(Selector.filter_results(Selector.annotate(ApiCase.objects.all(), None), ['0']).count(), 1)
        with patch('src.apps.auto_api.selectors.case_configuration.ApiCaseConfigurationSelector.scoped_cases',
                   return_value=ApiCase.objects.all()):
            results = Selector.version_results(self.case.id, None, user=object())
            published = [item for item in results if item['publication_status'] == 'published']
            self.assertEqual([(item['status'], item['test_env']) for item in published], [(1, 0), (0, 1)])

    def test_hover_latest_per_environment_and_version_without_fallback(self):
        self.publish()
        self.trace(self.revision.id, env=0, status=0, started=timezone.now() - timedelta(minutes=5))
        latest = self.trace(self.revision.id, env=0, status=1)
        other = self.trace(self.revision.id, env=1, status=4)
        self.trace(status=0, env=0, execution_source='editing', editing_fingerprint='old-configuration')
        with patch('src.apps.auto_api.selectors.case_configuration.ApiCaseConfigurationSelector.scoped_cases',
                   return_value=ApiCase.objects.all()):
            rows = Selector.version_results(self.case.id, None, user=object())
        published = [row for row in rows if row['publication_status'] == 'published']
        self.assertEqual([row['trace_id'] for row in published], [latest.trace_id, other.trace_id])
        editing = [row for row in rows if row['publication_status'] == 'unpublished']
        self.assertEqual([(row['status'], row['test_env']) for row in editing], [(0, 0)])

    def test_hover_does_not_present_pending_and_running_as_results(self):
        self.publish()
        active = self.trace(self.revision.id, env=1, status=3)
        self.report_detail(status=2)
        with patch('src.apps.auto_api.selectors.case_configuration.ApiCaseConfigurationSelector.scoped_cases',
                   return_value=ApiCase.objects.all()):
            rows = Selector.version_results(self.case.id, None, user=object())
        published = [row for row in rows if row['publication_status'] == 'published']
        self.assertEqual([(row['test_env'], row['status']) for row in published], [(None, None)])
        self.assertTrue(published[0]['is_active'])

    def test_queued_frozen_revision_keeps_previous_pass_and_duplicate_guard(self):
        self.publish()
        passed = self.trace(self.revision.id, started=timezone.now() - timedelta(minutes=3))
        self.report_detail(status=TaskEnum.STAY_BEGIN.value)
        row = self.row()
        self.assertEqual(row.list_status, TaskEnum.SUCCESS.value)
        self.assertEqual(row.list_trace_id, passed.trace_id)
        self.assertTrue(row.list_active)
        queryset = Selector.annotate(ApiCase.objects.all(), 0)
        self.assertEqual(Selector.filter_results(queryset, ['not_run']).count(), 0)
        self.assertEqual(Selector.filter_results(queryset, ['2']).count(), 0)
        self.assertEqual(Selector.filter_results(queryset, ['1']).count(), 1)

    def test_first_run_stays_untested_until_complete(self):
        self.publish()
        running = self.trace(self.revision.id, status=3)
        row = self.row()
        self.assertIsNone(row.list_status)
        self.assertIsNone(row.list_trace_id)
        self.assertTrue(row.list_active)
        self.assertEqual(Selector.collect([self.case.id])[self.case.id]['state'], 'not_run')
        running.status = 4
        running.save(update_fields=['status'])
        self.assertEqual(self.row().list_status, 4)

    @patch('src.apps.auto_api.services.execution.cases.list_execution.TestCase')
    def test_previous_pass_does_not_allow_duplicate_running_or_queued_execution(self, runner):
        self.publish()
        self.trace(self.revision.id, started=timezone.now() - timedelta(minutes=5))
        active = self.trace(self.revision.id, status=3)
        with self.assertRaises(AutoApiError) as caught:
            Service.prepare.__wrapped__(case_id=self.case.id, test_env=0,
                version_token=f'published:{self.revision.id}', user_id=self.case.case_people_id)
        self.assertEqual(caught.exception.code, 31236)
        active.status = 0
        active.save(update_fields=['status'])
        self.report_detail(status=2)
        with self.assertRaises(AutoApiError) as caught:
            Service.prepare.__wrapped__(case_id=self.case.id, test_env=0,
                version_token=f'published:{self.revision.id}', user_id=self.case.case_people_id)
        self.assertEqual(caught.exception.code, 31236)
        runner.assert_not_called()

    def test_active_report_recovery_keeps_previous_finished_result(self):
        self.publish()
        passed = self.trace(self.revision.id, started=timezone.now() - timedelta(minutes=5))
        detail = self.report_detail(status=3)
        detail.summary_data['meta']['execution_control'] = {'phase': 'automatic_recovery'}
        detail.save()
        running = self.trace(self.revision.id, status=0)
        running.test_suite_detail_id, running.test_suite_id = detail.id, detail.test_suite_id
        running.save()
        self.assertEqual(self.row().list_trace_id, passed.trace_id)

    def test_paged_fingerprints_do_not_load_other_editing_cases(self):
        with patch.object(Selector, 'editing_fingerprints', return_value={}) as fingerprints:
            Selector.annotate(ApiCase.objects.all(), 0, fingerprint_case_ids=[])
        fingerprints.assert_called_once_with([])

    def test_batch_supports_numeric_and_string_revision_ids(self):
        self.publish()
        self.trace(self.revision.id)
        latest = self.trace(str(self.revision.id), env=1, status=0)
        self.assertEqual(Selector.collect([self.case.id])[self.case.id]['trace_id'], latest.trace_id)

    def test_exact_result_record_never_falls_back_to_other_execution(self):
        self.publish()
        trace = self.trace(self.revision.id)
        ExecutionResult.objects.create(target_type='api_case', target_id=self.case.id,
            trace_id='unrelated-newer', test_env=0, status=0, result_data={'steps': []})
        result = Selector.collect([self.case.id])[self.case.id]
        self.assertIsNone(Selector.result_record(self.case.id, result))
        record = ExecutionResult.objects.create(target_type='api_case', target_id=self.case.id,
            trace_id=trace.trace_id, test_env=0, status=1, result_data={'steps': []})
        self.assertEqual(Selector.result_record(self.case.id, result).id, record.id)
        self.assertIsNone(Selector.result_record(self.case.id, {**result, 'test_env': 1}))
        self.assertIsNone(Selector.result_record(self.case.id, {**result, 'trace_id': None}))

    def test_mcp_search_uses_same_results_and_filter_as_page(self):
        from src.interfaces.mcp.tests.test_api_case_errors import ToolRegistry
        from src.interfaces.mcp.tools.api.case_tools.crud import register_case_crud_tools
        registry = ToolRegistry()
        register_case_crud_tools(registry)
        self.publish()
        expected_trace = self.trace(self.revision.id, status=1, env=1)
        self.trace(self.revision.id, status=3, env=1)
        self.trace(self.revision.id + 999, status=0)
        tool = registry.tools['search_api_cases']
        with patch('src.interfaces.mcp.tools.api.case_tools.crud.ApiExecutableSnapshotService.current_case_config',
                   return_value={}), patch('src.interfaces.mcp.tools.api.case_tools.crud._api_case_version_summary',
                   return_value={'publication_status': 'published'}):
            response = tool(project_product_id=self.product.id, result_statuses=[1])
            self.assertEqual(response['data']['count'], 1)
            item = response['data']['items'][0]
            self.assertEqual(item['list_result'], Selector.collect([self.case.id])[self.case.id])
            self.assertEqual((item['status'], item['list_result']['trace_id']), (1, expected_trace.trace_id))
            self.assertEqual(tool(project_product_id=self.product.id, result_statuses=[0])['data']['count'], 0)

    def test_batch_filter_total_and_pagination_cover_all_candidates(self):
        self.publish()
        self.trace(self.revision.id, status=0)
        ids = [self.case.id]
        for index in range(5):
            case = ApiCase.objects.create(project_product=self.product, module=self.case.module,
                case_people=self.case.case_people, name=f'分页用例{index}')
            ids.append(case.id)
        queryset = ApiCase.objects.filter(pk__in=ids).order_by('-id')
        pending = Selector.filter_queryset_by_results(queryset, ['2'])
        self.assertEqual(pending.count(), 5)
        self.assertEqual(list(pending.values_list('id', flat=True)[2:4]), list(reversed(ids[1:]))[2:4])
        failed = Selector.filter_queryset_by_results(queryset, ['0'])
        self.assertEqual(list(failed.values_list('id', flat=True)), [self.case.id])
        self.assertEqual(Selector.filter_queryset_by_results(queryset.filter(pk__gt=self.case.id), ['0']).count(), 0)

    def test_page_batch_loads_only_requested_fingerprints(self):
        with patch.object(Selector, 'editing_fingerprints', return_value={}) as fingerprints:
            Selector.collect([self.case.id])
        fingerprints.assert_called_once_with([self.case.id])

    def test_collect_is_bounded_for_unpaginated_callers(self):
        with patch.object(Selector, 'collect_batch', return_value={}) as batch:
            Selector.collect(range(405))
        self.assertEqual([len(call.args[0]) for call in batch.call_args_list], [200, 200, 5])

    def test_batch_query_count_does_not_grow_per_case_or_load_result_body(self):
        from django.test.utils import CaptureQueriesContext
        self.publish()
        self.trace(self.revision.id)
        with CaptureQueriesContext(self.memory) as single:
            Selector.collect([self.case.id])
        ids = [self.case.id]
        for index in range(19):
            case = ApiCase.objects.create(project_product=self.product, module=self.case.module,
                case_people=self.case.case_people, name=f'批量用例{index}')
            revision = ApiCaseRevision.objects.create(api_case=case, revision_no=1, payload={}, checksum='batch')
            ApiCaseRelease.objects.create(api_case=case, revision=revision, version_no=1,
                version_label='V1', status='published')
            ApiCaseExecutionTrace.objects.create(case_id=case.id, test_env=0, trace_id=f'batch-{index}',
                source_type=4, status=1, summary={'case_revision_id': revision.id})
            ids.append(case.id)
        with CaptureQueriesContext(self.memory) as multiple:
            results = Selector.collect(ids)
        self.assertEqual(len(results), 20)
        self.assertEqual(len(single), len(multiple))
        trace_selection = next(query['sql'] for query in multiple if 'ROW_NUMBER()' in query['sql'])
        # 终态判定允许读取报告/结果元数据，但不能重新展开发布版本查询或结果正文。
        self.assertNotIn('"result_data"', trace_selection)
        self.assertNotIn('apicaserelease', trace_selection.lower())


class CaseListExecutionAdmissionTests(SimpleTestCase):
    def prepare(self, row, token):
        manager = MagicMock()
        manager.select_for_update.return_value.filter.return_value.first.return_value = SimpleNamespace(id=1, name='Case')
        with patch('src.apps.auto_api.services.execution.cases.list_execution.ApiCase.objects', manager), \
             patch.object(Selector, 'annotate') as annotate, \
             patch.object(Selector, 'editing_fingerprints', return_value={1: 'a' * 64}):
            annotate.return_value.get.return_value = row
            return Service.prepare.__wrapped__(case_id=1, test_env=0, version_token=token, user_id=1)

    def row(self, version='published', status=1):
        return SimpleNamespace(list_version=version, list_revision_id=101 if version != 'unpublished' else None,
                               list_release_id=12, list_fingerprint='a' * 64, list_status=status, list_active=status in (2, 3))

    def test_version_changed_is_rejected_without_running(self):
        with self.assertRaises(AutoApiError) as caught:
            self.prepare(self.row(), 'published:99')
        self.assertEqual(caught.exception.code, 31235)

    def test_duplicate_active_execution_is_rejected(self):
        with self.assertRaises(AutoApiError) as caught:
            self.prepare(self.row(status=3), 'published:101')
        self.assertEqual(caught.exception.code, 31236)

    @patch('src.apps.auto_api.services.execution.cases.list_execution.TestCase')
    def test_published_pins_release_and_revision(self, runner):
        _, revision, release = self.prepare(self.row(), 'published:101')
        self.assertEqual((revision, release), (101, 12))
        runner.assert_called_once_with(user_id=1, test_env=0, case_id=1, revision_id=101, release_id=12)

    @patch('src.apps.auto_api.services.execution.cases.list_execution.TestCase')
    @patch('src.apps.auto_api.services.execution.cases.list_execution.ApiCaseRevisionService.record_execution_snapshot')
    def test_editing_is_frozen_before_execute(self, snapshot, runner):
        snapshot.return_value = SimpleNamespace(id=555)
        _, revision, release = self.prepare(self.row('unpublished'), 'unpublished:' + 'a' * 64)
        self.assertEqual((revision, release), (555, None))
        runner.return_value.trace_recorder.update_metadata.assert_called_once_with('Case', {
            'execution_source': 'editing', 'editing_fingerprint': 'a' * 64})

    @patch('src.apps.auto_api.services.execution.cases.list_execution.TestCase')
    def test_execution_without_durable_trace_is_rejected(self, runner):
        runner.return_value.trace_recorder.trace = None
        with self.assertRaises(AutoApiError) as caught:
            self.prepare(self.row(), 'published:101')
        self.assertEqual(caught.exception.code, 31237)


class CaseListExecutionEndpointTests(SimpleTestCase):
    def setUp(self):
        patcher = patch('src.apps.system.services.configuration.system_config.SystemConfigService.get_environment_display_names',
                        return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_hover_route_is_read_only_registered_and_passes_identity_and_environment(self):
        from django.http import QueryDict
        from django.urls import resolve
        from src.apps.auto_api.api.views.api_case import ApiCaseViews
        from src.apps.user.services.authorization.http_permission_registry import HTTP_PERMISSION_RULES
        route = resolve('/api/api/case/results/versions')
        self.assertEqual(route.func.actions, {'get': 'version_results'})
        self.assertEqual(HTTP_PERMISSION_RULES[(
            'src.apps.auto_api.api.views.api_case.ApiCaseViews', 'version_results', 'get')], 'api.case:read')
        user = SimpleNamespace(id=9)
        request = SimpleNamespace(user=SimpleNamespace(user_obj=user), query_params=QueryDict('id=10&test_env=0'))
        rows = [{'publication_status':'unpublished', 'status':None}]
        with patch.object(Selector, 'version_results', return_value=rows) as query:
            response = ApiCaseViews.version_results.__wrapped__(ApiCaseViews(), request)
        query.assert_called_once_with(10, None, user=user)
        self.assertEqual(response.data['data'], rows)

    def test_list_execution_persists_the_exact_selected_revision_and_runs_whole_case(self):
        from django.http import QueryDict
        from src.apps.auto_api.api.views.api_case import ApiCaseViews
        from src.apps.test_center.services.results.execution_result import ExecutionResultService
        result = SimpleNamespace(status=1, error_message=None, trace_id='example-list-trace',
                                 model_dump=lambda: {'id': 1, 'status': 1})
        runner = SimpleNamespace(test_case=MagicMock(return_value=result))
        request = SimpleNamespace(user={'id': 1}, query_params=QueryDict(
            'case_id=1&test_env=0&version_token=published:101&revision_id=invalid&case_sort=2'))
        with patch.object(ApiCaseViews, '_has_case_scope', return_value=True), \
             patch.object(Service, 'prepare', return_value=(runner, 101, 12)) as prepare, \
             patch('src.apps.auto_api.api.views.api_case.TestCase') as editing_runner, \
             patch.object(ExecutionResultService, 'save_result') as save, \
             patch.object(ExecutionResultService, 'serialize_run_response', return_value={}):
            response = ApiCaseViews.api_test_case.__wrapped__(ApiCaseViews(), request)
        self.assertEqual(response.status_code, 200)
        prepare.assert_called_once_with(case_id=1, test_env=0, version_token='published:101', user_id=1)
        editing_runner.assert_not_called()
        runner.test_case.assert_called_once_with(None)
        self.assertEqual((save.call_args.kwargs['revision_id'], save.call_args.kwargs['release_id']), (101, 12))

    def test_result_state_enum_is_registered_without_reusing_task_status_values(self):
        from src.apps.system.services.catalog.enum_catalog import EnumCatalogService
        with patch('src.apps.system.services.configuration.system_config.SystemConfigService.get_environment_display_names',
                   return_value={}):
            catalog = EnumCatalogService.catalog()
        self.assertEqual({item['key'] for item in catalog['api_case_list_result_state']},
                         {'not_run', 'needs_validation', 'executed'})

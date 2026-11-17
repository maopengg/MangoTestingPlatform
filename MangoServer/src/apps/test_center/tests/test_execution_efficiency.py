from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.db import connections
from django.db.backends.sqlite3.base import DatabaseWrapper
from django.http import QueryDict
from django.test import SimpleTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from mangotools.enums import TaskEnum, TestCaseTypeEnum

from src.apps.auto_api.models import ApiCaseExecutionStep, ApiCaseExecutionTrace
from src.apps.test_center.api.serializers.execution_efficiency import ExecutionEfficiencyQuerySerializer
from src.apps.test_center.api.views.test_suite import TestSuiteViews
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.models import ExecutionResult, ProductModule, Project, ProjectProduct, TestSuite, TestSuiteDetails
from src.apps.task_center.models import Tasks
from src.apps.test_center.schemas.execution_efficiency import ExecutionEfficiencyQuery
from src.apps.test_center.selectors.execution_efficiency import ExecutionEfficiencySelector, bounded
from src.apps.test_center.selectors.execution_efficiency_metrics import phase_durations, percentile, timing_snapshot
from src.apps.test_center.services.reporting.execution_efficiency import ExecutionEfficiencyService
from src.apps.user.middleware.permission import MenuActionPermission
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService
from src.interfaces.mcp.authentication import permission_error


class ExecutionEfficiencyTests(SimpleTestCase):
    def setUp(self):
        from src.apps.user.tests.permission_fixtures import install_legacy_endpoint_snapshot
        install_legacy_endpoint_snapshot(self)

    def test_range_limits_and_timezone_modes(self):
        now = timezone.now()
        for use_tz in (False, True):
            with override_settings(USE_TZ=use_tz):
                query = ExecutionEfficiencyQuery(start_at=now - timedelta(days=1), end_at=now)
                self.assertEqual(timezone.is_aware(query.start_at), use_tz)
        for start, end in ((now, now), (now, now - timedelta(seconds=1)), (now - timedelta(days=32), now)):
            with self.assertRaises(TestCenterError):
                ExecutionEfficiencyQuery(start_at=start, end_at=end)

    def test_http_accepts_multi_select_protocol_and_rejects_bad_page(self):
        serializer = ExecutionEfficiencyQuerySerializer.from_params(QueryDict('test_env__in=1,2&case_type__in=0,1&module_ids__in=10,11'))
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['test_env'], [1, 2])
        self.assertEqual(serializer.validated_data['module_ids'], [10, 11])
        self.assertFalse(ExecutionEfficiencyQuerySerializer.from_params(QueryDict('page_size=10000')).is_valid())

    def test_guard_rejects_instead_of_silently_sampling(self):
        with self.assertRaises(TestCenterError):
            bounded([1, 2, 3], 2)
        self.assertIsNone(percentile([], .95))
        self.assertEqual(percentile(list(range(1, 101)), .95), 95)

    def test_phase_intervals_are_disjoint_and_clamped_to_trace(self):
        now = timezone.now()
        trace = {'started_at': now, 'finished_at': now + timedelta(seconds=10)}
        def step(pk, parent, kind, start, end):
            return {'id': pk, 'parent_step_id': parent, 'step_type': kind,
                    'started_at': now + timedelta(seconds=start), 'finished_at': now + timedelta(seconds=end)}
        steps = [step(1, None, 'case_front', -1, 11), step(2, 1, 'request', 1, 2),
                 step(3, 1, 'posterior', 2, 8), step(4, 3, 'assertion', 4, 5)]
        phases = phase_durations(trace, steps)
        self.assertEqual(sum(phases.values()), 10000)
        self.assertEqual(phases['接口请求'], 1000)
        self.assertEqual(phases['后置处理'], 5000)
        self.assertEqual(phases['断言'], 1000)

    def test_missing_steps_remain_uncollected_not_zero(self):
        now = timezone.now()
        self.assertEqual(phase_durations({'started_at': now, 'finished_at': now + timedelta(seconds=2)}, []), {'其他/未采集': 2000})
        self.assertEqual(phase_durations({'started_at': now, 'finished_at': None}, []), {})

    def test_permission_http_mcp_and_guest(self):
        required = 'report.execution_efficiency:read'
        self.assertIn(required, PermissionMenuService.guest_permission_keys())
        user = SimpleNamespace(id=1)
        view = TestSuiteViews()
        view.action = 'execution_efficiency'
        request = SimpleNamespace(method='GET', path='/api/system/test/suite/execution-efficiency',
                                  query_params=QueryDict(), data={}, user=SimpleNamespace(user_obj=user))
        for grants, allowed in (({required}, True), ({'report:read'}, False), (set(), False)):
            with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                    patch.object(PermissionMenuService, 'permission_keys_for_user', return_value=grants):
                self.assertEqual(MenuActionPermission().has_permission(request, view), allowed)
                self.assertEqual(permission_error(user, 'list_execution_efficiency', {}) is None, allowed)
        view.action = 'unregistered_efficiency'
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=True):
            from src.apps.user.exceptions import UserError
            with self.assertRaises(UserError):
                MenuActionPermission().has_permission(request, view)

    def test_http_dispatch_validates_filters_and_uses_the_shared_service(self):
        user = SimpleNamespace(id=1)
        request = APIRequestFactory().get('/api/system/test/suite/execution-efficiency', {'test_env__in': '1,2'})
        force_authenticate(request, user=SimpleNamespace(user_obj=user))
        with patch.object(PermissionMenuService, 'is_effective_super_admin', return_value=False), \
                patch.object(PermissionMenuService, 'permission_keys_for_user', return_value={'report.execution_efficiency:read'}), \
                patch.object(ExecutionEfficiencyService, 'query', return_value={'items': [], 'summary': {}}) as query:
            response = TestSuiteViews.as_view({'get': 'execution_efficiency'})(request)
        self.assertEqual(response.data['code'], 200)
        self.assertEqual(query.call_args.args[1].test_env, [1, 2])
        self.assertEqual(response['Cache-Control'], 'no-store')

    @override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})
    def test_scopes_precede_cache_and_cache_is_paged_without_shared_mutation(self):
        cache.clear()
        user = SimpleNamespace(id=1, role_id=2)
        query = ExecutionEfficiencyQuery()
        snapshot = {'items': [{'id': index} for index in range(3)], 'anomalies': [{'id': 2}], 'summary': {}}
        with patch.object(ExecutionEfficiencySelector, 'scoped_reports', return_value=TestSuite.objects.none()) as scope, \
                patch.object(ExecutionEfficiencySelector, 'current', return_value=snapshot) as compute, \
                patch('src.apps.test_center.services.reporting.execution_efficiency.ExecutionCapacitySelector.api_workers', return_value={'online': 1, 'capacity': 1, 'running': 1}), \
                patch('src.apps.test_center.services.reporting.execution_efficiency.SystemConfigService.get_api_worker_thread_pool_size', return_value=1), \
                patch('src.apps.test_center.services.reporting.execution_efficiency.SystemConfigService.get_executor_execution_timeout_seconds', return_value=3600):
            first = ExecutionEfficiencyService.query(user, query.model_copy(update={'page_size': 1}))
            second = ExecutionEfficiencyService.query(user, query.model_copy(update={'page': 2, 'page_size': 1}))
            anomaly = ExecutionEfficiencyService.query(user, query.model_copy(update={'section': 'anomalies'}))
            self.assertEqual(first['items'], [{'id': 0}])
            self.assertEqual(second['items'], [{'id': 1}])
            self.assertEqual(anomaly['items'], [{'id': 2}])
            self.assertEqual(compute.call_count, 1)
            self.assertEqual(scope.call_count, 3)
            self.assertIn('anomalies', snapshot)
        cache.clear()


class ExecutionEfficiencyOrmTests(SimpleTestCase):
    """Real ORM/SQL on an isolated in-memory connection; no environment DB or migrations."""
    def setUp(self):
        self.alias = 'efficiency_isolated'
        self.database = DatabaseWrapper({
            'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:', 'USER': '', 'PASSWORD': '',
            'HOST': '', 'PORT': '', 'OPTIONS': {}, 'TIME_ZONE': None, 'AUTOCOMMIT': True,
            'CONN_MAX_AGE': 0, 'CONN_HEALTH_CHECKS': False, 'ATOMIC_REQUESTS': False,
        }, alias=self.alias)
        self.database.ensure_connection()
        connections[self.alias] = self.database
        self.addCleanup(self.close_database)
        self.models = (Project, ProjectProduct, ProductModule, Tasks, TestSuite, TestSuiteDetails,
                       ApiCaseExecutionTrace, ApiCaseExecutionStep, ExecutionResult)
        with self.database.cursor() as cursor:
            for model in self.models:
                columns = ', '.join(f'"{field.column}" {field.db_type(self.database)}'
                                    + (' PRIMARY KEY' if field.primary_key else '') for field in model._meta.concrete_fields)
                cursor.execute(f'CREATE TABLE "{model._meta.db_table}" ({columns})')
        Project.objects.using(self.alias).bulk_create([Project(id=1, name='示例项目')])
        ProjectProduct.objects.using(self.alias).bulk_create([ProjectProduct(id=1, project_id=1, name='示例产品'), ProjectProduct(id=2, project_id=1, name='范围外产品')])
        TestSuite.objects.using(self.alias).bulk_create([
            TestSuite(id=1, project_product_id=1, user_id=1, test_env=1, status=3, is_notice=0, execution_name='串行任务', api_concurrency_limit=1),
            TestSuite(id=2, project_product_id=2, user_id=1, test_env=1, status=3, is_notice=0, execution_name='不可见任务'),
        ])
        self.now = timezone.now()
        TestSuiteDetails.objects.using(self.alias).bulk_create([
            TestSuiteDetails(id=1, test_suite_id=1, project_product_id=1, test_env=1, type=1, case_id=5219, case_name='异步清理用例', status=3, retry=1, push_time=self.now - timedelta(minutes=5)),
            TestSuiteDetails(id=2, test_suite_id=1, project_product_id=1, test_env=1, type=1, case_id=2, case_name='等待用例', status=2, retry=0),
            TestSuiteDetails(id=3, test_suite_id=1, project_product_id=1, test_env=1, type=1, case_id=3, case_name='已结束用例', status=1, retry=1, is_excluded=True),
            TestSuiteDetails(id=4, test_suite_id=2, project_product_id=2, test_env=1, type=1, case_id=4, case_name='不可见用例', status=2, retry=0),
            TestSuiteDetails(id=5, test_suite_id=1, project_product_id=1, test_env=1, type=0, case_id=5, case_name='UI用例', status=1, retry=1),
            TestSuiteDetails(id=6, test_suite_id=1, project_product_id=1, test_env=1, type=2, case_id=6, case_name='Pytest用例', status=1, retry=1),
        ])
        TestSuiteDetails.objects.using(self.alias).filter(id=2).update(create_time=self.now - timedelta(minutes=10))
        ApiCaseExecutionTrace.objects.using(self.alias).bulk_create([
            ApiCaseExecutionTrace(id=1, trace_id='current', source_type=1, test_suite_id=1, test_suite_detail_id=1, case_id=5219, case_name='异步清理用例', status=3, started_at=self.now - timedelta(minutes=5)),
            ApiCaseExecutionTrace(id=2, trace_id='complete', source_type=1, test_suite_id=1, test_suite_detail_id=3, case_id=3, case_name='已结束用例', status=1, started_at=self.now - timedelta(seconds=20), finished_at=self.now - timedelta(seconds=10)),
        ])
        ApiCaseExecutionStep.objects.using(self.alias).bulk_create([
            ApiCaseExecutionStep(id=1, trace_id=1, step_key='posterior:1', step_type='posterior', step_name='执行响应后置处理', status=3, started_at=self.now - timedelta(minutes=4)),
            ApiCaseExecutionStep(id=2, trace_id=2, step_key='request:1', step_type='request', step_name='接口请求', status=1, started_at=self.now - timedelta(seconds=20), finished_at=self.now - timedelta(seconds=19)),
        ])
        for model in self.models:
            mocked = patch.object(model, 'objects', model.objects.using(self.alias))
            mocked.start()
            self.addCleanup(mocked.stop)
        for owner, method, result in ((PermissionMenuService, 'is_effective_super_admin', False),
                                      (ProjectProductScopeService, 'can_view_all_project_data', False),
                                      (ProjectProductScopeService, 'project_product_ids_for_user', {1})):
            mocked = patch.object(owner, method, return_value=result)
            mocked.start()
            self.addCleanup(mocked.stop)
        self.user = SimpleNamespace(id=1, role_id=1)

    def close_database(self):
        del connections[self.alias]
        self.database.connection.close()

    def current(self, **kwargs):
        query = ExecutionEfficiencyQuery(**kwargs)
        reports = ExecutionEfficiencySelector.scoped_reports(self.user, query)
        return ExecutionEfficiencySelector.current(reports, query, {'online': 2, 'capacity': 2, 'running': 1}, 2, {1: 3600})

    def test_current_queue_respects_scope_concurrency_and_dates_without_writing(self):
        with CaptureQueriesContext(self.database) as captured:
            data = self.current(start_at=self.now - timedelta(days=10), end_at=self.now - timedelta(days=9))
        self.assertLessEqual(len(captured), 7)
        self.assertTrue(all(item['sql'].lstrip().upper().startswith('SELECT') for item in captured))
        self.assertTrue(all('result_data' not in item['sql'] and 'input_summary' not in item['sql'] for item in captured))
        self.assertEqual(data['summary']['pending'], 1)
        self.assertEqual(data['items'][0]['diagnosis'], '报告并发限制')
        self.assertEqual(data['items'][0]['completed'], 3)
        self.assertEqual(data['items'][0]['current_case']['stage'], '执行响应后置处理')
        self.assertGreater(data['items'][0]['longest_wait_ms'], 590000)
        self.assertEqual(data['anomalies'], [])

    def test_finished_trace_is_anomaly_not_business_failure(self):
        ApiCaseExecutionTrace.objects.filter(id=1).update(status=0, finished_at=self.now - timedelta(seconds=30))
        data = self.current()
        self.assertEqual(len(data['anomalies']), 1)
        self.assertIn('链路已结束', data['anomalies'][0]['reason'])

    def test_prior_trace_does_not_describe_a_reclaimed_attempt(self):
        ApiCaseExecutionTrace.objects.filter(id=1).update(status=0, finished_at=self.now - timedelta(minutes=1))
        TestSuiteDetails.objects.filter(id=1).update(push_time=self.now)
        data = self.current()
        self.assertEqual(data['anomalies'], [])
        self.assertEqual(data['items'][0]['current_case']['stage'], '未采集')

    def test_timeout_uses_configured_limit(self):
        query = ExecutionEfficiencyQuery()
        data = ExecutionEfficiencySelector.current(ExecutionEfficiencySelector.scoped_reports(self.user, query), query,
                                                  {'online': 1, 'capacity': 1, 'running': 1}, 1, {1: 60})
        self.assertIn('超过当前配置', data['anomalies'][0]['reason'])

    def test_history_includes_excluded_cost_and_basic_types(self):
        query = ExecutionEfficiencyQuery(section='timing', start_at=self.now - timedelta(days=1), end_at=self.now + timedelta(seconds=1))
        with CaptureQueriesContext(self.database) as captured:
            data = ExecutionEfficiencySelector.historical(ExecutionEfficiencySelector.scoped_reports(self.user, query, historical=True), query)
        self.assertLessEqual(len(captured), 5)
        self.assertEqual(data['summary']['completed'], 3)
        self.assertEqual(data['summary']['sample_count'], 1)
        self.assertEqual(data['summary']['p95_ms'], 10000)
        self.assertEqual(data['summary']['covered_completed'], 1)
        self.assertEqual(sum(row['duration_ms'] for row in data['phases']), 10000)
        self.assertEqual([row['completed'] for row in data['basic']], [1, 1, 1])
        self.assertEqual(data['slow_cases'][0]['dominant_phase'], '其他/未采集')

    def test_type_filter_excludes_api_timings(self):
        query = ExecutionEfficiencyQuery(section='timing', case_type=[0], end_at=self.now + timedelta(seconds=1))
        data = ExecutionEfficiencySelector.historical(ExecutionEfficiencySelector.scoped_reports(self.user, query, historical=True), query)
        self.assertEqual(data['summary']['sample_count'], 0)
        self.assertIsNone(data['summary']['p95_ms'])

    def test_empty_scope_does_not_expand_to_all_products(self):
        with patch.object(ProjectProductScopeService, 'project_product_ids_for_user', return_value=set()):
            self.assertEqual(self.current()['items'], [])

    def test_retry_pending_has_no_invented_first_wait_time(self):
        TestSuiteDetails.objects.filter(id=2).update(retry=2)
        row = self.current()['items'][0]
        self.assertIsNone(row['longest_wait_ms'])
        self.assertEqual(row['unknown_wait_count'], 1)

    def test_result_mismatch_is_detected_without_loading_json(self):
        ExecutionResult.objects.bulk_create([ExecutionResult(
            source_type='test_suite', target_type='api_case', target_id=5219, test_suite_id=1,
            test_suite_detail_id=1, status=1, is_latest=True, result_data={'not_read': True},
        )])
        ExecutionResult.objects.update(create_time=self.now - timedelta(seconds=30))
        data = self.current()
        self.assertEqual(len(data['anomalies']), 1)
        self.assertIn('已有结束的执行结果', data['anomalies'][0]['reason'])

    def test_business_failure_is_not_platform_anomaly(self):
        TestSuiteDetails.objects.filter(id=3).update(status=TaskEnum.FAIL.value)
        ApiCaseExecutionTrace.objects.filter(id=2).update(status=TaskEnum.FAIL.value)
        self.assertEqual(self.current()['anomalies'], [])

    def test_history_counts_completion_once_despite_retry_traces(self):
        ApiCaseExecutionTrace.objects.bulk_create([ApiCaseExecutionTrace(
            id=3, trace_id='retry', source_type=1, test_suite_id=1, test_suite_detail_id=3,
            case_id=3, case_name='重试尝试', status=1,
            started_at=self.now - timedelta(seconds=8), finished_at=self.now - timedelta(seconds=3),
        )])
        query = ExecutionEfficiencyQuery(section='timing', end_at=self.now + timedelta(seconds=1))
        data = ExecutionEfficiencySelector.historical(ExecutionEfficiencySelector.scoped_reports(self.user, query, historical=True), query)
        self.assertEqual(data['summary']['completed'], 3)
        self.assertEqual(sum(row['completed'] for row in data['trend']), 1)
        self.assertEqual(data['summary']['sample_count'], 2)
        self.assertEqual(data['summary']['retry_count'], 1)
        self.assertEqual(data['summary']['retry_duration_ms'], 5000)

    def test_guard_is_enforced_before_loading_unbounded_trace_data(self):
        with patch('src.apps.test_center.selectors.execution_efficiency.MAX_DETAILS', 1):
            with self.assertRaises(TestCenterError):
                self.current()

    def test_no_worker_and_busy_capacity_diagnoses(self):
        query = ExecutionEfficiencyQuery()
        reports = ExecutionEfficiencySelector.scoped_reports(self.user, query)
        offline = ExecutionEfficiencySelector.current(reports, query, {'online': 0, 'capacity': 0, 'running': 0}, 1, {1: 3600})
        self.assertEqual(offline['items'][0]['diagnosis'], '未检测到在线 API Worker')
        TestSuite.objects.filter(id=1).update(api_concurrency_limit=2)
        busy = ExecutionEfficiencySelector.current(reports, query, {'online': 1, 'capacity': 2, 'running': 2}, 2, {1: 3600})
        self.assertEqual(busy['items'][0]['diagnosis'], '当前执行容量繁忙')

    def test_normal_result_propagation_does_not_raise_an_anomaly(self):
        ApiCaseExecutionTrace.objects.filter(id=1).update(status=1, finished_at=self.now)
        self.assertEqual(self.current()['anomalies'], [])

    def test_history_time_query_uses_existing_composite_index_for_both_states(self):
        with self.database.cursor() as cursor:
            cursor.execute('CREATE INDEX idx_suite_retained_time ON test_suite (report_retained, create_time DESC, id DESC)')
            query = ExecutionEfficiencyQuery(section='timing', end_at=self.now + timedelta(seconds=1))
            reports = ExecutionEfficiencySelector.scoped_reports(self.user, query, historical=True)
            for state in (True, False):
                sql, params = reports.filter(report_retained__in=[state]).order_by('-create_time', '-id').query.get_compiler(connection=self.database).as_sql()
                cursor.execute('EXPLAIN QUERY PLAN ' + sql, params)
                self.assertIn('idx_suite_retained_time', str(cursor.fetchall()))

    def test_task_options_are_scoped_and_paged_without_count_query(self):
        Tasks.objects.bulk_create([
            Tasks(id=index, name=f'示例任务{index}', project_product_id=1 if index < 3 else 2, case_people_id=1)
            for index in range(1, 4)
        ])
        with CaptureQueriesContext(self.database) as captured:
            data = ExecutionEfficiencyService.options(self.user, kind='tasks', page=1, page_size=1)
        self.assertEqual(len(captured), 1)
        self.assertTrue(data['has_more'])
        self.assertEqual(data['items'], [{'id': 2, 'name': '示例任务2'}])
        denied = ExecutionEfficiencyService.options(self.user, kind='tasks', product_id=2)
        self.assertEqual(denied['items'], [])

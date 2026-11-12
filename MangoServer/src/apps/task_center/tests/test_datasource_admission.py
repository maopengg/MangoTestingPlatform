from copy import deepcopy
from contextlib import nullcontext
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from django.db import connections, transaction
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.data_factory.schemas.performance import DatasourcePerformancePolicy
from src.apps.data_factory.services.governance.datasource_governor import DatasourceGovernorService as Governor
from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.task_center.services.execution.claim import ApiTaskClaimService as Claim
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.services.reporting.test_suite.infrastructure import TestSuiteInfrastructureService as Infrastructure
from src.apps.test_center.services.reporting.test_suite.disposition import TestSuiteDispositionService
from src.apps.test_center.services.reporting.test_suite.update_test_suite import UpdateTestSuite
from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService
from src.apps.auto_api.models import ApiCaseExecutionTrace, ApiCaseExecutionStep


class DatasourceClaimTests(TestCase):
    """只在临时 SQLite 建测试 ORM 表，不运行迁移，不连接环境数据库。"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.directory = TemporaryDirectory(prefix='mango-admission-')
        cls.alias = 'isolated_admission'
        config = deepcopy(connections['default'].settings_dict)
        config.update(ENGINE='django.db.backends.sqlite3', NAME=str(Path(cls.directory.name) / 'control.db'),
                      USER='', PASSWORD='', HOST='', PORT='', OPTIONS={}, TIME_ZONE=None)
        connections.databases[cls.alias] = config
        cls.connection = connections[cls.alias]
        with cls.connection.schema_editor() as editor:
            editor.create_model(TestSuite)
            editor.create_model(TestSuiteDetails)
            editor.create_model(ApiCaseExecutionTrace)
            editor.create_model(ApiCaseExecutionStep)
        cls.connection.disable_constraint_checking()

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        del connections.databases[cls.alias]
        delattr(connections._connections, cls.alias)
        cls.directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.suites = TestSuite.objects.db_manager(self.alias)
        self.details = TestSuiteDetails.objects.db_manager(self.alias)
        ApiCaseExecutionStep.objects.using(self.alias).all()._raw_delete(self.alias)
        ApiCaseExecutionTrace.objects.using(self.alias).all()._raw_delete(self.alias)
        self.details.all()._raw_delete(self.alias)
        self.suites.all()._raw_delete(self.alias)
        self.policy = DatasourcePerformancePolicy()
        self.target = SimpleNamespace(id=1, db_type=0, host='mysql.example.com', port=3306)
        self.bindings = [SimpleNamespace(environment=0, database=self.target,
                                         datasource_alias=SimpleNamespace(project_product_id=1))]
        original_atomic = transaction.atomic
        block = Infrastructure.block.__wrapped__
        guards = [
            patch.object(TestSuite, 'objects', self.suites),
            patch.object(TestSuiteDetails, 'objects', self.details),
            patch('src.apps.task_center.services.execution.claim.transaction.atomic',
                  side_effect=lambda *args, **kwargs: original_atomic(using=self.alias)),
            patch.object(Infrastructure, 'block', side_effect=lambda *args, **kwargs: block(Infrastructure, *args, **kwargs)),
            patch.object(Infrastructure, 'close_interrupted_trace'),
            patch.object(DataFactoryQuerySelector, 'execution_targets', side_effect=lambda *args: self.bindings),
            patch.object(Governor, 'policy', return_value=self.policy),
        ]
        for guard in guards:
            guard.start()
            self.addCleanup(guard.stop)
        self.suite = self.suites.create(id=1, project_product_id=1, user_id=1, test_env=0,
                                        api_concurrency_limit=100, status=2, is_notice=0)

    def add_cases(self, count, suite=None):
        suite = suite or self.suite
        self.details.bulk_create([TestSuiteDetails(test_suite_id=suite.id, project_product_id=suite.project_product_id,
            type=TestCaseTypeEnum.API.value, test_env=0, case_id=index + 1, case_name=f'AUTO_{index}',
            status=2, retry=0) for index in range(count)])

    def claim(self):
        now = timezone.now()
        return Claim.claim_with_platform_lock(now, now - timedelta(hours=1), 100, max_attempts=3)

    def test_ten_workers_ten_slots_ten_thousand_cases_use_configured_concurrency_not_fixture_window(self):
        self.add_cases(10000)
        # 生产领取锁串行化这 100 次竞争；模拟所有 Worker 均已取得领取锁后的实际 ORM 路径。
        claimed = [result for _ in range(10) for _ in range(10) if (result := self.claim()) is not None]
        self.assertEqual(len(claimed), 100)
        self.assertEqual(self.details.filter(status=3).count(), 100)
        self.assertEqual(self.details.filter(status=2, retry=0).count(), 9900)
        self.assertEqual(len({item.test_suite_details for item in claimed}), 100)
        self.assertIsNone(self.claim())

    def test_long_case_lifecycle_does_not_block_other_cases_or_instances(self):
        self.add_cases(5)
        first = [self.claim() for _ in range(3)]
        self.assertIsNotNone(self.claim())
        self.assertIsNotNone(self.claim())
        other = self.suites.create(id=2, project_product_id=2, user_id=1, test_env=0,
                                   api_concurrency_limit=100, status=2, is_notice=0)
        self.bindings.append(SimpleNamespace(environment=0, datasource_alias=SimpleNamespace(project_product_id=2),
            database=SimpleNamespace(id=2, db_type=0, host='other.example.com', port=3306)))
        self.add_cases(1, other)
        self.assertEqual(self.claim().test_suite, 2)
        self.assertEqual(self.details.filter(status=3).count(), 6)

    def test_new_report_gets_turn_before_old_report_claims_every_remaining_slot(self):
        self.add_cases(10)
        self.assertEqual(self.claim().test_suite, 1)
        other = self.suites.create(id=2, project_product_id=1, user_id=1, test_env=0,
                                  api_concurrency_limit=100, status=2, is_notice=0)
        self.add_cases(10, other)
        self.assertEqual(self.claim().test_suite, 2)
        self.assertEqual(self.claim().test_suite, 1)
        self.assertEqual(self.claim().test_suite, 2)
        self.assertEqual(self.details.filter(status=3).count(), 4)

    def test_renewal_does_not_reorder_reports_after_dispatch(self):
        self.add_cases(2)
        first = self.resource_claim(platform_limit=2)
        other = self.suites.create(id=2, project_product_id=1, user_id=1, test_env=0,
                                  api_concurrency_limit=2, status=2, is_notice=0)
        self.add_cases(2, other)
        second = self.resource_claim(platform_limit=2)
        self.assertEqual(second.test_suite, 2)
        self.details.filter(id=first.test_suite_details).update(push_time=timezone.now() + timedelta(days=1))
        order = Claim.candidate_suite_ids(timezone.now() - timedelta(hours=1), 3)
        self.assertEqual(order[:2], [1, 2])

    def test_candidate_scan_query_budget_does_not_grow_per_report(self):
        from django.test.utils import CaptureQueriesContext
        self.add_cases(3)
        for index in range(2, 12):
            suite = self.suites.create(id=index, project_product_id=1, user_id=1, test_env=0,
                                      api_concurrency_limit=2, status=2, is_notice=0)
            self.add_cases(2, suite)
        with CaptureQueriesContext(self.connection) as captured:
            order = Claim.candidate_suite_ids(timezone.now() - timedelta(hours=1), 3)
        self.assertEqual(len(order), 11)
        self.assertEqual(len(captured), 4)

    def test_legacy_empty_json_is_eligible_and_blocked_execution_is_never_replayed(self):
        self.add_cases(4)
        rows = list(self.details.order_by('id'))
        for row, summary in zip(rows, [None, [], {'children': [], 'meta': {}}]):
            self.details.filter(id=row.id).update(summary_data=summary)
        for _ in range(3):
            self.assertIsNotNone(self.claim())
        old = self.details.get(id=rows[0].id)
        self.details.filter(id=old.id).update(push_time=timezone.now() - timedelta(hours=2))
        self.assertIsNone(self.claim())
        old.refresh_from_db(using=self.alias)
        self.assertTrue(Infrastructure.is_blocked(old.summary_data))
        self.assertEqual(old.retry, 1)
        self.assertEqual((old.status, old.fail), (TaskEnum.FAIL.value, 0))
        self.assertIsNotNone(self.claim())
        self.assertEqual(self.details.get(id=rows[3].id).retry, 1)
        self.assertIsNone(self.claim())

    def test_blocking_ends_report_preserves_review_fence_and_allows_group_notice(self):
        from src.apps.data_factory.schemas.performance import DatasourceInfrastructureIssue
        from src.apps.test_center.services.reporting.test_suite.send_notice import SendNotice
        from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService
        from src.apps.test_center.exceptions import TestCenterError
        self.add_cases(1)
        command = self.claim()
        issue = DatasourceInfrastructureIssue(code=34185, message='control unavailable')
        self.assertTrue(Infrastructure.block(command.test_suite_details, command.attempt, [issue]))
        row = self.details.get(id=command.test_suite_details)
        self.assertEqual((row.status, row.retry, row.success, row.fail, row.warning), (TaskEnum.FAIL.value, 1, 0, 0, 0))
        self.assertEqual(self.suites.get(id=self.suite.id).status, TaskEnum.FAIL.value)
        self.assertTrue(Infrastructure.blocked_suites([self.suite.id]).exists())
        with self.assertRaises(TestCenterError):
            TestSuiteRetryService.ensure_infrastructure_reviewed(row)
        notice = SendNotice.__new__(SendNotice)
        notice.test_suite = self.suites.get(id=self.suite.id)
        with patch('src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroupExecutionService.complete_test_suite') as grouped:
            notice.send_test_suite()
        grouped.assert_called_once_with(self.suite.id)
        self.suites.filter(id=self.suite.id).update(status=TaskEnum.STOPPED.value)
        self.assertFalse(Infrastructure.block(row.id, command.attempt, [issue]))
        self.details.filter(id=row.id).update(retry=2)
        self.assertFalse(Infrastructure.block(row.id, command.attempt, [issue]))

    def test_block_review_requires_explicit_stopped_report_diagnosis_and_clean_resources(self):
        from src.apps.test_center.services.reporting.test_suite.disposition import TestSuiteDispositionService as Disposition
        from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        from src.apps.test_center.exceptions import TestCenterError
        self.add_cases(1)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        self.suites.filter(id=self.suite.id).update(status=TaskEnum.STOPPED.value)
        self.details.filter(id=command.test_suite_details).update(status=TaskEnum.STOPPED.value)
        values = {'failure_reason': 'platform', 'failure_description': '已独立核查原请求结果与零残留', 'is_excluded': False}
        raw_update = Disposition.update.__wrapped__
        with patch('src.apps.test_center.services.reporting.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=True), \
                patch.object(DatasourceInfrastructureService, 'review_ready', return_value=False):
            with self.assertRaises(TestCenterError):
                raw_update(Disposition, command.test_suite_details, values.copy(), user=SimpleNamespace(id=7))
        with patch('src.apps.test_center.services.reporting.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=True), \
                patch.object(DatasourceInfrastructureService, 'review_ready', return_value=True):
            raw_update(Disposition, command.test_suite_details, values.copy(), user=SimpleNamespace(id=7))
        row = self.details.get(id=command.test_suite_details)
        self.assertEqual(row.status, TaskEnum.STOPPED.value)
        self.assertFalse(row.summary_data['meta']['execution_control']['requires_review'])
        self.assertEqual(row.summary_data['meta']['execution_control']['reviewed_by'], 7)
        with patch.object(DatasourceInfrastructureService, 'review_ready', return_value=True):
            TestSuiteRetryService.ensure_infrastructure_reviewed(row)

    def test_blocked_only_report_can_be_reviewed_without_stopping_or_changing_results(self):
        from src.apps.test_center.services.reporting.test_suite.disposition import TestSuiteDispositionService as Disposition
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        self.add_cases(2)
        commands = [self.claim(), self.claim()]
        for command in commands:
            Infrastructure.block(command.test_suite_details, command.attempt, [])
        self.assertFalse(Infrastructure.has_live_details(self.suite.id))
        raw_update = Disposition.update.__wrapped__
        with patch('src.apps.test_center.services.reporting.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=True), \
                patch.object(DatasourceInfrastructureService, 'review_ready', return_value=True):
            raw_update(Disposition, commands[0].test_suite_details,
                {'failure_reason': 'platform', 'failure_description': '已核查旧请求与全部清理结果'},
                user=SimpleNamespace(id=7))
        row = self.details.get(id=commands[0].test_suite_details)
        untouched = self.details.get(id=commands[1].test_suite_details)
        self.assertFalse(row.summary_data['meta']['execution_control']['requires_review'])
        self.assertTrue(untouched.summary_data['meta']['execution_control']['requires_review'])
        self.assertEqual((row.status, row.retry, row.success, row.fail, row.warning), (TaskEnum.FAIL.value, 1, 0, 0, 0))
        self.assertEqual(self.suites.get(id=self.suite.id).status, TaskEnum.FAIL.value)

    def test_pending_and_running_siblings_prevent_blocked_review(self):
        from src.apps.test_center.services.reporting.test_suite.disposition import TestSuiteDispositionService as Disposition
        from src.apps.test_center.exceptions import TestCenterError
        self.add_cases(2)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        self.assertEqual(self.suites.get(id=self.suite.id).status, TaskEnum.PROCEED.value)
        for status in (TaskEnum.STAY_BEGIN.value, TaskEnum.PROCEED.value):
            self.details.exclude(id=command.test_suite_details).update(status=status, summary_data=None)
            self.assertTrue(Infrastructure.has_live_details(self.suite.id))
            with patch('src.apps.test_center.services.reporting.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=True), \
                    self.subTest(status=status), self.assertRaises(TestCenterError):
                Disposition.update.__wrapped__(Disposition, command.test_suite_details,
                    {'failure_reason': 'platform', 'failure_description': '已核查'}, user=SimpleNamespace(id=7))

    def test_legacy_interruption_finishes_without_replay_or_changing_review_and_is_idempotent(self):
        self.add_cases(1)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        row = self.details.get(id=command.test_suite_details)
        summary = deepcopy(row.summary_data)
        self.details.filter(id=row.id).update(status=TaskEnum.PROCEED.value)
        self.suites.filter(id=self.suite.id).update(status=TaskEnum.PROCEED.value)
        raw_finish = Infrastructure.finish_legacy_block.__wrapped__
        with patch.object(Infrastructure, 'finish_legacy_block',
                          side_effect=lambda detail_id: raw_finish(Infrastructure, detail_id)):
            self.assertEqual(Infrastructure.repair_legacy_blocks(), 1)
            self.assertEqual(Infrastructure.repair_legacy_blocks(), 0)
        row.refresh_from_db(using=self.alias)
        self.assertEqual((row.status, row.retry), (TaskEnum.FAIL.value, command.attempt))
        self.assertEqual(row.summary_data, summary)
        self.assertEqual(self.suites.get(id=self.suite.id).status, TaskEnum.FAIL.value)
        self.assertIsNone(self.claim())

    def test_legacy_repair_preserves_stopped_report_and_unrelated_pending_cases(self):
        self.add_cases(2)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        self.details.filter(id=command.test_suite_details).update(status=TaskEnum.PROCEED.value)
        self.suites.filter(id=self.suite.id).update(status=TaskEnum.STOPPED.value)
        self.assertEqual(Infrastructure.repair_legacy_blocks(), 0)
        self.assertEqual(self.details.exclude(id=command.test_suite_details).get().status, TaskEnum.STAY_BEGIN.value)

    def test_late_progress_cannot_resurrect_interrupted_execution(self):
        from src.apps.test_center.services.reporting.test_suite.update_test_suite import UpdateTestSuite
        self.add_cases(1)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        self.assertFalse(UpdateTestSuite.update_test_suite_details_status(
            command.test_suite_details, TaskEnum.PROCEED.value, 'late progress'))
        row = self.details.get(id=command.test_suite_details)
        self.assertEqual(row.status, TaskEnum.FAIL.value)
        self.assertIn('执行已中断', row.error_message)

    def test_interrupted_trace_and_running_steps_finish_but_other_attempts_are_untouched(self):
        from src.apps.auto_api.services.execution_trace.recorder import ApiCaseExecutionTraceRecorder
        traces = ApiCaseExecutionTrace.objects.db_manager(self.alias)
        steps = ApiCaseExecutionStep.objects.db_manager(self.alias)
        now = timezone.now()
        old = traces.create(trace_id='AUTO_old', source_type=1, case_id=1, test_suite_detail_id=80,
                            started_at=now - timedelta(minutes=10), status=TaskEnum.PROCEED.value)
        active = traces.create(trace_id='AUTO_current', source_type=1, case_id=1, test_suite_detail_id=80,
                               started_at=now, status=TaskEnum.PROCEED.value)
        unrelated = traces.create(trace_id='AUTO_other', source_type=1, case_id=1, test_suite_detail_id=81,
                                  started_at=now, status=TaskEnum.PROCEED.value)
        running = steps.create(trace=active, step_key='AUTO_post', step_type='case_posterior',
                               step_name='后置函数', started_at=now, status=TaskEnum.PROCEED.value)
        passed = steps.create(trace=active, step_key='AUTO_request', step_type='request',
                              step_name='原请求', started_at=now, status=TaskEnum.SUCCESS.value)
        control = {'phase': 'infrastructure_blocked', 'attempt': 2, 'requires_review': True}
        with patch.object(ApiCaseExecutionTrace, 'objects', traces), patch.object(ApiCaseExecutionStep, 'objects', steps):
            ApiCaseExecutionTraceRecorder.interrupt_report_attempt(80, now, '执行中断', control)
        for row in (old, active, unrelated, running, passed):
            row.refresh_from_db(using=self.alias)
        self.assertEqual((old.status, unrelated.status), (TaskEnum.PROCEED.value, TaskEnum.PROCEED.value))
        self.assertEqual((active.status, running.status, passed.status),
                         (TaskEnum.FAIL.value, TaskEnum.FAIL.value, TaskEnum.SUCCESS.value))
        self.assertIsNotNone(active.finished_at)
        self.assertIsNotNone(running.finished_at)
        self.assertEqual(active.summary['execution_control'], control)

    def test_partial_passed_snapshot_does_not_turn_interrupted_report_into_success(self):
        from src.apps.test_center.services.reporting.test_suite.summary import TestSuiteSummaryService
        self.add_cases(1)
        command = self.claim()
        self.details.filter(id=command.test_suite_details).update(
            case_sum=2, summary_data={'children': [{'status': 1}], 'meta': {}})
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        counter = TestSuiteSummaryService.counter_data(self.suite.id)
        self.assertEqual((counter['success'], counter['fail'], counter['proceed']), (0, 2, 0))

    def test_interrupted_notice_uses_normal_idempotent_delivery_without_unlocking_retry(self):
        from src.apps.test_center.services.reporting.test_suite.send_notice import SendNotice
        from src.apps.system.enums import TestSuiteNoticeEnum
        self.add_cases(1)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        suite = self.suites.get(id=self.suite.id)
        from src.apps.task_center.models import Tasks
        suite.tasks = Tasks(id=1, task_group_id=None, is_notice=1, fail_notice=1, notice_group_id=9)
        notice = SendNotice.__new__(SendNotice)
        notice.test_suite = suite
        with patch('src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroupExecutionService.complete_test_suite', return_value=False), \
                patch('src.apps.test_center.services.reporting.test_suite.send_notice.NoticeMain') as sender:
            notice.send_test_suite()
            notice.send_test_suite()
        sender.return_value.notice_main.assert_called_once_with(self.suite.id)
        self.assertEqual(self.suites.get(id=self.suite.id).is_notice, TestSuiteNoticeEnum.SENT.value)
        row = self.details.get(id=command.test_suite_details)
        self.assertTrue(row.summary_data['meta']['execution_control']['requires_review'])

    def test_blocked_review_still_requires_clean_resources_and_cannot_exclude(self):
        from src.apps.test_center.services.reporting.test_suite.disposition import TestSuiteDispositionService as Disposition
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        from src.apps.test_center.exceptions import TestCenterError
        self.add_cases(1)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        with patch('src.apps.test_center.services.reporting.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=True), \
                patch.object(DatasourceInfrastructureService, 'review_ready', return_value=False):
            with self.assertRaises(TestCenterError):
                Disposition.update.__wrapped__(Disposition, command.test_suite_details,
                    {'failure_reason': 'platform', 'failure_description': '已核查'}, user=SimpleNamespace(id=7))
        with patch('src.apps.test_center.services.reporting.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=True):
            with self.assertRaises(TestCenterError):
                Disposition.update.__wrapped__(Disposition, command.test_suite_details,
                    {'is_excluded': True}, user=SimpleNamespace(id=7))
        row = self.details.get(id=command.test_suite_details)
        self.assertTrue(row.summary_data['meta']['execution_control']['requires_review'])
        self.assertFalse(row.is_excluded)

    def test_retry_rechecks_resource_safety_and_same_attempt_after_review(self):
        from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        from src.apps.test_center.exceptions import TestCenterError
        self.add_cases(1)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        row = self.details.get(id=command.test_suite_details)
        with patch.object(DatasourceInfrastructureService, 'review_ready') as review_ready:
            with self.assertRaises(TestCenterError) as raised:
                TestSuiteRetryService.ensure_infrastructure_reviewed(row)
            self.assertEqual(raised.exception.code, 40107)
            self.assertIn('填写核查说明并保存', raised.exception.msg)
            self.assertNotIn('请先停止报告', raised.exception.msg)
            review_ready.assert_not_called()
        row.summary_data['meta']['execution_control']['requires_review'] = False
        with patch.object(DatasourceInfrastructureService, 'review_ready', return_value=False):
            with self.assertRaises(TestCenterError) as raised:
                TestSuiteRetryService.ensure_infrastructure_reviewed(row)
            self.assertEqual(raised.exception.code, 40109)
            self.assertIn('数据清理或数据源配额核查未通过', raised.exception.msg)
        with patch.object(DatasourceInfrastructureService, 'review_ready', return_value=True):
            TestSuiteRetryService.ensure_infrastructure_reviewed(row)
            row.retry += 1
            with self.assertRaises(TestCenterError) as raised:
                TestSuiteRetryService.ensure_infrastructure_reviewed(row)
            self.assertEqual(raised.exception.code, 40108)
            self.assertIn('执行轮次', raised.exception.msg)

    def test_review_then_retry_reuses_original_report_and_only_resets_target(self):
        from src.apps.test_center.services.reporting.test_suite.disposition import TestSuiteDispositionService as Disposition
        from src.apps.test_center.services.reporting.test_suite.retry import TestSuiteRetryService as Retry
        from src.apps.data_factory.services.governance.infrastructure import DatasourceInfrastructureService
        self.add_cases(2)
        commands = [self.claim(), self.claim()]
        first_id, second_id = [command.test_suite_details for command in commands]
        Infrastructure.block(first_id, commands[0].attempt, [])
        self.details.filter(id=second_id).update(status=TaskEnum.SUCCESS.value, success=1)
        with patch('src.apps.test_center.services.reporting.test_suite.disposition.PermissionMenuService.is_effective_super_admin', return_value=True), \
                patch.object(DatasourceInfrastructureService, 'review_ready', return_value=True), \
                patch.object(Retry, 'refresh_current_api_release'), \
                patch('src.apps.test_center.services.reporting.test_suite.retry.TestSuiteExecutionResultService.clear_result') as clear:
            Disposition.update.__wrapped__(Disposition, first_id,
                {'failure_reason': 'platform', 'failure_description': '已核查旧执行与全部清理结果'},
                user=SimpleNamespace(id=7))
            Retry.retry_detail.__wrapped__(Retry, first_id)
        first, second = self.details.get(id=first_id), self.details.get(id=second_id)
        self.assertEqual(first.test_suite_id, self.suite.id)
        self.assertEqual(first.status, TaskEnum.STAY_BEGIN.value)
        self.assertIsNone(first.summary_data)
        self.assertEqual((second.status, second.success), (TaskEnum.SUCCESS.value, 1))
        self.assertEqual(self.suites.count(), 1)
        self.assertEqual(self.details.count(), 2)
        clear.assert_called_once_with([first_id])

    def test_late_recovery_summary_cannot_erase_unknown_result_review_fence(self):
        from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService
        self.add_cases(1)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        row = self.details.get(id=command.test_suite_details)
        TestSuiteExecutionResultService.save_detail_summary(row, [{'status': 1}], {})
        row.refresh_from_db(using=self.alias)
        self.assertTrue(Infrastructure.is_blocked(row.summary_data))
        self.assertTrue(row.summary_data['meta']['execution_control']['requires_review'])

    def test_stale_progress_object_cannot_erase_persisted_block(self):
        from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService as Results
        self.add_cases(1)
        command = self.claim()
        stale = self.details.get(id=command.test_suite_details)
        self.assertFalse(Infrastructure.is_blocked(stale.summary_data))
        Infrastructure.block(stale.id, command.attempt, [])
        Results.save_detail_summary(stale, [{'status': 1}], {})
        row = self.details.get(id=stale.id)
        self.assertTrue(Infrastructure.is_blocked(row.summary_data))
        self.assertTrue(row.summary_data['meta']['execution_control']['requires_review'])
        self.assertEqual(row.status, TaskEnum.FAIL.value)

    def test_lazy_summary_backfill_cannot_erase_block_or_termination(self):
        from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService as Results
        self.add_cases(1)
        command = self.claim()
        Infrastructure.block(command.test_suite_details, command.attempt, [])
        row = self.details.get(id=command.test_suite_details)
        row.summary_data['meta']['termination'] = {'reason': 'timeout'}
        row.save(update_fields=['summary_data'])
        Results.save_detail_summary_by_id(
            row.id, [{'status': 1}], {'execution_control': {}}, expected_attempt=row.retry,
        )
        row.refresh_from_db(using=self.alias)
        self.assertTrue(Infrastructure.is_blocked(row.summary_data))
        self.assertEqual(row.summary_data['meta']['termination'], {'reason': 'timeout'})

    def test_late_summary_from_old_attempt_does_not_overwrite_new_attempt(self):
        from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService as Results
        self.add_cases(1)
        command = self.claim()
        stale = self.details.get(id=command.test_suite_details)
        self.details.filter(id=stale.id).update(retry=2, summary_data={'children': [], 'meta': {'new_attempt': True}})
        self.assertFalse(Results.save_detail_summary(stale, [{'status': 1}], {}))
        self.assertTrue(self.details.get(id=stale.id).summary_data['meta']['new_attempt'])

    def test_old_attempt_backfill_cannot_overwrite_new_attempt(self):
        from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService as Results
        self.add_cases(1)
        command = self.claim()
        self.details.filter(id=command.test_suite_details).update(retry=2, summary_data={'children': [], 'meta': {'new_attempt': True}})
        for expected_attempt in (command.attempt, None):
            self.assertFalse(Results.save_detail_summary_by_id(
                command.test_suite_details, [{'status': 1}], {}, expected_attempt=expected_attempt,
            ))
        self.assertTrue(self.details.get(id=command.test_suite_details).summary_data['meta']['new_attempt'])

    def test_old_attempt_payload_is_rejected_before_creating_latest_result(self):
        from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService as Results
        self.add_cases(1)
        command = self.claim()
        stale = self.details.get(id=command.test_suite_details)
        self.details.filter(id=stale.id).update(retry=2)
        with patch.object(Results, 'create_latest_result') as create_result:
            self.assertIsNone(Results._save_result_and_summary(
                stale, [], [], {}, prepared_result_payload={},
            ))
        create_result.assert_not_called()

import threading
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import close_old_connections, connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_pytest.models import PytestCase, PytestProduct
from src.apps.auto_ui.services.test_case.case_flow import UiCaseFlow
from src.apps.task_center.api.serializers.tasks import TasksSerializers
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum
from src.apps.task_center.enums.execution import (
    AutomationExecutionSceneEnum,
    AutomationExecutionScopeEnum,
)
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.models import Tasks, TasksDetails, TimeTasks
from src.apps.task_center.selectors.querysets import TaskCenterQuerySelector
from src.apps.task_center.services.execution.add_tasks import AddTasks
from src.apps.task_center.services.execution.claim import ApiTaskClaimService
from src.apps.task_center.services.scheduling.consumer import ScheduleFireConsumer
from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService
from src.apps.task_center.services.scheduling.fire import ScheduleFireService
from src.apps.task_center.services.scheduling.system_job import SystemJobService
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import Project, ProjectProduct, TestSuite, TestSuiteDetails
from src.apps.user.models import User
from src.processes.api_worker.runner import ApiWorkerRunner
from src.processes.scheduler.runner import ScheduleRunner
from src.processes.scheduler.system_jobs import SchedulerSystemJobService


class ApiTaskClaimServiceTests(TestCase):
    def setUp(self):
        release_patcher = patch.object(
            ApiCaseRevisionService,
            'resolve_current_published',
            side_effect=lambda case_id: SimpleNamespace(
                case_revision_id=case_id * 10,
                case_release_id=case_id * 100,
                checksum=f'checksum-{case_id}',
            ),
        )
        release_patcher.start()
        self.addCleanup(release_patcher.stop)
        project = Project.objects.create(name='报告并发测试项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.user = User.objects.create(
            name='报告并发测试用户',
            username='suite_claim_user',
            password='pwd',
        )
        self.suite_one = self.create_suite(10001, 1)
        self.suite_two = self.create_suite(10002, 2)
        self.details = [
            self.create_detail(self.suite_one, 1),
            self.create_detail(self.suite_one, 2),
            self.create_detail(self.suite_two, 3),
            self.create_detail(self.suite_two, 4),
        ]

    def create_suite(self, suite_id: int, limit: int, test_env: int = 0):
        return TestSuite.objects.create(
            id=suite_id,
            project_product=self.product,
            test_env=test_env,
            user=self.user,
            status=TaskEnum.STAY_BEGIN.value,
            is_notice=0,
            api_concurrency_limit=limit,
        )

    def create_detail(self, suite: TestSuite, case_id: int):
        return TestSuiteDetails.objects.create(
            test_suite=suite,
            type=TestCaseTypeEnum.API.value,
            project_product=self.product,
            test_env=suite.test_env,
            case_id=case_id,
            case_name=f'用例{case_id}',
            status=TaskEnum.STAY_BEGIN.value,
            retry=0,
        )

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=3)
    def test_claim_obeys_report_limit_and_uses_other_report_capacity(self, _mock_limit):
        first = ApiTaskClaimService.claim()
        second = ApiTaskClaimService.claim()
        third = ApiTaskClaimService.claim()
        fourth = ApiTaskClaimService.claim()

        self.assertEqual(first.test_suite, self.suite_one.id)
        self.assertEqual(second.test_suite, self.suite_two.id)
        self.assertEqual(third.test_suite, self.suite_two.id)
        self.assertIsNone(fourth)
        self.assertEqual(
            TestSuiteDetails.objects.filter(
                test_suite=self.suite_one,
                status=TaskEnum.PROCEED.value,
            ).count(),
            1,
        )
        self.assertEqual(
            TestSuiteDetails.objects.filter(
                test_suite=self.suite_two,
                status=TaskEnum.PROCEED.value,
            ).count(),
            2,
        )

    def test_candidate_suites_use_creation_time_instead_of_running_count(self):
        now = timezone.now()
        TestSuiteDetails.objects.filter(id=self.details[0].id).update(
            status=TaskEnum.PROCEED.value,
            push_time=now,
        )

        candidate_ids = ApiTaskClaimService.candidate_suite_ids(
            now - timedelta(seconds=1800),
        )

        self.assertEqual(candidate_ids, [self.suite_one.id, self.suite_two.id])

    def test_candidate_environment_order_is_reverse_display_order_with_two_queries(self):
        TestSuiteDetails.objects.all().update(status=TaskEnum.SUCCESS.value)
        suite_ids = []
        now = timezone.now()
        for index, environment in enumerate(EnvironmentEnum.default_obj()):
            suite = self.create_suite(20000 + index, 1, environment)
            detail = self.create_detail(suite, 100 + index)
            TestSuiteDetails.objects.filter(id=detail.id).update(
                create_time=now + timedelta(minutes=index),
            )
            suite_ids.append(suite.id)

        with self.assertNumQueries(2):
            candidates = ApiTaskClaimService.candidate_suite_ids(
                now - timedelta(hours=1), max_attempts=3,
            )

        self.assertEqual(candidates, list(reversed(suite_ids)))

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=3)
    def test_production_is_claimed_first_until_report_concurrency_limit(self, _mock_limit):
        TestSuiteDetails.objects.filter(test_suite=self.suite_one).update(test_env=EnvironmentEnum.DEV.value)
        TestSuiteDetails.objects.filter(test_suite=self.suite_two).update(test_env=EnvironmentEnum.PRO.value)

        claims = [ApiTaskClaimService.claim() for _ in range(4)]

        self.assertEqual(
            [item.test_suite if item else None for item in claims],
            [self.suite_two.id, self.suite_two.id, self.suite_one.id, None],
        )

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=3)
    def test_api_claim_uses_creation_time_even_when_detail_ids_are_reversed(self, _mock_limit):
        TestSuiteDetails.objects.filter(id=self.details[1].id).update(
            create_time=timezone.now() - timedelta(days=1),
        )

        claimed = ApiTaskClaimService.claim()

        self.assertEqual(claimed.test_suite_details, self.details[1].id)

    @patch('src.apps.auto_ui.services.test_case.case_flow.SystemConfigService.get_test_suite_timeout_max_attempts',
           return_value=3)
    def test_ui_claim_uses_environment_then_creation_time(self, _max_attempts):
        TestSuiteDetails.objects.all().update(type=TestCaseTypeEnum.UI.value)
        TestSuiteDetails.objects.filter(test_suite=self.suite_one).update(test_env=EnvironmentEnum.DEV.value)
        TestSuiteDetails.objects.filter(test_suite=self.suite_two).update(test_env=EnvironmentEnum.PRO.value)
        TestSuiteDetails.objects.filter(id=self.details[3].id).update(
            create_time=timezone.now() - timedelta(hours=1),
        )
        TestSuiteDetails.objects.filter(id=self.details[0].id).update(
            create_time=timezone.now() - timedelta(days=1),
        )

        claims = [UiCaseFlow.claim_case()[0].test_suite_details for _ in range(4)]

        self.assertEqual(claims, [self.details[index].id for index in (3, 2, 0, 1)])

    @patch('src.apps.auto_ui.services.test_case.case_flow.SystemConfigService.get_test_suite_timeout_max_attempts',
           return_value=3)
    def test_ui_priority_does_not_bypass_status_retry_or_type_filters(self, _max_attempts):
        TestSuiteDetails.objects.all().update(test_env=EnvironmentEnum.PRO.value)
        TestSuiteDetails.objects.filter(id=self.details[0].id).update(
            type=TestCaseTypeEnum.UI.value, status=TaskEnum.SUCCESS.value,
        )
        TestSuiteDetails.objects.filter(id=self.details[1].id).update(
            type=TestCaseTypeEnum.UI.value, retry=3,
        )
        TestSuiteDetails.objects.filter(id=self.details[3].id).update(
            type=TestCaseTypeEnum.UI.value, test_env=EnvironmentEnum.DEV.value,
        )

        self.assertEqual(UiCaseFlow.claim_case()[0].test_suite_details, self.details[3].id)
        self.assertIsNone(UiCaseFlow.claim_case())

    def test_candidate_suites_include_timed_out_details(self):
        now = timezone.now()
        TestSuiteDetails.objects.all().update(status=TaskEnum.SUCCESS.value)
        TestSuiteDetails.objects.filter(id=self.details[0].id).update(
            status=TaskEnum.PROCEED.value,
            push_time=now - timedelta(seconds=1801),
        )

        candidate_ids = ApiTaskClaimService.candidate_suite_ids(
            now - timedelta(seconds=1800),
        )

        self.assertEqual(candidate_ids, [self.suite_one.id])

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=3)
    def test_claim_uses_revision_already_pinned_on_report_detail(self, _mock_limit):
        detail = self.details[0]
        with connection.constraint_checks_disabled():
            TestSuiteDetails.objects.filter(id=detail.id).update(
                api_case_revision_id=777,
                api_case_release_id=None,
                config_checksum='editing-checksum',
            )
            try:
                with patch.object(
                        ApiCaseRevisionService,
                        'resolve_revision',
                        return_value=SimpleNamespace(
                            case_revision_id=777,
                            case_release_id=None,
                            checksum='editing-checksum',
                        ),
                ) as resolve_revision:
                    claimed = ApiTaskClaimService.claim()

                resolve_revision.assert_called_once_with(
                    detail.case_id,
                    777,
                    release_id=None,
                )
                self.assertEqual(claimed.case_revision_id, 777)
                self.assertIsNone(claimed.case_release_id)
            finally:
                TestSuiteDetails.objects.filter(id=detail.id).update(
                    api_case_revision_id=None,
                    config_checksum=None,
                )


class ScheduledTaskEnvironmentTests(SimpleTestCase):
    def test_environment_override_and_default(self):
        self.assertEqual(ScheduleDispatchService.resolve_test_env(None, 0), 0)
        self.assertEqual(ScheduleDispatchService.resolve_test_env('4', 0), 4)

    def test_invalid_environment_is_rejected(self):
        for value in (True, 1.5, 99, 'invalid'):
            with self.subTest(value=value), self.assertRaises(TaskCenterError):
                ScheduleDispatchService.resolve_test_env(value, 0)

    def test_case_types_are_deduplicated_and_sorted(self):
        self.assertEqual(
            ScheduledTaskCaseSelectionService.normalize_case_types([2, 0, 2, 1]),
            [0, 1, 2],
        )
        self.assertEqual(ScheduledTaskCaseSelectionService.normalize_case_types([]), [])

    def test_other_automation_type_is_rejected(self):
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.normalize_case_types([TestCaseTypeEnum.OTHER.value])

    def test_unsupported_production_dynamic_scene_is_rejected(self):
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environment_rule(
                execution_scenes=[AutomationExecutionSceneEnum.EFFECTIVENESS_TEST.value],
                execution_scope=AutomationExecutionScopeEnum.FULL_PRODUCT.value,
                test_env=EnvironmentEnum.PRO.value,
            )

    def test_production_inspection_dynamic_scene_is_allowed(self):
        ScheduledTaskCaseSelectionService.validate_environment_rule(
            execution_scenes=[AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value],
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
            test_env=EnvironmentEnum.PRO.value,
        )


class ScheduledTaskEmptyCaseValidationTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='空定时任务校验项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.user = User.objects.create(
            name='空定时任务校验用户',
            username='empty_scheduled_task_user',
            password='pwd',
        )
        self.timing = TimeTasks.objects.create(name='空任务校验策略', cron='0 10 * * *')
        self.task = Tasks.objects.create(
            project_product=self.product,
            test_envs=[0],
            name='未绑定用例的任务',
            case_people=self.user,
            status=0,
        )
        self.task.timing_strategies.add(self.timing)

    def test_new_task_cannot_be_created_enabled(self):
        serializer = TasksSerializers(data={
            'project_product': self.product.id,
            'test_envs': [0],
            'name': '直接启用的空任务',
            'case_people': self.user.id,
            'status': 1,
            'timing_strategies': [self.timing.id],
        })

        with self.assertRaises(TaskCenterError):
            serializer.is_valid()

    def test_empty_task_cannot_be_enabled(self):
        serializer = TasksSerializers(
            instance=self.task,
            data={'status': 1},
            partial=True,
        )

        with self.assertRaises(TaskCenterError):
            serializer.is_valid()

        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 0)

    def test_empty_task_cannot_create_report(self):
        with self.assertRaises(TaskCenterError):
            ScheduleDispatchService.create_test_suite(self.task)

        self.assertFalse(TestSuite.objects.filter(tasks=self.task).exists())

    def test_scheduled_empty_task_is_skipped_without_report(self):
        fire = ScheduleFire.objects.create(
            fire_key='empty-task:scheduled-fire',
            time_task=self.timing,
            task=self.task,
            task_name=self.task.name,
            planned_at=timezone.now(),
            fired_at=timezone.now(),
            status=ScheduleFireStatusEnum.DISPATCHING.value,
        )

        test_suite_id = ScheduleDispatchService.dispatch_fire(fire, 'test-node')

        fire.refresh_from_db()
        self.assertIsNone(test_suite_id)
        self.assertEqual(fire.status, ScheduleFireStatusEnum.SKIPPED.value)
        self.assertIn('尚未绑定任何有效用例', fire.error_message)
        self.assertFalse(TestSuite.objects.filter(tasks=self.task).exists())

    def test_status_repair_marks_empty_report_failed(self):
        report = TestSuite.objects.create(
            id=30002,
            project_product=self.product,
            test_env=0,
            user=self.user,
            tasks=self.task,
            status=TaskEnum.STAY_BEGIN.value,
            is_notice=0,
        )

        SchedulerSystemJobService.repair_test_suite_status.__wrapped__(SchedulerSystemJobService)

        report.refresh_from_db()
        self.assertEqual(report.status, TaskEnum.FAIL.value)


class ScheduleFireStatusTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='触发状态测试项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.user = User.objects.create(
            name='触发状态测试用户',
            username='schedule_fire_status_user',
            password='pwd',
        )
        self.suite = TestSuite.objects.create(
            id=30001,
            project_product=self.product,
            test_env=0,
            user=self.user,
            status=TaskEnum.FAIL.value,
            is_notice=0,
        )
        self.fire = ScheduleFire.objects.create(
            fire_key='test-suite:30001',
            task_name='定时执行失败报告',
            planned_at=timezone.now(),
            fired_at=timezone.now(),
            status=ScheduleFireStatusEnum.DISPATCHED.value,
            test_suite=self.suite,
        )

    @patch('src.processes.api_worker.runner.set_current_worker_db_context')
    @patch('src.processes.api_worker.runner.connection.close')
    @patch('src.processes.api_worker.runner.TestCase')
    def test_report_failure_does_not_overwrite_dispatched_fire(
            self,
            test_case_mock,
            _connection_close_mock,
            _set_context_mock,
    ):
        db_context = SimpleNamespace(close_idle=lambda: None)
        runner = ApiWorkerRunner.__new__(ApiWorkerRunner)
        runner.db_context_registry = SimpleNamespace(current=lambda: db_context)
        test_case_mock.return_value.test_case.return_value = False
        case_model = SimpleNamespace(
            user_id=self.user.id,
            test_env=0,
            case_id=1,
            test_suite=self.suite.id,
            test_suite_details=1,
            case_revision_id=1,
            case_release_id=1,
            config_checksum='checksum',
            parametrize=None,
        )

        runner.execute(case_model)

        self.fire.refresh_from_db()
        self.assertEqual(self.fire.status, ScheduleFireStatusEnum.DISPATCHED.value)

    def test_stale_dispatching_fire_without_report_is_requeued(self):
        stale_fire = ScheduleFire.objects.create(
            fire_key='test-suite:stale-pending',
            task_name='超时待恢复任务',
            planned_at=timezone.now(),
            fired_at=timezone.now(),
            status=ScheduleFireStatusEnum.DISPATCHING.value,
        )
        ScheduleFire.objects.filter(id=stale_fire.id).update(
            update_time=timezone.now() - timedelta(minutes=31),
        )

        result = ScheduleDispatchService.recover_stale_dispatching_fires('recovery-node')

        stale_fire.refresh_from_db()
        self.assertEqual(result['recovered_count'], 1)
        self.assertEqual(stale_fire.status, ScheduleFireStatusEnum.PENDING.value)
        self.assertIsNone(stale_fire.dispatcher_node)
        self.assertEqual(stale_fire.extra_data['dispatch_recovery_count'], 1)

    def test_stale_dispatching_fire_with_report_is_repaired_as_dispatched(self):
        stale_fire = ScheduleFire.objects.create(
            fire_key='test-suite:stale-dispatched',
            task_name='已创建报告的超时任务',
            planned_at=timezone.now(),
            fired_at=timezone.now(),
            status=ScheduleFireStatusEnum.DISPATCHING.value,
            test_suite=self.suite,
        )
        ScheduleFire.objects.filter(id=stale_fire.id).update(
            update_time=timezone.now() - timedelta(minutes=31),
        )

        result = ScheduleDispatchService.recover_stale_dispatching_fires('recovery-node')

        stale_fire.refresh_from_db()
        self.assertEqual(result['dispatched_count'], 1)
        self.assertEqual(stale_fire.status, ScheduleFireStatusEnum.DISPATCHED.value)
        self.assertEqual(stale_fire.dispatcher_node, 'recovery-node')

    def test_stale_dispatching_fire_stops_after_max_recoveries(self):
        stale_fire = ScheduleFire.objects.create(
            fire_key='test-suite:stale-failed',
            task_name='多次超时任务',
            planned_at=timezone.now(),
            fired_at=timezone.now(),
            status=ScheduleFireStatusEnum.DISPATCHING.value,
            extra_data={'dispatch_recovery_count': 3},
        )
        ScheduleFire.objects.filter(id=stale_fire.id).update(
            update_time=timezone.now() - timedelta(minutes=31),
        )

        result = ScheduleDispatchService.recover_stale_dispatching_fires('recovery-node')

        stale_fire.refresh_from_db()
        self.assertEqual(result['failed_count'], 1)
        self.assertEqual(stale_fire.status, ScheduleFireStatusEnum.FAIL.value)
        self.assertEqual(stale_fire.extra_data['dispatch_recovery_count'], 4)

    def test_duplicate_test_suite_fire_does_not_break_outer_transaction(self):
        planned_at = timezone.now().replace(second=0, microsecond=0)
        time_task = TimeTasks.objects.create(name='重复触发事务测试', cron='* * * * *')
        task = Tasks.objects.create(
            project_product=self.product,
            test_envs=[0],
            name='重复触发任务',
            case_people=self.user,
        )

        first_fire, first_created = ScheduleFireService.create_test_suite_fire(
            task, time_task, 0, planned_at,
        )
        duplicate_fire, duplicate_created = ScheduleFireService.create_test_suite_fire(
            task, time_task, 0, planned_at,
        )

        self.assertTrue(first_created)
        self.assertIsNotNone(first_fire)
        self.assertFalse(duplicate_created)
        self.assertIsNone(duplicate_fire)
        self.assertTrue(ScheduleFire.objects.filter(id=first_fire.id).exists())

    def test_duplicate_system_fire_does_not_break_outer_transaction(self):
        planned_at = timezone.now().replace(second=0, microsecond=0)
        kwargs = {
            'source_type': ScheduleFireSourceTypeEnum.SYSTEM_JOB.value,
            'business_key': 'transaction-savepoint-test',
            'task_name': '系统任务重复触发测试',
            'planned_at': planned_at,
        }

        first_fire, first_created = ScheduleFireService.create_system_fire(**kwargs)
        duplicate_fire, duplicate_created = ScheduleFireService.create_system_fire(**kwargs)

        self.assertTrue(first_created)
        self.assertIsNotNone(first_fire)
        self.assertFalse(duplicate_created)
        self.assertIsNone(duplicate_fire)
        self.assertTrue(ScheduleFire.objects.filter(id=first_fire.id).exists())


class ScheduleFireConsumerTests(SimpleTestCase):
    def test_auth_risk_todo_job_replaces_api_only_expire_notice_job(self):
        auth_job = next(
            job for job in SystemJobService.JOBS
            if job.key == 'reconcile_auth_risk_todos'
        )

        self.assertEqual(auth_job.name, '授权风险代办同步')
        self.assertEqual(auth_job.cron, '*/3 * * * *')
        self.assertNotIn(
            'send_api_auth_expire_notice',
            [job.key for job in SystemJobService.JOBS],
        )

    def test_system_job_list_supports_pagination(self):
        with patch.object(SystemJobService, 'latest_fire_map', return_value={}):
            rows, total = SystemJobService.list_jobs(page=2, page_size=10)

        self.assertEqual(total, len(SystemJobService.JOBS))
        self.assertEqual(
            [row['key'] for row in rows],
            [job.key for job in SystemJobService.JOBS[10:20]],
        )

    def test_scheduler_uses_system_job_definition_as_single_source(self):
        runner = ScheduleRunner(node_name='system-job-node')
        planned_at = timezone.now().replace(second=0, microsecond=0)
        handler = MagicMock(return_value={'processed': 3})
        job = SimpleNamespace(
            key='test_cleanup_job',
            cron='7 4 * * *',
            source_type=ScheduleFireSourceTypeEnum.DATA_CLEANUP.value,
            handler=handler,
        )
        fire = SimpleNamespace(id=91)

        with (
            patch.object(SystemJobService, 'JOBS', [job]),
            patch.object(runner, 'is_due', side_effect=lambda cron, _planned_at: cron == job.cron),
            patch.object(
                ScheduleFireService,
                'create_data_cleanup_fire',
                return_value=(fire, True),
            ) as create_fire,
            patch.object(ScheduleFireService, 'mark_success') as mark_success,
        ):
            runner.run_due_system_jobs(planned_at)

        create_fire.assert_called_once_with(
            job_name=job.key,
            planned_at=planned_at,
            node_name='system-job-node',
        )
        handler.assert_called_once_with()
        mark_success.assert_called_once_with(
            fire.id,
            'system-job-node',
            extra_data={'processed': 3},
        )

    @patch.object(ScheduleDispatchService, 'recover_stale_dispatching_fires')
    @patch.object(ScheduleDispatchService, 'dispatch_fire')
    @patch.object(ScheduleDispatchService, 'claim_pending_fire')
    def test_consumer_claims_and_dispatches_fire(
            self,
            claim_pending_fire,
            dispatch_fire,
            recover_stale_dispatching_fires,
    ):
        stop_event = threading.Event()
        wakeup_event = threading.Event()
        fire = SimpleNamespace(id=19)
        claim_pending_fire.return_value = fire
        dispatch_fire.side_effect = lambda *_args: stop_event.set()
        consumer = ScheduleFireConsumer(
            'consumer-node',
            stop_event,
            wakeup_event,
            poll_interval=0,
        )

        consumer.run_forever()

        recover_stale_dispatching_fires.assert_called_once_with('consumer-node')
        claim_pending_fire.assert_called_once_with('consumer-node')
        dispatch_fire.assert_called_once_with(fire, 'consumer-node')

    @patch.object(ScheduleDispatchService, 'recover_stale_dispatching_fires')
    @patch.object(ScheduleDispatchService, 'dispatch_fire')
    @patch.object(ScheduleDispatchService, 'claim_pending_fire')
    def test_recovery_failure_does_not_block_normal_consumption(
            self,
            claim_pending_fire,
            dispatch_fire,
            recover_stale_dispatching_fires,
    ):
        stop_event = threading.Event()
        fire = SimpleNamespace(id=20)
        recover_stale_dispatching_fires.side_effect = RuntimeError('temporary recovery error')
        claim_pending_fire.return_value = fire
        dispatch_fire.side_effect = lambda *_args: stop_event.set()
        consumer = ScheduleFireConsumer(
            'consumer-node',
            stop_event,
            threading.Event(),
            poll_interval=0,
        )

        consumer.run_forever()

        claim_pending_fire.assert_called_once_with('consumer-node')
        dispatch_fire.assert_called_once_with(fire, 'consumer-node')

    def test_scheduler_tick_only_produces_and_wakes_consumer(self):
        runner = ScheduleRunner(node_name='producer-node', lookback_minutes=2)
        with (
            patch.object(runner, 'create_due_time_task_fires') as create_fires,
            patch.object(runner, 'run_due_system_jobs') as run_system_jobs,
        ):
            runner.tick()

        self.assertEqual(create_fires.call_count, 2)
        self.assertEqual(run_system_jobs.call_count, 2)
        self.assertTrue(runner.dispatch_wakeup_event.is_set())

    @patch(
        'src.processes.scheduler.runner.ScheduledTaskGroupExecutionService.try_finalize'
    )
    @patch(
        'src.processes.scheduler.runner.ScheduledTaskGroupExecutionService.prepare'
    )
    @patch.object(ScheduleFireService, 'create_test_suite_fire')
    @patch.object(ScheduleRunner, 'has_ui_auth_to_refresh', return_value=False)
    @patch.object(ScheduleRunner, 'has_api_auth_to_refresh', return_value=False)
    @patch.object(ScheduleRunner, 'is_due', return_value=True)
    @patch.object(TaskCenterQuerySelector, 'tasks')
    @patch.object(TaskCenterQuerySelector, 'time_tasks')
    def test_scheduler_creates_group_execution_for_grouped_tasks(
            self,
            time_task_objects,
            task_objects,
            _is_due,
            _has_api_auth,
            _has_ui_auth,
            create_fire,
            prepare_group,
            finalize_group,
    ):
        planned_at = timezone.now().replace(second=0, microsecond=0)
        time_task = SimpleNamespace(id=7, cron='0 18 * * *')
        group = SimpleNamespace(id=3, test_envs=[0, 2])
        group_tasks = [
            SimpleNamespace(id=11, task_group_id=3, task_group=group, test_envs=[0]),
            SimpleNamespace(id=12, task_group_id=3, task_group=group, test_envs=[0]),
        ]
        standalone_task = SimpleNamespace(
            id=13,
            task_group_id=None,
            task_group=None,
            test_envs=[1],
        )
        time_task_objects.return_value.filter.return_value = [time_task]
        task_objects.return_value.filter.return_value.select_related.return_value.distinct.return_value = [
            *group_tasks,
            standalone_task,
        ]
        prepare_group.side_effect = [
            (SimpleNamespace(id=31), []),
            (SimpleNamespace(id=32), []),
        ]
        runner = ScheduleRunner(node_name='scheduler-node')

        runner.create_due_time_task_fires(planned_at)

        create_fire.assert_called_once_with(
            standalone_task,
            time_task,
            1,
            planned_at,
            'scheduler-node',
        )
        self.assertEqual(prepare_group.call_count, 2)
        prepare_group.assert_any_call(
            group,
            time_task,
            group_tasks,
            0,
            planned_at,
            node_name='scheduler-node',
        )
        prepare_group.assert_any_call(
            group,
            time_task,
            group_tasks,
            2,
            planned_at,
            node_name='scheduler-node',
        )
        self.assertEqual(
            [call.args[0] for call in finalize_group.call_args_list],
            [31, 32],
        )


class ReportConcurrencySnapshotTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='报告快照测试项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.user = User.objects.create(
            name='报告快照测试用户',
            username='suite_snapshot_user',
            password='pwd',
        )
        self.pytest_product = PytestProduct.objects.create(
            project_product=self.product,
            name='快照测试Pytest产品',
            file_name='snapshot',
        )
        self.pytest_case = PytestCase.objects.create(
            project_product=self.pytest_product,
            case_people=self.user,
            name='快照测试用例',
            publication_status='published',
            file_name='test_snapshot.py',
            file_path='tests/test_snapshot.py',
            file_update_time=timezone.now(),
        )

    def bind_case(self, task: Tasks):
        TasksDetails.objects.create(
            task=task,
            type=TestCaseTypeEnum.PYTEST.value,
            pytest_case=self.pytest_case,
        )

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=5)
    def test_manual_batch_report_keeps_execution_name_and_limit(self, _mock_limit):
        add_tasks = AddTasks(
            project_product=self.product.id,
            test_env=0,
            is_notice=0,
            user_id=self.user.id,
            execution_name='订单主流程回归',
            api_concurrency_limit=2,
        )

        report = TestSuite.objects.get(id=add_tasks.test_suite_id)
        self.assertEqual(report.execution_name, '订单主流程回归')
        self.assertEqual(report.api_concurrency_limit, 2)
        self.assertIsNone(report.tasks_id)

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=5)
    def test_manual_task_override_only_updates_report_snapshot(self, _mock_limit):
        timing = TimeTasks.objects.create(name='每小时快照测试', cron='0 * * * *')
        task = Tasks.objects.create(
            project_product=self.product,
            test_envs=[0],
            name='定时回归',
            case_people=self.user,
            status=1,
            api_concurrency_limit=2,
        )
        task.timing_strategies.add(timing)
        self.bind_case(task)

        report_id = ScheduleDispatchService.create_test_suite(
            task,
            api_concurrency_limit=4,
            user_id=self.user.id,
        )

        report = TestSuite.objects.get(id=report_id)
        task.refresh_from_db()
        self.assertEqual(report.api_concurrency_limit, 4)
        self.assertEqual(report.tasks_id, task.id)
        self.assertIsNone(report.execution_name)
        self.assertEqual(task.api_concurrency_limit, 2)

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=5)
    def test_manual_task_environment_override_only_updates_report_snapshot(self, _mock_limit):
        timing = TimeTasks.objects.create(name='手动环境覆盖测试', cron='0 * * * *')
        task = Tasks.objects.create(
            project_product=self.product,
            test_envs=[0, 4],
            name='环境覆盖定时回归',
            case_people=self.user,
            status=1,
            api_concurrency_limit=2,
        )
        task.timing_strategies.add(timing)
        self.bind_case(task)

        report_id = ScheduleDispatchService.create_test_suite(
            task,
            api_concurrency_limit=2,
            user_id=self.user.id,
            test_env=4,
        )

        report = TestSuite.objects.get(id=report_id)
        task.refresh_from_db()
        self.assertEqual(report.test_env, 4)
        self.assertEqual(task.test_envs, [0, 4])

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=5)
    def test_manual_task_can_run_in_unconfigured_temporary_environment(self, _mock_limit):
        timing = TimeTasks.objects.create(name='临时环境覆盖测试', cron='0 * * * *')
        task = Tasks.objects.create(
            project_product=self.product,
            test_envs=[EnvironmentEnum.PRO.value],
            name='生产任务临时仿真执行',
            case_people=self.user,
            status=1,
            api_concurrency_limit=2,
        )
        task.timing_strategies.add(timing)
        self.bind_case(task)

        report_id = ScheduleDispatchService.create_test_suite(
            task,
            api_concurrency_limit=2,
            user_id=self.user.id,
            test_env=EnvironmentEnum.SIM.value,
            allow_unconfigured_test_env=True,
        )

        report = TestSuite.objects.get(id=report_id)
        task.refresh_from_db()
        self.assertEqual(report.test_env, EnvironmentEnum.SIM.value)
        self.assertEqual(task.test_envs, [EnvironmentEnum.PRO.value])

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=5)
    def test_scheduled_task_without_limit_uses_platform_snapshot(self, _mock_limit):
        timing = TimeTasks.objects.create(name='默认并发快照测试', cron='0 * * * *')
        task = Tasks.objects.create(
            project_product=self.product,
            test_envs=[0],
            name='平台默认并发定时回归',
            case_people=self.user,
            status=1,
            api_concurrency_limit=None,
        )
        task.timing_strategies.add(timing)
        self.bind_case(task)

        report_id = ScheduleDispatchService.create_test_suite(task)

        report = TestSuite.objects.get(id=report_id)
        self.assertEqual(report.api_concurrency_limit, 5)
        self.assertEqual(report.tasks_id, task.id)


class ApiTaskConcurrentClaimTests(TransactionTestCase):
    def setUp(self):
        release_patcher = patch.object(
            ApiCaseRevisionService,
            'resolve_current_published',
            side_effect=lambda case_id: SimpleNamespace(
                case_revision_id=case_id * 10,
                case_release_id=case_id * 100,
                checksum=f'checksum-{case_id}',
            ),
        )
        release_patcher.start()
        self.addCleanup(release_patcher.stop)
        project = Project.objects.create(name='并发抢占测试项目')
        self.product = ProjectProduct.objects.create(project=project, name='主服务')
        self.user = User.objects.create(
            name='并发抢占测试用户',
            username='concurrent_claim_user',
            password='pwd',
        )

    def create_suite(self, suite_id: int, limit: int):
        return TestSuite.objects.create(
            id=suite_id,
            project_product=self.product,
            test_env=0,
            user=self.user,
            status=TaskEnum.STAY_BEGIN.value,
            is_notice=0,
            api_concurrency_limit=limit,
        )

    def create_detail(self, suite: TestSuite, case_id: int):
        return TestSuiteDetails.objects.create(
            test_suite=suite,
            type=TestCaseTypeEnum.API.value,
            project_product=self.product,
            test_env=0,
            case_id=case_id,
            case_name=f'并发用例{case_id}',
            status=TaskEnum.STAY_BEGIN.value,
            retry=0,
        )

    @staticmethod
    def run_concurrent_claims():
        barrier = threading.Barrier(2)
        results = [None, None]
        errors = []

        def claim(index: int):
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                claimed = ApiTaskClaimService.claim()
                results[index] = claimed.test_suite_details if claimed else None
            except Exception as error:
                errors.append(error)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=claim, args=(index,)) for index in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        if any(thread.is_alive() for thread in threads):
            raise AssertionError('并发抢占测试线程未在预期时间内结束')
        if errors:
            raise errors[0]
        return results

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=1)
    def test_concurrent_claims_do_not_exceed_platform_limit_across_reports(self, _mock_limit):
        first_suite = self.create_suite(20001, 1)
        second_suite = self.create_suite(20002, 1)
        self.create_detail(first_suite, 1)
        self.create_detail(second_suite, 2)

        results = self.run_concurrent_claims()

        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(
            TestSuiteDetails.objects.filter(status=TaskEnum.PROCEED.value).count(),
            1,
        )

    @patch.object(ApiConcurrencyService, 'platform_limit', return_value=2)
    def test_concurrent_claims_do_not_exceed_single_report_limit(self, _mock_limit):
        suite = self.create_suite(20003, 1)
        self.create_detail(suite, 3)
        self.create_detail(suite, 4)

        results = self.run_concurrent_claims()

        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(
            TestSuiteDetails.objects.filter(
                test_suite=suite,
                status=TaskEnum.PROCEED.value,
            ).count(),
            1,
        )

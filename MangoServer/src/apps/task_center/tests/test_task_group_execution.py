import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.system.enums import TestSuiteNoticeEnum
from src.apps.task_center.enums import ScheduleFireStatusEnum
from src.apps.task_center.models import ScheduleFire
from src.apps.task_center.services.scheduling.task_group_execution import (
    ScheduledTaskGroupExecutionService,
)
from src.apps.task_center.services.scheduling.task_group_notice import (
    TaskGroupChildReport,
    TaskGroupNoticeBuilder,
    TaskGroupNoticeReport,
)


class ScheduledTaskGroupExecutionServiceTests(SimpleTestCase):
    def setUp(self):
        patcher = patch('src.apps.system.services.system_config.SystemConfigService.get_environment_display_names',
                        return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def fire(*, fire_status, suite_status=None):
        suite = None if suite_status is None else SimpleNamespace(status=suite_status)
        return SimpleNamespace(
            status=fire_status,
            test_suite_id=1 if suite else None,
            test_suite=suite,
        )

    def test_dispatch_failure_is_completed_and_failed(self):
        fire = self.fire(fire_status=ScheduleFireStatusEnum.FAIL.value)

        self.assertTrue(ScheduledTaskGroupExecutionService._fire_completed(fire))
        self.assertTrue(ScheduledTaskGroupExecutionService._fire_failed(fire))

    def test_skipped_generation_is_completed_and_failed(self):
        fire = self.fire(fire_status=ScheduleFireStatusEnum.SKIPPED.value)

        self.assertTrue(ScheduledTaskGroupExecutionService._fire_completed(fire))
        self.assertTrue(ScheduledTaskGroupExecutionService._fire_failed(fire))

    def test_running_suite_keeps_group_waiting(self):
        fire = self.fire(
            fire_status=ScheduleFireStatusEnum.DISPATCHED.value,
            suite_status=TaskEnum.PROCEED.value,
        )

        self.assertFalse(ScheduledTaskGroupExecutionService._fire_completed(fire))
        self.assertFalse(ScheduledTaskGroupExecutionService._fire_failed(fire))

    def test_stopped_suite_is_completed_and_failed(self):
        fire = self.fire(
            fire_status=ScheduleFireStatusEnum.DISPATCHED.value,
            suite_status=TaskEnum.STOPPED.value,
        )

        self.assertTrue(ScheduledTaskGroupExecutionService._fire_completed(fire))
        self.assertTrue(ScheduledTaskGroupExecutionService._fire_failed(fire))

    def test_generation_failure_is_excluded_from_group_report(self):
        now = datetime(2026, 9, 18, 22, 0, 0)
        execution = SimpleNamespace(
            id=17,
            task_group_name='生产巡检',
            expected_count=1,
            test_env=2,
            planned_at=now,
            create_time=now,
            finished_at=now,
            project_product=SimpleNamespace(
                name='WEB前端',
                project=SimpleNamespace(name='示例项目'),
            ),
        )
        failed_fire = SimpleNamespace(
            status=ScheduleFireStatusEnum.SKIPPED.value,
            test_suite_id=None,
            test_suite=None,
            task_name='【生产巡检】订单管理',
            task=None,
            update_time=now,
        )

        report = ScheduledTaskGroupExecutionService._build_report(
            execution,
            [failed_fire],
        )

        self.assertEqual(report.task_group_name, '生产巡检')
        self.assertEqual(report.task_count, 0)
        self.assertEqual(report.failed_task_count, 0)
        self.assertEqual(report.case_sum, 0)
        self.assertEqual(report.fail, 0)
        self.assertEqual(report.children, [])

    @patch(
        'src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroupExecution.objects'
    )
    @patch('src.apps.task_center.services.scheduling.task_group_execution.NoticeMain')
    @patch.object(ScheduledTaskGroupExecutionService, '_cleanup_finished_reports')
    def test_claimed_group_notice_is_sent_once(self, cleanup, notice_main, execution_objects):
        report = MagicMock()
        with patch.object(
                ScheduledTaskGroupExecutionService,
                '_claim_notice',
                side_effect=[{'notice_group_id': 9, 'report': report}, None],
        ):
            self.assertTrue(ScheduledTaskGroupExecutionService.try_finalize(11))
            self.assertFalse(ScheduledTaskGroupExecutionService.try_finalize(11))

        notice_main.assert_called_once_with(9)
        notice_main.return_value.notice_task_group.assert_called_once_with(report)
        execution_objects.filter.return_value.update.assert_called_once()


class EmptyTaskGroupBatchTests(SimpleTestCase):
    def test_new_batch_without_fires_is_discarded(self):
        execution = MagicMock()

        discarded = ScheduledTaskGroupExecutionService._discard_empty_execution(execution, True)

        self.assertTrue(discarded)
        execution.delete.assert_called_once()

    def test_existing_batch_without_new_fires_is_kept(self):
        execution = MagicMock()

        discarded = ScheduledTaskGroupExecutionService._discard_empty_execution(execution, False)

        self.assertFalse(discarded)
        execution.delete.assert_not_called()

    def test_empty_batch_is_finalized_instead_of_waiting(self):
        execution = MagicMock()
        execution.finished_at = None

        ScheduledTaskGroupExecutionService._finalize_empty_execution(execution)

        self.assertEqual(execution.status, TaskEnum.FAIL.value)
        self.assertIsNotNone(execution.finished_at)
        self.assertEqual(execution.notice_status, TestSuiteNoticeEnum.EXPIRED.value)
        execution.save.assert_called_once_with(update_fields=[
            'completed_count', 'status', 'finished_at', 'notice_status', 'update_time',
        ])


class ScheduleFireConstraintTests(SimpleTestCase):
    def test_cross_environment_fires_are_not_blocked_by_composite_unique_constraint(self):
        # 触发去重由带环境的 fire_key 负责；按任务与计划分钟建唯一约束会把第二个环境误判为重复。
        constraint_names = {constraint.name for constraint in ScheduleFire._meta.constraints}
        self.assertNotIn('uniq_schedule_fire_task_plan_type', constraint_names)


class TaskGroupNoticeBuilderTests(SimpleTestCase):
    def test_all_group_notice_titles_show_the_effective_result_icon(self):
        from dataclasses import replace
        for failed, icon, result in ((0, '✅', '通过'), (1, '❌', '失败')):
            with self.subTest(failed=failed):
                report = replace(self.report(), failed_task_count=failed, fail=failed, warning=0, warning_task_count=0)
                builder = TaskGroupNoticeBuilder(report)
                title = f'{icon}芒果测试平台任务组执行报告 - {result}'
                self.assertEqual(builder.build_title(), title)
                self.assertEqual(builder.build_feishu_card()['header']['title']['content'], title)
                self.assertTrue(builder.build_wechat_markdown().startswith(f'## {icon}芒果测试平台任务组执行报告'))
                self.assertIn(f'<h2>{icon}芒果测试平台任务组执行报告', builder.build_email_html())

    def report(self):
        return TaskGroupNoticeReport(
            execution_id=17,
            task_group_name='生产巡检',
            project_name='示例项目',
            product_name='WEB前端',
            test_environment='生产环境',
            planned_at='2026-09-18 22:00:00',
            execution_duration='01:28:03',
            task_count=2,
            completed_task_count=2,
            success_task_count=1,
            failed_task_count=1,
            warning_task_count=0,
            case_sum=212,
            success=210,
            fail=1,
            warning=1,
            success_rate=99.06,
            api_case_sum=212,
            api_fail=1,
            children=[
                TaskGroupChildReport(
                    task_name='【生产巡检】订单管理',
                    result='失败',
                    test_suite_id=597138979665,
                    case_sum=202,
                    success=200,
                    fail=1,
                    warning=1,
                ),
                TaskGroupChildReport(
                    task_name='【生产巡检】用户管理',
                    result='成功',
                    test_suite_id=123456789012,
                    case_sum=10,
                    success=10,
                ),
            ],
        )

    def test_feishu_card_uses_group_identity_and_contains_all_report_links(self):
        card = TaskGroupNoticeBuilder(
            self.report(),
            'https://example.com',
        ).build_feishu_card()
        payload = json.dumps(card, ensure_ascii=False)

        self.assertIn('任务组执行报告', payload)
        self.assertIn('**任务组：** 生产巡检', payload)
        self.assertIn('/#/report/system/details?id=597138979665', payload)
        self.assertIn('/#/report/system/details?id=123456789012', payload)
        self.assertIn('/#/report/index?group_execution_id=17', payload)
        self.assertNotIn('执行批次', payload)
        self.assertNotIn('**任务名称：**', payload)
        self.assertNotIn('**测试套ID：**', payload)

    def test_group_notice_text_formats_hide_execution_id(self):
        builder = TaskGroupNoticeBuilder(self.report(), 'https://example.com')

        self.assertNotIn('执行批次', builder.build_wechat_markdown())
        self.assertNotIn('执行批次', builder.build_email_html())
        self.assertIn('group_execution_id=17', builder.build_wechat_markdown())
        self.assertIn('group_execution_id=17', builder.build_email_html())

    def test_group_notice_uses_compact_labeled_statistics_across_channels(self):
        builder = TaskGroupNoticeBuilder(self.report(), 'https://example.com')
        card = builder.build_feishu_card()
        self.assertFalse(card['config']['wide_screen_mode'])
        self.assertFalse(any(item['tag'] == 'column_set' for item in card['elements']))
        metadata = card['elements'][0]['text']['content']
        self.assertIn('**测试环境：** 生产环境\n', metadata)
        self.assertIn('**计划时间：** 2026-09-18 22:00:00 · **耗时：** 01:28:03', metadata)
        stats = next(item['text']['content'] for item in card['elements']
                     if item.get('tag') == 'div' and '成功率' in item.get('text', {}).get('content', ''))
        self.assertNotIn('\n', stats)
        for label in ('成功率', '总用例', '成功', '失败', '告警用例', '已排除用例'):
            self.assertIn(f'**{label}：**', stats)
            self.assertIn(f'**{label}：**', builder.build_wechat_markdown())
            self.assertIn(f'<strong>{label}：</strong>', builder.build_email_html())
        self.assertIn('总用例：** 212 个', stats)

    def test_group_notice_uses_configured_platform_name(self):
        builder = TaskGroupNoticeBuilder(self.report(), 'https://example.com', '演示<&>平台')
        self.assertIn('演示<&>平台任务组执行报告', builder.build_feishu_card()['header']['title']['content'])
        self.assertIn('演示<&>平台任务组执行报告', builder.build_wechat_markdown())
        self.assertIn('演示&lt;&amp;&gt;平台任务组执行报告', builder.build_email_html())

    def test_feishu_child_reports_are_rendered_in_one_continuous_block(self):
        report = self.report()
        report = TaskGroupNoticeReport(**{
            **report.__dict__,
            'children': [
                TaskGroupChildReport(task_name=f'子任务{index}', result='成功')
                for index in range(17)
            ],
        })

        card = TaskGroupNoticeBuilder(report, 'https://example.com').build_feishu_card()
        child_blocks = [
            element['text']['content']
            for element in card['elements']
            if element.get('tag') == 'div'
               and '子任务0' in element.get('text', {}).get('content', '')
        ]

        self.assertEqual(len(child_blocks), 1)
        self.assertIn('子任务16', child_blocks[0])
        self.assertNotIn('\n\n', child_blocks[0])

    def test_group_card_does_not_expose_report_links_without_http_domain(self):
        payload = json.dumps(
            TaskGroupNoticeBuilder(self.report(), '请先配置域名').build_feishu_card(),
            ensure_ascii=False,
        )

        self.assertNotIn('/#/report/', payload)

    def test_historical_group_report_links_to_all_suite_ids(self):
        report = self.report()
        report = TaskGroupNoticeReport(**{
            **report.__dict__,
            'execution_id': None,
        })

        url = TaskGroupNoticeBuilder(report, 'https://example.com').group_report_url()

        self.assertEqual(
            url,
            'https://example.com/#/report/index?'
            'test_suite_ids=597138979665,123456789012',
        )

    @patch(
        'src.apps.task_center.services.scheduling.task_group_execution.ScheduledTaskGroupExecution.objects'
    )
    @patch('src.apps.task_center.services.scheduling.task_group_execution.NoticeMain')
    @patch.object(ScheduledTaskGroupExecutionService, '_cleanup_finished_reports')
    def test_three_completed_groups_trigger_three_aggregate_notices(
            self,
            cleanup,
            notice_main,
            execution_objects,
    ):
        reports = [MagicMock(name=f'group-{index}') for index in range(3)]
        payloads = [
            {'notice_group_id': 2, 'report': report}
            for report in reports
        ]
        with patch.object(
                ScheduledTaskGroupExecutionService,
                '_claim_notice',
                side_effect=payloads,
        ):
            for execution_id in (101, 102, 103):
                self.assertTrue(
                    ScheduledTaskGroupExecutionService.try_finalize(execution_id)
                )

        self.assertEqual(notice_main.call_count, 3)
        actual_reports = [
            call.args[0]
            for call in notice_main.return_value.notice_task_group.call_args_list
        ]
        self.assertEqual(actual_reports, reports)
        self.assertEqual(execution_objects.filter.return_value.update.call_count, 3)

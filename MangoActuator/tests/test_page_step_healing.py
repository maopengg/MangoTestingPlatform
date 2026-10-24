import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from mangoautomation.models import ElementModel
from mangoautomation.models import ElementResultModel
from mangoautomation.element_healing.snapshot import AccessibilitySnapshot, AccessibilitySnapshotNode
from mangoautomation.step_healing import (
    StepHealingResponseError,
    StepRepairPlan,
    StepRepairRejected,
)

from src.services.ui.step_healing.orchestrator import PageStepHealingOrchestrator
from src.services.ui.page_steps import PageSteps


class _TestData:
    def get_all(self):
        return {'template_name': 'demo'}


def page_step():
    element = ElementModel(
        id=11, element_id=21, type=0, name='Template name', sleep=None,
        ope_key='w_input', ope_value=[], precondition={}, postcondition={},
    )
    return SimpleNamespace(
        id=3, name='Create template', goal='Create and open a template', config_version=2,
        healing_enabled=True, healing_policy={'mode': 'execute_low_risk'},
        entry_criteria={}, success_criteria={}, element_list=[element], test_env=1,
        execution_id='dispatch-1',
    )


class PageStepHealingRuntimeTest(unittest.IsolatedAsyncioTestCase):
    def test_missing_cache_key_is_classified_as_runtime_data_dependency(self):
        kind = PageStepHealingOrchestrator._failure_kind(
            'node_failed',
            '无法获取缓存的key【搜索设置定位表达式】的值，请检查是否设置这个key',
        )

        self.assertEqual(kind, 'runtime_data_dependency_missing')

    def test_missing_cache_key_repair_cannot_retry_original_node(self):
        plan = StepRepairPlan.model_validate({
            'schema_version': 1,
            'diagnosis_code': 'missing_runtime_data',
            'diagnosis_summary': 'Original locator variable is unavailable',
            'confidence': .9,
            'actions': [{
                'action': 'retry_node', 'node_id': '11',
                'reason': 'retry original node',
            }],
            'user_message': 'retry',
        })

        with self.assertRaises(StepRepairRejected):
            PageStepHealingOrchestrator._validate_failure_plan(
                plan, 'runtime_data_dependency_missing',
            )

    def test_missing_cache_replacement_must_remove_original_node(self):
        plan = StepRepairPlan.model_validate({
            'schema_version': 1,
            'diagnosis_code': 'missing_runtime_data',
            'diagnosis_summary': 'Use a safe replacement action',
            'confidence': .95,
            'actions': [{
                'action': 'insert_action', 'operation_intent': 'activate',
                'target_ref': 'e1', 'reason': 'perform replacement',
            }],
            'user_message': 'recovered',
        })

        with self.assertRaisesRegex(StepRepairRejected, '必须移除'):
            PageStepHealingOrchestrator._validate_failure_plan(
                plan, 'runtime_data_dependency_missing',
            )

    async def test_protocol_error_is_fed_back_to_the_next_model_call(self):
        model = page_step()
        model.healing_policy = {
            'mode': 'execute_low_risk',
            'max_model_calls': 2,
        }
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), model, _TestData())
        snap = AccessibilitySnapshot(
            snapshot_id='snapshot01', page_url='https://example.com', created_at_ms=1,
            nodes=[AccessibilitySnapshotNode(
                ref='e1', frame_index=0, order=1, role='button', name='Search',
                tag='button', interactive=True,
            )],
        )
        state = SimpleNamespace(
            normalized_url_path='/', visible_text_digest='text',
            form_state_digest='form', matched_checkpoints=[],
            model_dump=lambda **_: {},
        )
        runtime.observer.snapshot = AsyncMock(return_value=(state, snap))
        runtime.planner.plan_async = AsyncMock(side_effect=[
            StepHealingResponseError('步骤自愈响应不符合协议：diagnosis_code:missing'),
            StepRepairRejected('stop after feedback'),
        ])

        with self.assertRaisesRegex(StepRepairRejected, 'stop after feedback'):
            await runtime._recover(
                model.element_list[0], 'missing cache key', [], {
                    'trace_id': 'trace-1', 'trigger': 'node_failed',
                    'source_version': 2, 'failed_node_id': '11',
                },
            )

        second_context = runtime.planner.plan_async.await_args_list[1].args[0]
        self.assertIn('diagnosis_code:missing', second_context['previous_response_error'])

    def test_model_timeout_has_readable_user_message(self):
        class APITimeoutError(Exception):
            pass

        message = PageStepHealingOrchestrator._failure_user_message(
            APITimeoutError('Request timed out.'),
        )

        self.assertEqual(message, '步骤AI请求超时，本次未执行修复，请稍后重试')

    def test_guard_rejection_keeps_the_real_reason(self):
        message = PageStepHealingOrchestrator._failure_user_message(
            StepRepairRejected('AI没有返回可执行的恢复动作'),
        )

        self.assertEqual(
            message,
            '步骤自愈未通过安全校验：AI没有返回可执行的恢复动作',
        )

    async def test_missing_cache_key_failure_is_still_escalated_to_step_healing(self):
        runner = PageSteps.__new__(PageSteps)
        element = page_step().element_list[0]
        runner.page_steps_model = SimpleNamespace(element_list=[element])
        runner.base_data = SimpleNamespace(page=object())
        runner._update_element_data = AsyncMock(return_value=element)
        failure = ElementResultModel(
            id=element.id,
            name=element.name,
            type=element.type,
            ope_key=element.ope_key,
            status=0,
            error_message=(
                '无法获取缓存的key【搜索设置定位表达式】的值，'
                '请检查是否设置这个key'
            ),
        )
        runner._ope_steps = AsyncMock(return_value=failure)
        runner._recover_step = AsyncMock(return_value=False)
        runner._record_element_result = AsyncMock()

        result = await runner.test_flow_data({'id': element.id, 'children': []})

        self.assertIs(result, failure)
        runner._recover_step.assert_awaited_once_with(
            failure, element, trigger='node_failed',
        )
        runner._record_element_result.assert_awaited_once_with(failure)

    def test_empty_node_checkpoint_does_not_participate_in_execution(self):
        self.assertFalse(PageSteps._has_condition_rules(None))
        self.assertFalse(PageSteps._has_condition_rules({}))
        self.assertFalse(PageSteps._has_condition_rules({'operator': 'all', 'conditions': []}))
        self.assertTrue(PageSteps._has_condition_rules({
            'operator': 'all',
            'conditions': [{'type': 'visible_text', 'matcher': 'contains', 'expected': 'ready'}],
        }))

    def test_node_map_contains_operation_and_risk(self):
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), page_step(), _TestData())
        self.assertEqual(runtime.node_map['11']['operation_intent'], 'edit')
        self.assertEqual(runtime.node_map['11']['risk_level'], 'low')
        self.assertEqual(runtime.node_map['11']['later_checkpoints'], ['success'])

    async def test_edit_action_uses_only_bound_test_data(self):
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), page_step(), _TestData())
        locator = SimpleNamespace(is_editable=AsyncMock(return_value=True), fill=AsyncMock())
        await runtime._operate(locator, 'edit', 'template_name')
        locator.fill.assert_awaited_once_with('demo')

    async def test_edit_action_can_use_text_explicitly_declared_by_step_goal(self):
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), page_step(), _TestData())
        locator = SimpleNamespace(is_editable=AsyncMock(return_value=True), fill=AsyncMock())

        await runtime._operate(locator, 'edit', None, 'demo query')

        locator.fill.assert_awaited_once_with('demo query')

    async def test_missing_cache_replacement_does_not_retry_broken_original_node(self):
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), page_step(), _TestData())
        plan = StepRepairPlan.model_validate({
            'schema_version': 1,
            'diagnosis_code': 'missing_runtime_data',
            'diagnosis_summary': 'Use a safe replacement action',
            'confidence': .95,
            'actions': [{
                'action': 'insert_action', 'operation_intent': 'activate',
                'target_ref': 'e1', 'reason': 'perform replacement',
            }],
            'user_message': 'recovered',
        })
        snap = AccessibilitySnapshot(
            snapshot_id='snapshot01', page_url='https://example.com', created_at_ms=1,
            nodes=[AccessibilitySnapshotNode(
                ref='e1', frame_index=0, order=1, role='button', name='Search',
                tag='button', interactive=True,
            )],
        )
        locator = SimpleNamespace(
            count=AsyncMock(return_value=1), is_visible=AsyncMock(return_value=True),
            click=AsyncMock(),
        )
        runtime._locator = lambda *_: locator

        outcome = await runtime._execute(
            plan, snap, page_step().element_list[0], {
                'trace_id': 'trace-1', 'trigger': 'node_failed',
                'source_version': 2, 'failed_node_id': '11',
            }, failure_kind='runtime_data_dependency_missing',
        )

        self.assertTrue(outcome.skip_current_node)
        self.assertFalse(outcome.retry_current_node)
        locator.click.assert_awaited_once()

    def test_insert_action_gets_durable_writeback_metadata(self):
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), page_step(), _TestData())
        plan = StepRepairPlan.model_validate({
            'schema_version': 1,
            'diagnosis_code': 'missing_step',
            'diagnosis_summary': 'missing next button',
            'confidence': .95,
            'actions': [{
                'action': 'insert_action', 'operation_intent': 'activate',
                'target_ref': 'e1', 'reason': 'continue',
            }],
            'user_message': 'recovered',
        })
        snapshot = AccessibilitySnapshot(
            snapshot_id='snapshot01', page_url='https://example.com', created_at_ms=1,
            nodes=[AccessibilitySnapshotNode(
                ref='e1', frame_index=0, order=1, role='button', name='Next',
                tag='button', interactive=True,
            )],
        )

        runtime._attach_writeback_targets(plan, snapshot, None, 'entry_criteria_mismatch')

        action = plan.actions[0]
        self.assertEqual(action.node_id, '11')
        self.assertEqual(action.placement, 'before')
        self.assertEqual(action.target_name, 'Next')
        self.assertEqual(action.durable_locators[0]['loc'], "get_by_role('button', name='Next', exact=True)")

    def test_dynamic_textbox_name_is_not_used_as_the_saved_element_name(self):
        model = page_step()
        current = model.element_list[0].model_copy(update={'name': '搜索设置'})
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), model, _TestData())
        plan = StepRepairPlan.model_validate({
            'schema_version': 1,
            'diagnosis_code': 'missing_runtime_data',
            'diagnosis_summary': 'replace missing locator variable',
            'confidence': .98,
            'actions': [{
                'action': 'insert_action', 'operation_intent': 'edit',
                'target_ref': 'e1', 'reason': '输入搜索内容',
            }],
            'user_message': 'recovered',
        })
        snapshot = AccessibilitySnapshot(
            snapshot_id='snapshot01', page_url='https://example.com', created_at_ms=1,
            nodes=[AccessibilitySnapshotNode(
                ref='e1', frame_index=0, order=1, role='textbox',
                name='动态推荐文字', placeholder='动态推荐文字', tag='textarea',
                attributes={'id': 'search-textarea'}, interactive=True,
            )],
        )

        runtime._attach_writeback_targets(plan, snapshot, current, 'node_failed')

        action = plan.actions[0]
        self.assertEqual(action.target_name, '搜索设置输入框')
        self.assertEqual(action.durable_locators[0]['strategy'], 'stable_id')

    async def test_entry_device_opens_web_url_before_condition_evaluation(self):
        runner = PageSteps.__new__(PageSteps)
        runner.page_steps_model = SimpleNamespace(type=0)
        runner.base_data = SimpleNamespace()
        runner._device_opened = False
        runner._should_force_step_url = lambda: True
        runner._open_web_device = AsyncMock()

        with patch('src.services.ui.page_steps.AsyncElement') as element_class:
            await runner._prepare_entry_device()

        element_class.assert_called_once_with(runner.base_data, 0)
        runner._open_web_device.assert_awaited_once_with(element_class.return_value)
        self.assertTrue(runner._device_opened)

    async def test_report_failure_does_not_replace_business_result(self):
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), page_step(), _TestData())
        outcome = SimpleNamespace(
            trace_id='e60d4e46-ff64-42ef-8f39-a5e91b3e41fd', status='failed',
            model_dump=lambda **_: {
                'trace_id': 'e60d4e46-ff64-42ef-8f39-a5e91b3e41fd', 'status': 'failed',
                'trigger': 'node_failed', 'source_version': 2, 'failed_node_id': '11',
                'before_state': {}, 'after_state': {}, 'proposed_plan': {},
                'executed_plan': {}, 'confidence': 0, 'user_message': 'not recovered',
                'error_message': None,
            },
        )
        with (
            patch('src.services.ui.step_healing.orchestrator.HTTP.ui_page_step.save_heal_report', AsyncMock(side_effect=RuntimeError('offline'))),
            patch('src.services.ui.step_healing.orchestrator.StepHealReportOutbox.upsert', return_value=1),
            patch('src.services.ui.step_healing.orchestrator.StepHealReportOutbox.mark_failed') as mark_failed,
        ):
            await runtime._report(outcome)
        mark_failed.assert_called_once()

    async def test_recover_reports_readable_timeout_reason(self):
        model = page_step()
        model.healing_policy = {
            'mode': 'execute_low_risk',
            'total_timeout_seconds': 5,
        }
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), model, _TestData())
        runtime._recover = AsyncMock(side_effect=asyncio.TimeoutError())
        runtime._report = AsyncMock()

        outcome = await runtime.recover(model.element_list[0], trigger='node_failed')

        self.assertEqual(outcome.status, 'failed')
        self.assertEqual(outcome.error_message, '页面步骤自愈超过总超时5秒')
        self.assertEqual(outcome.user_message, '页面步骤自愈超过总超时5秒')

    async def test_planner_receives_latest_snapshot_after_checkpoint_confirmation(self):
        model = page_step()
        model.healing_policy = {'mode': 'suggest_only'}
        with patch('src.services.ui.step_healing.orchestrator.PlatformModelClient'):
            runtime = PageStepHealingOrchestrator(SimpleNamespace(), model, _TestData())
        state = SimpleNamespace(
            normalized_url_path='/flow', visible_text_digest='text',
            form_state_digest='form', matched_checkpoints=[],
            model_dump=lambda **_: {'matched_checkpoints': []},
        )
        first = AccessibilitySnapshot(
            snapshot_id='snapshot01', page_url='https://example.com', created_at_ms=1,
        )
        latest = AccessibilitySnapshot(
            snapshot_id='snapshot02', page_url='https://example.com', created_at_ms=2,
        )
        runtime.observer.snapshot = AsyncMock(side_effect=[(state, first), (state, latest)])
        runtime.planner.plan_async = AsyncMock(return_value=StepRepairPlan.model_validate({
            'schema_version': 1,
            'diagnosis_code': 'stop',
            'diagnosis_summary': 'No safe action',
            'confidence': .9,
            'actions': [{'action': 'abort', 'reason': 'manual review'}],
            'user_message': 'Manual review is required',
        }))
        runtime._report = AsyncMock()

        await runtime._recover(
            model.element_list[0], 'failed', [], {
                'trace_id': 'trace-1', 'trigger': 'node_failed',
                'source_version': 2, 'failed_node_id': '11',
            },
        )

        self.assertIs(runtime.planner.plan_async.await_args.args[1], latest)
        self.assertEqual(runtime.observer.snapshot.await_count, 2)

    async def test_entry_mismatch_resumes_from_latest_stable_precondition(self):
        runner = PageSteps.__new__(PageSteps)
        runner.page_steps_model = SimpleNamespace(
            id=3,
            entry_criteria={'operator': 'all', 'conditions': [{'type': 'visible_text'}]},
        )
        runner._condition_met = AsyncMock(return_value=False)
        runner._wait_for_condition = AsyncMock(return_value=False)
        runner._element_model = lambda _: page_step().element_list[0]
        state = SimpleNamespace(matched_checkpoints=['node:12:pre'])
        runtime = SimpleNamespace(
            checkpoints={},
            observer=SimpleNamespace(snapshot=AsyncMock(side_effect=[(state, None), (state, None)])),
            recover=AsyncMock(),
        )
        runner._healing_runtime = lambda: runtime
        flow = {'id': 11, 'children': [{'id': 12, 'children': []}]}

        entry, result = await runner._prepare_flow_entry(flow)

        self.assertEqual(entry['id'], 12)
        self.assertIsNone(result)
        runtime.recover.assert_not_awaited()

    async def test_entry_mismatch_finishes_when_success_checkpoint_is_stable(self):
        runner = PageSteps.__new__(PageSteps)
        runner.page_steps_model = SimpleNamespace(
            id=3,
            entry_criteria={'operator': 'all', 'conditions': [{'type': 'visible_text'}]},
        )
        runner._condition_met = AsyncMock(return_value=False)
        runner._wait_for_condition = AsyncMock(return_value=False)
        runner._element_model = lambda _: page_step().element_list[0]
        state = SimpleNamespace(matched_checkpoints=['success'])
        runtime = SimpleNamespace(
            checkpoints={},
            observer=SimpleNamespace(snapshot=AsyncMock(side_effect=[(state, None), (state, None)])),
            recover=AsyncMock(),
        )
        runner._healing_runtime = lambda: runtime

        entry, result = await runner._prepare_flow_entry({'id': 11, 'children': []})

        self.assertIsNone(entry)
        self.assertEqual(result.status, 1)
        runtime.recover.assert_not_awaited()

    async def test_entry_mismatch_continues_when_entry_becomes_stable_after_navigation(self):
        runner = PageSteps.__new__(PageSteps)
        runner.page_steps_model = SimpleNamespace(
            id=3,
            entry_criteria={'operator': 'all', 'conditions': [{'type': 'visible_text'}]},
        )
        runner._condition_met = AsyncMock(return_value=False)
        runner._wait_for_condition = AsyncMock(return_value=False)
        runner._element_model = lambda _: page_step().element_list[0]
        loading_state = SimpleNamespace(matched_checkpoints=[])
        ready_state = SimpleNamespace(matched_checkpoints=['entry'])
        runtime = SimpleNamespace(
            checkpoints={},
            observer=SimpleNamespace(snapshot=AsyncMock(side_effect=[
                (loading_state, None), (ready_state, None),
            ])),
            recover=AsyncMock(),
        )
        runner._healing_runtime = lambda: runtime
        flow = {'id': 11, 'children': []}

        entry, result = await runner._prepare_flow_entry(flow)

        self.assertIs(entry, flow)
        self.assertIsNone(result)
        runtime.recover.assert_not_awaited()

    async def test_entry_waits_for_spa_content_before_starting_recovery(self):
        runner = PageSteps.__new__(PageSteps)
        runner.page_steps_model = SimpleNamespace(
            entry_criteria={'operator': 'all', 'conditions': [{'type': 'visible_text'}]},
        )
        runner._condition_met = AsyncMock(return_value=False)
        runner._wait_for_condition = AsyncMock(return_value=True)
        runner._healing_runtime = lambda: SimpleNamespace(recover=AsyncMock())
        flow = {'id': 11, 'children': []}

        entry, result = await runner._prepare_flow_entry(flow)

        self.assertIs(entry, flow)
        self.assertIsNone(result)
        runner._wait_for_condition.assert_awaited_once()

    async def test_success_criteria_waits_for_async_navigation(self):
        runner = PageSteps.__new__(PageSteps)
        criteria = {
            'operator': 'all',
            'conditions': [{'type': 'url_path', 'matcher': 'starts_with', 'expected': '/done/'}],
        }
        runner.page_steps_model = SimpleNamespace(success_criteria=criteria)
        runner._wait_for_condition = AsyncMock(return_value=True)

        result = await runner._wait_for_success_criteria()

        self.assertTrue(result)
        runner._wait_for_condition.assert_awaited_once_with(criteria, timeout_seconds=5.0)

    async def test_record_element_result_updates_page_step_summary(self):
        runner = PageSteps.__new__(PageSteps)
        runner.page_step_result_model = SimpleNamespace(
            status=0,
            error_message=None,
            element_result_list=[],
        )
        runner._send_node_progress = AsyncMock()
        runner._send_progress = AsyncMock()
        result = ElementResultModel(
            id=11,
            type=0,
            status=0,
            error_message='入口条件未满足',
        )

        await runner._record_element_result(result)

        self.assertEqual(runner.page_step_result_model.status, 0)
        self.assertEqual(runner.page_step_result_model.error_message, '入口条件未满足')
        self.assertEqual(runner.page_step_result_model.element_result_list, [result])


if __name__ == '__main__':
    unittest.main()

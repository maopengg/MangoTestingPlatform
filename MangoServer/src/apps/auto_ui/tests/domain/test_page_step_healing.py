from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework import serializers

from src.apps.auto_ui.api.serializers.ui_page_steps import PageStepsSerializers
from src.apps.auto_ui.models import PageSteps, PageStepsDetailed, UiPageStepHealRecord
from src.apps.auto_ui.schemas.step_healing import (
    UiPageStepHealReport,
    UiStepRepairAction,
    validate_condition_group,
    validate_healing_policy,
)
from src.apps.auto_ui.services.page_step_healing import (
    AUTO_APPLIED_REVIEW_STATUS,
    PageStepHealingService,
)
from src.apps.auto_ui.services.test_case.test_case import TestCase


class PageStepHealingSchemaTest(SimpleTestCase):
    def test_case_step_model_delegates_without_undefined_page_step(self):
        service = TestCase.__new__(TestCase)
        expected = object()
        service.steps_model = MagicMock(return_value=expected)

        result = service.case_steps_model(7)

        self.assertIs(result, expected)
        self.assertEqual(service.steps_model.call_args.kwargs['model_class'].__name__, 'UiCasePageStepExecutionSchema')

    def test_model_fields_exist(self):
        self.assertIsNotNone(PageSteps._meta.get_field('success_criteria'))
        self.assertIsNotNone(PageSteps._meta.get_field('config_version'))
        self.assertIsNotNone(PageStepsDetailed._meta.get_field('precondition'))

    def test_auto_applied_status_fits_database_column(self):
        field = UiPageStepHealRecord._meta.get_field('writeback_status')
        self.assertLessEqual(len(AUTO_APPLIED_REVIEW_STATUS), field.max_length)

    def test_condition_group_is_normalized(self):
        result = validate_condition_group({
            'operator': 'all',
            'conditions': [{'type': 'visible_text', 'matcher': 'contains', 'expected': 'Done'}],
        }, 'success')
        self.assertEqual(result['conditions'][0]['expected'], 'Done')

    def test_empty_condition_group_is_stored_as_unconfigured(self):
        result = validate_condition_group({
            'operator': 'all',
            'conditions': [],
        }, 'node checkpoint')
        self.assertEqual(result, {})

    def test_invalid_policy_is_rejected(self):
        with self.assertRaises(serializers.ValidationError):
            validate_healing_policy({'mode': 'unsafe', 'auto_writeback': True})

    def test_auto_writeback_policy_keeps_safe_confidence_threshold(self):
        result = validate_healing_policy({
            'mode': 'execute_low_risk',
            'auto_writeback': True,
            'auto_writeback_min_confidence': 0.7,
        })
        self.assertTrue(result['auto_writeback'])
        self.assertEqual(result['auto_writeback_min_confidence'], 0.7)

    def test_enabled_healing_requires_an_active_run_mode(self):
        serializer = PageStepsSerializers()
        with self.assertRaises(serializers.ValidationError):
            serializer.validate({
                'healing_enabled': True,
                'goal': '完成页面目标',
                'success_criteria': {
                    'operator': 'all',
                    'conditions': [{
                        'type': 'visible_text', 'matcher': 'contains', 'expected': '完成',
                    }],
                },
                'healing_policy': {'mode': 'off'},
            })

    def test_removed_condition_types_are_rejected(self):
        for condition_type, matcher in (
                ('dialog_state', 'open'),
                ('variable_state', 'exists'),
        ):
            with self.subTest(condition_type=condition_type), self.assertRaises(serializers.ValidationError):
                validate_condition_group({
                    'operator': 'all',
                    'conditions': [{'type': condition_type, 'matcher': matcher}],
                }, 'success')

    def test_incompatible_condition_matcher_is_rejected(self):
        with self.assertRaises(serializers.ValidationError):
            validate_condition_group({
                'operator': 'all',
                'conditions': [{
                    'type': 'element_state',
                    'matcher': 'contains',
                    'element_id': 1,
                }],
            }, 'success')

    def test_report_requires_strict_protocol(self):
        with self.assertRaises(ValueError):
            UiPageStepHealReport.model_validate({
                'schema_version': 1, 'page_step_id': 1, 'trace_id': 'bad',
                'source_version': 1, 'trigger': 'node_failed', 'status': 'failed',
            })

    def test_repair_action_accepts_literal_input(self):
        action = UiStepRepairAction.model_validate({
            'action': 'insert_action',
            'operation_intent': 'edit',
            'target_ref': 'e1',
            'value_literal': '芒果测试平台',
            'reason': '使用步骤目标中明确的文本',
        })

        self.assertEqual(action.value_literal, '芒果测试平台')

    def test_linear_node_can_be_removed_and_edges_bridged(self):
        flow = {
            'nodes': [{'id': 'a'}, {'id': 'b'}, {'id': 'c'}],
            'edges': [
                {'id': 'ab', 'source': {'node_id': 'a'}, 'target': {'node_id': 'b'}},
                {'id': 'bc', 'source': {'node_id': 'b'}, 'target': {'node_id': 'c'}},
            ],
        }
        result = PageStepHealingService._remove_flow_node(flow, 'b')
        self.assertEqual([item['id'] for item in result['nodes']], ['a', 'c'])
        self.assertEqual(result['edges'][0]['source']['node_id'], 'a')
        self.assertEqual(result['edges'][0]['target']['node_id'], 'c')

    def test_action_can_be_inserted_before_linear_node(self):
        edges = [
            {'id': 'ab', 'source': {'node_id': 'a'}, 'target': {'node_id': 'b'}},
        ]
        result = PageStepHealingService._insert_flow_edges(edges, 'b', 'heal', 'before')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['target']['node_id'], 'heal')
        self.assertEqual(result[1]['source']['node_id'], 'heal')
        self.assertEqual(result[1]['target']['node_id'], 'b')

    def test_multiple_actions_before_node_keep_order_and_distinct_positions(self):
        positions = PageStepHealingService._linear_action_positions(
            {'x': 500, 'y': 100}, 2, 'before',
        )
        edges = PageStepHealingService._insert_flow_action_chain(
            [{
                'id': 'ab',
                'source': {'node_id': 'a'},
                'target': {'node_id': 'b'},
            }],
            'b', ['input', 'submit'], 'before',
        )

        self.assertEqual(positions, [
            {'x': 60.0, 'y': 100.0},
            {'x': 280.0, 'y': 100.0},
        ])
        pairs = [
            (edge['source']['node_id'], edge['target']['node_id'])
            for edge in edges
        ]
        self.assertEqual(pairs, [('a', 'input'), ('input', 'submit'), ('submit', 'b')])

    def test_multiple_actions_after_node_keep_original_order(self):
        edges = PageStepHealingService._insert_flow_action_chain(
            [{
                'id': 'bc',
                'source': {'node_id': 'b'},
                'target': {'node_id': 'c'},
            }],
            'b', ['confirm', 'continue'], 'after',
        )

        pairs = [
            (edge['source']['node_id'], edge['target']['node_id'])
            for edge in edges
        ]
        self.assertEqual(pairs, [('continue', 'c'), ('b', 'confirm'), ('confirm', 'continue')])

    def test_materialized_action_is_marked_for_ai_review(self):
        action = SimpleNamespace(
            durable_locators=[{
                'exp': 2, 'loc': "get_by_role('button', name='Next', exact=True)",
                'sub': None, 'strategy': 'role_name',
            }],
            node_id='detail-1', placement='before', target_name='Next', reason='continue',
            operation_intent='activate', target_tag='button', value_binding=None,
            value_literal=None,
        )
        page_step = SimpleNamespace(id=3, page_id=4, page=SimpleNamespace())
        flow = {
            'nodes': [{
                'id': 'root', 'type': 0, 'label': 'Root', 'position': {'x': 200, 'y': 100},
                'config': {'id': 'detail-1'},
            }],
            'edges': [],
        }
        element_query = MagicMock()
        element_query.exclude.return_value.exists.return_value = False
        detail_query = MagicMock()
        detail_query.aggregate.return_value = {'value': 1}
        detail = SimpleNamespace(id=9)
        detail_query.create.return_value = detail
        with (
            patch('src.apps.auto_ui.services.page_step_healing.PageElement.objects.filter', return_value=element_query),
            patch('src.apps.auto_ui.services.page_step_healing.PageStepsDetailed.objects.filter',
                  return_value=detail_query),
            patch('src.apps.auto_ui.services.page_step_healing.PageStepsDetailed.objects.create', return_value=detail),
            patch('src.apps.auto_ui.services.page_step_healing.PageStepRecordingService._detail_payload',
                  return_value={'type': 0}),
        ):
            result = PageStepHealingService._insert_action(
                page_step, flow, action, record_id=7, user_id=None,
            )

        inserted = result['nodes'][1]
        self.assertTrue(inserted['config']['ai_healed'])
        self.assertEqual(inserted['config']['ai_heal_record_id'], 7)
        self.assertEqual(inserted['config']['ai_review_status'], 'pending')

    def test_safe_recovered_insert_action_can_be_auto_applied(self):
        report = UiPageStepHealReport.model_validate({
            'page_step_id': 3,
            'trace_id': '12345678-1234-1234-1234-123456789abc',
            'source_version': 2,
            'trigger': 'entry_mismatch',
            'status': 'recovered',
            'confidence': 0.95,
            'auto_writeback_requested': True,
            'executed_plan': {
                'diagnosis_code': 'missing_action',
                'diagnosis_summary': '缺少继续操作',
                'confidence': 0.95,
                'user_message': '已临时补齐步骤',
                'actions': [{
                    'action': 'insert_action',
                    'node_id': 'detail-1',
                    'operation_intent': 'activate',
                    'target_ref': 'e12',
                    'target_name': '下一步',
                    'target_role': 'button',
                    'target_tag': 'button',
                    'placement': 'before',
                    'reason': '继续上传流程',
                    'durable_locators': [{
                        'exp': 2,
                        'loc': "get_by_role('button', name='下一步', exact=True)",
                        'strategy': 'role_name',
                    }],
                }],
            },
        })
        page_step = SimpleNamespace(healing_policy={
            'auto_writeback': True,
            'auto_writeback_min_confidence': 0.9,
        })

        self.assertTrue(PageStepHealingService._can_auto_apply(page_step, report))

        report.confidence = 0.89
        self.assertFalse(PageStepHealingService._can_auto_apply(page_step, report))

    def test_runtime_replacement_with_final_skip_can_be_auto_applied(self):
        report = UiPageStepHealReport.model_validate({
            'page_step_id': 3,
            'trace_id': '12345678-1234-1234-1234-123456789abd',
            'source_version': 2,
            'trigger': 'runtime_data_dependency_missing',
            'status': 'recovered',
            'confidence': 0.98,
            'auto_writeback_requested': True,
            'executed_plan': {
                'diagnosis_code': 'runtime_data_dependency_missing',
                'diagnosis_summary': '原定位变量缺失，已用页面目标替代',
                'confidence': 0.98,
                'user_message': '已完成替代动作并移除旧节点',
                'actions': [{
                    'action': 'insert_action',
                    'node_id': '216',
                    'operation_intent': 'edit',
                    'target_ref': 'e38',
                    'target_name': '搜索框',
                    'target_role': 'textbox',
                    'target_tag': 'input',
                    'placement': 'before',
                    'value_literal': '测试平台',
                    'reason': '输入步骤目标中的文字',
                    'durable_locators': [{
                        'exp': 2,
                        'loc': "get_by_role('textbox')",
                        'strategy': 'role_name',
                    }],
                }, {
                    'action': 'skip_node',
                    'node_id': '216',
                    'reason': '替代动作成功后移除失效旧节点',
                }],
            },
        })
        page_step = SimpleNamespace(healing_policy={
            'auto_writeback': True,
            'auto_writeback_min_confidence': 0.9,
        })

        self.assertTrue(PageStepHealingService._can_auto_apply(page_step, report))

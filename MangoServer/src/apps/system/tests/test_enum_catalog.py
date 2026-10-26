from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from src.apps.auto_api.enums import ApiCaseReleaseStatusEnum, ApiClientEnum
from src.apps.auto_api.enums.case import ApiCaseScenarioTagEnum
from src.apps.functional_test.services.common import ENUM_FIELD_MAP
from src.apps.system.api.views.system_api import SystemViews
from src.apps.system.services.enum_catalog import EnumCatalogService
from src.apps.task_center.enums.execution import AutomationExecutionSceneEnum
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums.environment import EnvironmentEnum


class EnumCatalogTests(SimpleTestCase):
    def test_offline_report_enums_are_explicitly_registered(self):
        from src.apps.test_center.enums.report_delivery import ReportSourceEnum
        catalog = EnumCatalogService.catalog()
        for key, enum in (
            ('report_source', ReportSourceEnum),
        ):
            self.assertEqual(catalog[key], enum.get_option())

    def test_reference_api_is_registered_as_an_item_source(self):
        from src.apps.evaluation.enums.data_source import EvaluationItemSourceEnum
        options = EnumCatalogService.catalog()['evaluation_item_source']
        self.assertEqual(options, EvaluationItemSourceEnum.get_option())
        self.assertIn({'key': 'api_info', 'title': '参考接口查询'}, options)

    def test_memory_fact_status_is_registered(self):
        from src.apps.evaluation.enums.memory import MemoryFactStatusEnum
        self.assertEqual(EnumCatalogService.catalog()['evaluation_memory_fact_status'], MemoryFactStatusEnum.get_option())

    def test_api_case_configuration_filter_is_registered(self):
        from src.apps.auto_api.enums.case import ApiCaseConfigurationFilterEnum
        self.assertEqual(EnumCatalogService.catalog()['api_case_configuration_filter'],
                         ApiCaseConfigurationFilterEnum.get_option())

    def setUp(self):
        patcher = patch('src.apps.system.services.system_config.SystemConfigService.get_environment_display_names',
                        return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_api_case_release_status_is_registered(self):
        self.assertEqual(
            EnumCatalogService.catalog()['api_case_release_status'],
            [
                {'key': ApiCaseReleaseStatusEnum.PREPUBLISHED.value, 'title': '预发布'},
                {'key': ApiCaseReleaseStatusEnum.PUBLISHED.value, 'title': '已发布'},
                {'key': ApiCaseReleaseStatusEnum.DEPRECATED.value, 'title': '已取消发布'},
                {'key': ApiCaseReleaseStatusEnum.RETIRED.value, 'title': '已归档'},
            ],
        )

    def test_report_failure_reason_is_registered(self):
        from src.apps.test_center.enums import ReportFailureReasonEnum
        self.assertEqual(EnumCatalogService.catalog()['report_failure_reason'], ReportFailureReasonEnum.get_option())
        self.assertEqual(ReportFailureReasonEnum.get_value('product_pending'), '产品缺陷待修复')

    def test_report_retention_policy_is_registered(self):
        from src.apps.task_center.enums.execution import ReportRetentionPolicyEnum
        self.assertEqual(EnumCatalogService.catalog()['report_retention_policy'], ReportRetentionPolicyEnum.get_option())

    def test_tuple_enum_uses_one_definition_for_value_and_label(self):
        self.assertEqual(ApiClientEnum.PC.value, 1)
        self.assertEqual(ApiClientEnum.APP.value, 2)
        self.assertEqual(
            ApiClientEnum.get_option(),
            [
                {'key': 0, 'title': 'WEB'},
                {'key': 1, 'title': 'PC桌面'},
                {'key': 2, 'title': 'APP'},
                {'key': 3, 'title': '小程序'},
            ],
        )

    def test_catalog_version_is_stable_and_changes_with_content(self):
        first = EnumCatalogService.build({'status': [{'key': 1, 'title': '成功'}]})
        reordered = EnumCatalogService.build({'status': [{'title': '成功', 'key': 1}]})
        changed = EnumCatalogService.build({'status': [{'key': 1, 'title': '通过'}]})

        self.assertEqual(first['enum_version'], reordered['enum_version'])
        self.assertNotEqual(first['enum_version'], changed['enum_version'])

    def test_scheduled_task_and_cases_share_execution_scenes(self):
        task_tags = ScheduledTaskCaseSelectionService.scheduled_execution_scene_options()

        case_tags = ApiCaseScenarioTagEnum.obj()
        case_only_tags = {
            ApiCaseScenarioTagEnum.TEMPORARY_VALIDATION.value,
            ApiCaseScenarioTagEnum.PERFORMANCE_TEST.value,
            ApiCaseScenarioTagEnum.EFFECTIVENESS_TEST.value,
        }
        self.assertEqual(
            task_tags,
            {
                key: value
                for key, value in case_tags.items()
                if key not in case_only_tags
            },
        )
        self.assertIs(ENUM_FIELD_MAP['scenario_tags'], ApiCaseScenarioTagEnum)
        self.assertEqual(task_tags['smoke_verification'], '冒烟验证')
        self.assertEqual(task_tags['stability_monitoring'], '稳定性监测')
        self.assertEqual(task_tags['data_verification'], '数据校验')
        self.assertEqual(task_tags['production_inspection'], '生产巡检')
        self.assertEqual(task_tags['production_regression'], '生产回归')
        self.assertNotIn('main_flow', task_tags)
        self.assertNotIn('core_link', task_tags)
        self.assertNotIn('high_frequency', task_tags)
        self.assertNotIn('blocking', task_tags)
        self.assertNotIn('main_flow', case_tags)
        self.assertNotIn('core_link', case_tags)
        self.assertNotIn('high_frequency', case_tags)
        self.assertNotIn('blocking', case_tags)
        self.assertNotIn('temporary_validation', task_tags)
        self.assertNotIn('performance_test', task_tags)
        self.assertNotIn('effectiveness_test', task_tags)
        self.assertEqual(case_tags['effectiveness_test'], '效果评测')
        self.assertEqual(case_tags['temporary_validation'], '临时验证')
        self.assertEqual(case_tags['performance_test'], '性能测试')

    def test_production_task_matches_one_exact_production_scene(self):
        self.assertEqual(
            ScheduledTaskCaseSelectionService.required_tags(
                AutomationExecutionSceneEnum.STABILITY_MONITORING.value,
                EnvironmentEnum.PRO.value,
            ),
            ['stability_monitoring'],
        )
        self.assertEqual(
            ScheduledTaskCaseSelectionService.required_tags(
                AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value,
                EnvironmentEnum.PRO.value,
            ),
            ['production_inspection'],
        )
        self.assertEqual(
            ScheduledTaskCaseSelectionService.required_tags(
                AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
                EnvironmentEnum.PRO.value,
            ),
            ['production_regression'],
        )
        self.assertEqual(
            ScheduledTaskCaseSelectionService.manual_required_tags(
                AutomationExecutionSceneEnum.SMOKE_VERIFICATION.value,
                EnvironmentEnum.TEST.value,
            ),
            [],
        )

    def test_manual_task_execution_scene_is_only_a_classification_label(self):
        ScheduledTaskCaseSelectionService.validate_environment_rule(
            execution_scenes=[AutomationExecutionSceneEnum.STABILITY_MONITORING.value],
            execution_scope='manual',
            test_env=EnvironmentEnum.PRO.value,
        )
        ScheduledTaskCaseSelectionService.validate_environment_rule(
            execution_scenes=[AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value],
            execution_scope='manual',
            test_env=EnvironmentEnum.TEST.value,
        )
        ScheduledTaskCaseSelectionService.validate_environment_rule(
            execution_scenes=[AutomationExecutionSceneEnum.STABILITY_MONITORING.value],
            execution_scope='manual',
            test_env=EnvironmentEnum.PRO.value,
        )
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environment_rule(
                execution_scenes=[AutomationExecutionSceneEnum.STABILITY_MONITORING.value],
                execution_scope='manual',
                test_env=EnvironmentEnum.TEST.value,
            )

    def test_dynamic_task_allows_production_case_tags_in_test_environment(self):
        ScheduledTaskCaseSelectionService.validate_environment_rule(
            execution_scenes=[AutomationExecutionSceneEnum.STABILITY_MONITORING.value],
            execution_scope='module',
            test_env=EnvironmentEnum.PRO.value,
        )
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environment_rule(
                execution_scenes=[AutomationExecutionSceneEnum.STABILITY_MONITORING.value],
                execution_scope='module',
                test_env=EnvironmentEnum.TEST.value,
            )
        ScheduledTaskCaseSelectionService.validate_environment_rule(
            execution_scenes=[AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value],
            execution_scope='module',
            test_env=EnvironmentEnum.TEST.value,
        )

    def test_multiple_execution_scenes_use_any_match_semantics(self):
        required_tags = [
            AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value,
            AutomationExecutionSceneEnum.SMOKE_VERIFICATION.value,
        ]

        self.assertTrue(
            ScheduledTaskCaseSelectionService._has_tags(
                [AutomationExecutionSceneEnum.SMOKE_VERIFICATION.value],
                required_tags,
            )
        )
        self.assertFalse(
            ScheduledTaskCaseSelectionService._has_tags(
                [AutomationExecutionSceneEnum.DATA_VERIFICATION.value],
                required_tags,
            )
        )
        self.assertFalse(
            ScheduledTaskCaseSelectionService._has_tags(
                [
                    AutomationExecutionSceneEnum.SMOKE_VERIFICATION.value,
                    ApiCaseScenarioTagEnum.EFFECTIVENESS_TEST.value,
                ],
                required_tags,
            )
        )
        self.assertFalse(
            ScheduledTaskCaseSelectionService._has_tags(
                [
                    AutomationExecutionSceneEnum.SMOKE_VERIFICATION.value,
                    ApiCaseScenarioTagEnum.TEMPORARY_VALIDATION.value,
                ],
                required_tags,
            )
        )
        self.assertFalse(
            ScheduledTaskCaseSelectionService._has_tags(
                [
                    AutomationExecutionSceneEnum.SMOKE_VERIFICATION.value,
                    ApiCaseScenarioTagEnum.PERFORMANCE_TEST.value,
                ],
                required_tags,
            )
        )

    def test_execution_scene_list_is_required_and_cannot_mix_environments(self):
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environment_rule(
                execution_scenes=[],
                execution_scope='manual',
                test_env=EnvironmentEnum.TEST.value,
            )
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environment_rule(
                execution_scenes=[ApiCaseScenarioTagEnum.EFFECTIVENESS_TEST.value],
                execution_scope='manual',
                test_env=EnvironmentEnum.TEST.value,
            )
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environment_rule(
                execution_scenes=[ApiCaseScenarioTagEnum.TEMPORARY_VALIDATION.value],
                execution_scope='manual',
                test_env=EnvironmentEnum.TEST.value,
            )
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environment_rule(
                execution_scenes=[ApiCaseScenarioTagEnum.PERFORMANCE_TEST.value],
                execution_scope='manual',
                test_env=EnvironmentEnum.TEST.value,
            )
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environment_rule(
                execution_scenes=[
                    AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value,
                    AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value,
                ],
                execution_scope='full_product',
                test_env=EnvironmentEnum.PRO.value,
            )

    def test_enum_api_contains_version_and_complete_client_options(self):
        request = Request(APIRequestFactory().get('/api/system/enum'))

        response = SystemViews().enum_api(request)
        data = response.data['data']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data['enum_version']), 16)
        self.assertIn('ai_agent_tool_call_status', data)
        self.assertEqual(data['api_client'], ApiClientEnum.get_option())
        self.assertEqual(
            data['assertion_result_display_max_length'],
            settings.ASSERTION_RESULT_DISPLAY_MAX_LENGTH,
        )

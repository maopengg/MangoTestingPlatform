from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.task_center.enums import ScheduleFireSourceTypeEnum
from src.apps.task_center.enums.execution import (
    AutomationExecutionSceneEnum,
    AutomationExecutionScopeEnum,
)
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService
from src.apps.task_center.services.scheduling.fire import ScheduleFireService
from src.apps.task_center.services.selection.case_selection import ScheduledTaskCaseSelectionService
from src.apps.test_center.enums.environment import EnvironmentEnum


class ScheduledTaskMultiConfigTests(SimpleTestCase):
    def test_test_environments_are_deduplicated_and_sorted(self):
        result = ScheduledTaskCaseSelectionService.normalize_test_envs([
            EnvironmentEnum.PRO.value,
            EnvironmentEnum.TEST.value,
            EnvironmentEnum.PRO.value,
        ])

        self.assertEqual(result, sorted([EnvironmentEnum.TEST.value, EnvironmentEnum.PRO.value]))

    def test_dynamic_task_can_cover_production_and_non_production_environments(self):
        ScheduledTaskCaseSelectionService.validate_environments_rule(
            execution_scenes=[
                AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value,
                AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
            ],
            execution_scope=AutomationExecutionScopeEnum.FULL_PRODUCT.value,
            test_envs=[EnvironmentEnum.TEST.value, EnvironmentEnum.PRO.value],
        )

    def test_test_environment_can_match_production_inspection_and_regression_cases(self):
        scenes = [
            AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value,
            AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
        ]

        ScheduledTaskCaseSelectionService.validate_environments_rule(
            execution_scenes=scenes,
            execution_scope=AutomationExecutionScopeEnum.MODULE.value,
            test_envs=[EnvironmentEnum.TEST.value],
        )
        self.assertEqual(
            ScheduledTaskCaseSelectionService.execution_scenes_for_environment(
                scenes,
                EnvironmentEnum.TEST.value,
            ),
            scenes,
        )

    def test_test_environment_still_rejects_stability_monitoring(self):
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environments_rule(
                execution_scenes=[AutomationExecutionSceneEnum.STABILITY_MONITORING.value],
                execution_scope=AutomationExecutionScopeEnum.MODULE.value,
                test_envs=[EnvironmentEnum.TEST.value],
            )

    def test_dynamic_task_requires_a_scene_for_each_environment_category(self):
        with self.assertRaises(TaskCenterError):
            ScheduledTaskCaseSelectionService.validate_environments_rule(
                execution_scenes=[AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value],
                execution_scope=AutomationExecutionScopeEnum.FULL_PRODUCT.value,
                test_envs=[EnvironmentEnum.TEST.value, EnvironmentEnum.PRO.value],
            )

    def test_report_scenes_are_split_by_environment(self):
        scenes = [
            AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value,
            AutomationExecutionSceneEnum.STABILITY_MONITORING.value,
            AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
        ]

        self.assertEqual(
            ScheduledTaskCaseSelectionService.execution_scenes_for_environment(
                scenes,
                EnvironmentEnum.TEST.value,
            ),
            [
                AutomationExecutionSceneEnum.ROUTINE_REGRESSION.value,
                AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
            ],
        )
        self.assertEqual(
            ScheduledTaskCaseSelectionService.execution_scenes_for_environment(
                scenes,
                EnvironmentEnum.PRO.value,
            ),
            [
                AutomationExecutionSceneEnum.STABILITY_MONITORING.value,
                AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value,
            ],
        )

    def test_same_task_environment_and_minute_share_one_fire_key(self):
        planned_at = datetime(2026, 8, 31, 18, 0)

        first = ScheduleFireService.build_fire_key(
            ScheduleFireSourceTypeEnum.TEST_SUITE.value,
            'task:26:environment:0',
            planned_at,
        )
        second = ScheduleFireService.build_fire_key(
            ScheduleFireSourceTypeEnum.TEST_SUITE.value,
            'task:26:environment:0',
            planned_at,
        )

        self.assertEqual(first, second)

    @patch.object(ScheduleDispatchService, 'create_test_suite')
    def test_manual_trigger_creates_one_report_for_each_environment(self, create_test_suite):
        create_test_suite.side_effect = [101, 102]
        task = SimpleNamespace(test_envs=[EnvironmentEnum.TEST.value, EnvironmentEnum.PRO.value])

        result = ScheduleDispatchService.create_test_suites.__wrapped__(
            ScheduleDispatchService,
            task,
            user_id=8,
        )

        self.assertEqual(result, [101, 102])
        self.assertEqual(create_test_suite.call_count, 2)
        self.assertEqual(
            [call.kwargs['test_env'] for call in create_test_suite.call_args_list],
            [EnvironmentEnum.TEST.value, EnvironmentEnum.PRO.value],
        )

    @patch.object(ScheduleDispatchService, 'create_test_suite')
    def test_manual_trigger_allows_temporary_execution_environment(self, create_test_suite):
        create_test_suite.return_value = 101
        task = SimpleNamespace(test_envs=[EnvironmentEnum.PRO.value])

        result = ScheduleDispatchService.create_test_suites.__wrapped__(
            ScheduleDispatchService,
            task,
            user_id=8,
            test_envs=[EnvironmentEnum.SIM.value],
            allow_unconfigured_test_env=True,
        )

        self.assertEqual(result, [101])
        create_test_suite.assert_called_once_with(
            task,
            api_concurrency_limit=None,
            user_id=8,
            test_env=EnvironmentEnum.SIM.value,
            allow_unconfigured_test_env=True,
        )

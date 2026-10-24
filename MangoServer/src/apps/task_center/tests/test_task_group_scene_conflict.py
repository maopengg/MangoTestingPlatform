from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.task_center.enums.execution import AutomationExecutionSceneEnum
from src.apps.task_center.exceptions import TaskCenterError
from src.apps.task_center.services.scheduling.task_group import ScheduledTaskGroupService
from src.apps.test_center.enums.environment import EnvironmentEnum


class TaskGroupSceneConflictTests(SimpleTestCase):
    def normalize(self, scenes, **extra):
        with (
            patch('src.apps.task_center.services.scheduling.task_group.User') as user,
            patch.object(ScheduledTaskGroupService, '_notice', return_value=(0, None, 0)),
            patch.object(ScheduledTaskGroupService, '_modules', return_value=[]),
            patch.object(ScheduledTaskGroupService, '_timing_ids', return_value=[1]),
        ):
            user.objects.filter.return_value.exists.return_value = True
            return ScheduledTaskGroupService.normalize(None, {
                'name': '场景互斥测试', 'case_people': 1,
                'test_envs': [EnvironmentEnum.PRO.value],
                'execution_scenes': scenes,
                **extra,
            })

    def test_initial_report_policy_is_validated_but_not_persisted_to_group(self):
        scenes = [AutomationExecutionSceneEnum.STABILITY_MONITORING.value]
        normalized = self.normalize(scenes, new_task_report_retention_policy='abnormal_only')
        self.assertEqual(normalized['new_task_report_retention_policy'], 'abnormal_only')
        values = ScheduledTaskGroupService._group_values(normalized, None)
        self.assertNotIn('report_retention_policy', values)
        self.assertNotIn('new_task_report_retention_policy', values)
        self.assertEqual(self.normalize(scenes)['new_task_report_retention_policy'], 'all')
        with self.assertRaises(TaskCenterError):
            self.normalize(scenes, new_task_report_retention_policy='invalid')

    def test_stability_rejects_each_production_scene_and_both(self):
        stability = AutomationExecutionSceneEnum.STABILITY_MONITORING.value
        inspection = AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value
        regression = AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value
        for scenes in ([stability, inspection], [regression, stability], [stability, inspection, regression]):
            with self.subTest(scenes=scenes):
                with self.assertRaisesMessage(TaskCenterError, '稳定性监测不能与生产巡检、生产回归同时选择'):
                    self.normalize(scenes)

    def test_stability_alone_and_production_pair_remain_allowed(self):
        for scenes in (
            [AutomationExecutionSceneEnum.STABILITY_MONITORING.value],
            [AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value],
            [AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value],
            [AutomationExecutionSceneEnum.PRODUCTION_INSPECTION.value,
             AutomationExecutionSceneEnum.PRODUCTION_REGRESSION.value],
        ):
            with self.subTest(scenes=scenes):
                self.assertEqual(set(self.normalize(scenes)['execution_scenes']), set(scenes))

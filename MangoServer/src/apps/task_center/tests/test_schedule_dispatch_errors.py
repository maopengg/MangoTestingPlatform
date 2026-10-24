from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.exceptions import AutoApiError, API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum
from src.apps.task_center.services.scheduling.dispatch import ScheduleDispatchService


class ScheduleDispatchErrorClassificationTests(SimpleTestCase):
    def setUp(self):
        self.fire = SimpleNamespace(
            id=101,
            source_type=ScheduleFireSourceTypeEnum.TEST_SUITE.value,
            task_id=202,
            extra_data={},
            test_suite_id=None,
            status=ScheduleFireStatusEnum.DISPATCHING.value,
        )
        manager = patch('src.apps.task_center.services.scheduling.dispatch.ScheduleFire.objects')
        self.fires = manager.start()
        self.addCleanup(manager.stop)
        self.fires.select_for_update.return_value.filter.return_value.first.return_value = self.fire

    @patch('src.apps.task_center.services.scheduling.dispatch.transaction.atomic', return_value=nullcontext())
    @patch('src.apps.task_center.services.scheduling.dispatch.Tasks.objects.select_related')
    @patch.object(
        ScheduleDispatchService,
        'create_test_suite',
        side_effect=AutoApiError(API_VERSION_API_INFO_CASE_REVISION_BINDING_INVALID),
    )
    @patch('src.apps.task_center.services.scheduling.dispatch.ScheduleFireService.mark_failed')
    @patch('src.apps.task_center.services.scheduling.dispatch.ScheduleFireService.mark_skipped')
    def test_business_error_is_skipped(
            self,
            mark_skipped,
            mark_failed,
            _create_test_suite,
            select_related,
            _atomic,
    ):
        select_related.return_value.get.return_value = SimpleNamespace(
            id=self.fire.task_id,
            test_envs=[1],
        )

        result = ScheduleDispatchService.dispatch_fire(self.fire, node_name='scheduler-1')

        self.assertIsNone(result)
        mark_skipped.assert_called_once_with(
            self.fire.id,
            '[1128] 用例修订的接口绑定不完整或不一致',
            'scheduler-1',
        )
        mark_failed.assert_not_called()

    @patch('src.apps.task_center.services.scheduling.dispatch.transaction.atomic', return_value=nullcontext())
    @patch('src.apps.task_center.services.scheduling.dispatch.Tasks.objects.select_related')
    @patch.object(
        ScheduleDispatchService,
        'create_test_suite',
        side_effect=RuntimeError('database unavailable'),
    )
    @patch('src.apps.task_center.services.scheduling.dispatch.ScheduleFireService.mark_failed')
    @patch('src.apps.task_center.services.scheduling.dispatch.ScheduleFireService.mark_skipped')
    def test_unknown_error_is_failed(
            self,
            mark_skipped,
            mark_failed,
            _create_test_suite,
            select_related,
            _atomic,
    ):
        select_related.return_value.get.return_value = SimpleNamespace(
            id=self.fire.task_id,
            test_envs=[1],
        )

        result = ScheduleDispatchService.dispatch_fire(self.fire, node_name='scheduler-1')

        self.assertIsNone(result)
        mark_failed.assert_called_once_with(self.fire.id, 'database unavailable', 'scheduler-1')
        mark_skipped.assert_not_called()

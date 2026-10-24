from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from src.apps.system.services.runtime_center.recent_errors import RecentErrorsService
from src.apps.task_center.enums import ScheduleFireSourceTypeEnum, ScheduleFireStatusEnum


class RecentErrorsPaginationTests(SimpleTestCase):
    @patch('src.apps.system.services.runtime_center.recent_errors.ScheduleFire.objects.filter')
    def test_schedule_errors_exclude_test_suite_execution_failures(self, filter_queryset):
        queryset = MagicMock()
        filter_queryset.return_value = queryset

        result = RecentErrorsService.schedule_fire_error_queryset()

        filter_queryset.assert_called_once_with(status=ScheduleFireStatusEnum.FAIL.value)
        queryset.exclude.assert_called_once_with(
            source_type=ScheduleFireSourceTypeEnum.TEST_SUITE.value,
        )
        self.assertIs(result, queryset.exclude.return_value)

    @patch.object(RecentErrorsService, 'schedule_fire_error_count', return_value=2)
    @patch.object(RecentErrorsService, 'system_error_count', return_value=3)
    @patch.object(RecentErrorsService, 'schedule_fire_errors')
    @patch.object(RecentErrorsService, 'system_errors')
    def test_paginate_merges_sources_before_slicing(
            self,
            system_errors,
            schedule_fire_errors,
            _system_error_count,
            _schedule_error_count,
    ):
        now = datetime.now(timezone.utc)
        system_errors.return_value = [
            self.error_row('system-1', now),
            self.error_row('system-2', now - timedelta(minutes=2)),
            self.error_row('system-3', now - timedelta(minutes=4)),
        ]
        schedule_fire_errors.return_value = [
            self.error_row('schedule-1', now - timedelta(minutes=1)),
            self.error_row('schedule-2', now - timedelta(minutes=3)),
        ]

        rows, total = RecentErrorsService.paginate_errors(page=2, page_size=2)

        self.assertEqual(total, 5)
        self.assertEqual([item['title'] for item in rows], ['system-2', 'schedule-2'])
        self.assertNotIn('sort_time', rows[0])
        system_errors.assert_called_once_with(4, '', [])
        schedule_fire_errors.assert_called_once_with(4, '')

    @patch.object(RecentErrorsService, 'schedule_fire_error_count', return_value=1)
    @patch.object(RecentErrorsService, 'schedule_fire_errors', return_value=[])
    @patch.object(RecentErrorsService, 'system_error_count')
    @patch.object(RecentErrorsService, 'system_errors')
    def test_paginate_can_filter_schedule_errors(
            self,
            system_errors,
            system_error_count,
            schedule_fire_errors,
            schedule_fire_error_count,
    ):
        rows, total = RecentErrorsService.paginate_errors(
            page=1,
            page_size=20,
            category='schedule_fire',
            keyword='订单',
        )

        self.assertEqual(rows, [])
        self.assertEqual(total, 1)
        system_errors.assert_not_called()
        system_error_count.assert_not_called()
        schedule_fire_errors.assert_called_once_with(20, '订单')
        schedule_fire_error_count.assert_called_once_with('订单')

    @patch.object(RecentErrorsService, 'schedule_fire_error_count')
    @patch.object(RecentErrorsService, 'schedule_fire_errors')
    @patch.object(RecentErrorsService, 'system_error_count', return_value=2)
    @patch.object(RecentErrorsService, 'system_errors', return_value=[])
    def test_paginate_can_filter_event_source(
            self,
            system_errors,
            system_error_count,
            schedule_fire_errors,
            schedule_fire_error_count,
    ):
        rows, total = RecentErrorsService.paginate_errors(
            page=1,
            page_size=20,
            source='http,drf',
        )

        self.assertEqual(rows, [])
        self.assertEqual(total, 2)
        system_errors.assert_called_once_with(20, '', ['http', 'drf'])
        system_error_count.assert_called_once_with('', ['http', 'drf'])
        schedule_fire_errors.assert_not_called()
        schedule_fire_error_count.assert_not_called()

    @staticmethod
    def error_row(title: str, sort_time: datetime) -> dict:
        return {
            'title': title,
            'sort_time': sort_time,
            'source': 'test',
            'object_id': title,
        }

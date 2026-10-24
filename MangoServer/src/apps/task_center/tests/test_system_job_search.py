from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from src.apps.task_center.api.views.system_job import SystemJobViews
from src.apps.task_center.services.scheduling.system_job import SystemJobService
from src.apps.task_center.enums import ScheduleFireStatusEnum


class SystemJobSearchTests(SimpleTestCase):
    def list_jobs(self, **kwargs):
        with patch.object(SystemJobService, 'latest_fire_map', return_value={}), patch.object(
            SystemJobService, 'next_fire_at', return_value=None,
        ):
            return SystemJobService.list_jobs(**kwargs)

    def test_each_text_field_supports_partial_matching(self):
        job = SystemJobService.JOBS[0]
        for key, value in {
            'key': job.key.upper(), 'name': job.name[:4],
            'description': job.description[:8], 'cron': job.cron,
        }.items():
            with self.subTest(key=key):
                rows, total = self.list_jobs(filters={key: f' {value} '}, page_size=100)
                self.assertIn(job.key, [row['key'] for row in rows])
                self.assertEqual(total, len(rows))
                self.assertTrue(all(value.casefold() in row[key].casefold() for row in rows))

    def test_filters_are_combined_before_pagination(self):
        filters = {'name': '清理', 'cron': '30'}
        expected = [job.key for job in SystemJobService.JOBS if '清理' in job.name and '30' in job.cron]
        rows, total = self.list_jobs(filters=filters, page=2, page_size=1)
        self.assertGreater(len(expected), 1)
        self.assertEqual(total, len(expected))
        self.assertEqual([row['key'] for row in rows], expected[1:2])

    def test_empty_filters_preserve_existing_pagination(self):
        rows, total = self.list_jobs(filters={'name': ' ', 'cron': None}, page=2, page_size=10)
        self.assertEqual(total, len(SystemJobService.JOBS))
        self.assertEqual([row['key'] for row in rows], [job.key for job in SystemJobService.JOBS[10:20]])

    def test_no_match_has_zero_total(self):
        rows, total = self.list_jobs(filters={'key': 'missing-job-example'})
        self.assertEqual((rows, total), ([], 0))

    def test_view_passes_clean_filters_and_pagination(self):
        request = Request(APIRequestFactory().get('/', {'name': ' 清理 ', 'page': 2, 'pageSize': 10}))
        with patch.object(SystemJobService, 'list_jobs', return_value=([], 0)) as list_jobs:
            SystemJobViews().list(request)
        list_jobs.assert_called_once_with(
            page=2, page_size=10, filters={
                'key': '', 'name': '清理', 'description': '', 'cron': '',
                'latest_error_message': '', 'source_type__in': '', 'latest_status__in': '',
            },
        )

    def test_source_type_multi_select_filters_before_pagination(self):
        source_type = SystemJobService.JOBS[-1].source_type
        expected = [job.key for job in SystemJobService.JOBS if job.source_type == source_type]
        rows, total = self.list_jobs(filters={'source_type__in': f' {source_type},999 '}, page=2, page_size=2)
        self.assertEqual(total, len(expected))
        self.assertEqual([row['key'] for row in rows], expected[2:4])

    def test_status_multi_select_includes_zero_and_untriggered_before_pagination(self):
        jobs = SystemJobService.JOBS
        latest = {
            jobs[0].key: {'status': ScheduleFireStatusEnum.SUCCESS.value},
            jobs[1].key: {'status': ScheduleFireStatusEnum.PENDING.value},
            jobs[2].key: {'status': ScheduleFireStatusEnum.FAIL.value},
        }
        with patch.object(SystemJobService, 'latest_fire_map', return_value=latest), patch.object(
            SystemJobService, 'next_fire_at', return_value=None,
        ):
            rows, total = SystemJobService.list_jobs(
                filters={'latest_status__in': '0,4,untriggered'}, page=2, page_size=2,
            )
        self.assertEqual(total, len(jobs) - 1)
        self.assertEqual([row['key'] for row in rows], [job.key for job in jobs[3:5]])

    def test_error_and_latest_status_filters_are_combined(self):
        first, second = SystemJobService.JOBS[:2]
        latest = {
            first.key: {'status': ScheduleFireStatusEnum.FAIL.value, 'error_message': 'Example timeout'},
            second.key: {'status': ScheduleFireStatusEnum.SUCCESS.value, 'error_message': 'Example timeout'},
        }
        with patch.object(SystemJobService, 'latest_fire_map', return_value=latest), patch.object(
            SystemJobService, 'next_fire_at', return_value=None,
        ):
            rows, total = SystemJobService.list_jobs(filters={
                'latest_status__in': str(ScheduleFireStatusEnum.FAIL.value),
                'latest_error_message': ' TIMEOUT ',
            })
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]['key'], first.key)

    def test_view_passes_multi_select_parameters(self):
        request = Request(APIRequestFactory().get('/', {
            'source_type__in': ' 2,4 ', 'latest_status__in': ' 0,4,untriggered ',
        }))
        with patch.object(SystemJobService, 'list_jobs', return_value=([], 0)) as list_jobs:
            SystemJobViews().list(request)
        filters = list_jobs.call_args.kwargs['filters']
        self.assertEqual(filters['source_type__in'], '2,4')
        self.assertEqual(filters['latest_status__in'], '0,4,untriggered')

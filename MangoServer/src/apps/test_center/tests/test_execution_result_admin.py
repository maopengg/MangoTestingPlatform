from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from src.apps.test_center.api.views.execution_result import ExecutionResultViews
from src.apps.test_center.models import ExecutionResult
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.apps.system.models import CacheData
from src.apps.system.services.system_config import SystemConfigService, get_config_definition_map


class ExecutionResultAdminServiceTests(TestCase):
    def setUp(self):
        key = 'RESULT_DATA_RETENTION_DAYS'
        defaults = SystemConfigService._definition_defaults(get_config_definition_map()[key])
        defaults['value'] = '7'
        CacheData.objects.update_or_create(key=key, defaults=defaults)
        SystemConfigService.invalidate(key)
        self.addCleanup(SystemConfigService.invalidate, key)

    @staticmethod
    def create_result(**kwargs) -> ExecutionResult:
        defaults = {
            'source_type': ExecutionResultService.SOURCE_PAGE,
            'target_type': ExecutionResultService.TARGET_API_CASE,
            'target_id': 100,
            'status': 1,
            'result_data': {'status': 1},
            'result_size': 12,
        }
        defaults.update(kwargs)
        return ExecutionResult.objects.create(**defaults)

    def test_admin_config_uses_backend_retention_and_counts_payload_state(self):
        old_result = self.create_result(target_id=101)
        ExecutionResult.objects.filter(id=old_result.id).update(
            create_time=timezone.now() - timedelta(days=8),
        )
        self.create_result(target_id=102)
        self.create_result(
            target_id=103,
            result_data=None,
            result_size=0,
            result_cleaned=True,
            result_cleaned_at=timezone.now(),
        )

        config = ExecutionResultService.admin_config()

        self.assertEqual(config['retention_days'], 7)
        self.assertEqual(config['total_count'], 3)
        self.assertEqual(config['available_count'], 2)
        self.assertEqual(config['expired_pending_count'], 1)
        self.assertEqual(config['cleaned_count'], 1)

    def test_admin_list_supports_result_state_and_business_filters(self):
        available = self.create_result(
            source_type=ExecutionResultService.SOURCE_REPORT,
            target_id=201,
        )
        self.create_result(
            source_type=ExecutionResultService.SOURCE_PAGE,
            target_id=202,
        )
        self.create_result(
            source_type=ExecutionResultService.SOURCE_REPORT,
            target_id=203,
            result_data=None,
            result_size=0,
            result_cleaned=True,
            result_cleaned_at=timezone.now(),
        )

        data, total = ExecutionResultService.admin_result_options({
            'source_type': ExecutionResultService.SOURCE_REPORT,
            'result_state': 'available',
        })

        self.assertEqual(total, 1)
        self.assertEqual(data[0]['id'], available.id)
        self.assertEqual(data[0]['source_type_name'], '测试报告')
        self.assertTrue(data[0]['has_result_data'])

    def test_cleanup_removes_only_expired_payload_and_keeps_record(self):
        old_result = self.create_result(target_id=301)
        recent_result = self.create_result(target_id=302)
        ExecutionResult.objects.filter(id=old_result.id).update(
            create_time=timezone.now() - timedelta(days=8),
        )

        updated_count = ExecutionResultService.clear_expired_result_data()

        self.assertEqual(updated_count, 1)
        self.assertEqual(ExecutionResult.objects.count(), 2)
        old_result.refresh_from_db()
        recent_result.refresh_from_db()
        self.assertIsNone(old_result.result_data)
        self.assertTrue(old_result.result_cleaned)
        self.assertIsNotNone(old_result.result_cleaned_at)
        self.assertIsNotNone(recent_result.result_data)
        self.assertFalse(recent_result.result_cleaned)

    def test_admin_filters_use_naive_datetime_when_project_disables_timezone(self):
        request = Request(APIRequestFactory().get(
            '/api/system/execution/result/admin/list',
            {
                'create_time_start': '2026-07-01 00:00:00',
                'create_time_end': '2026-07-28 23:59:59',
            },
        ))

        filters = ExecutionResultViews.build_admin_filters(request)

        self.assertIsNotNone(filters)
        self.assertTrue(timezone.is_naive(filters['create_time__gte']))
        self.assertTrue(timezone.is_naive(filters['create_time__lte']))

    def test_admin_filters_support_multiple_enum_and_integer_values(self):
        request = Request(APIRequestFactory().get(
            '/api/system/execution/result/admin/list',
            {
                'status__in': '0,1,4',
                'test_env__in': '1,2',
                'trigger_user_id__in': '2,3',
                'source_type__in': 'page,report',
                'target_type__in': 'api_case,ui_case',
                'result_state__in': 'available,cleaned',
            },
        ))

        filters = ExecutionResultViews.build_admin_filters(request)

        self.assertEqual(filters['status__in'], [0, 1, 4])
        self.assertEqual(filters['test_env__in'], [1, 2])
        self.assertEqual(filters['trigger_user_id__in'], [2, 3])
        self.assertEqual(filters['source_type__in'], ['page', 'report'])
        self.assertEqual(filters['target_type__in'], ['api_case', 'ui_case'])
        self.assertEqual(filters['result_state__in'], ['available', 'cleaned'])

    def test_admin_filters_reject_invalid_multiple_integer_values(self):
        request = Request(APIRequestFactory().get(
            '/api/system/execution/result/admin/list',
            {'status__in': '0,失败'},
        ))

        self.assertIsNone(ExecutionResultViews.build_admin_filters(request))

    def test_admin_filters_reject_invalid_multiple_result_states(self):
        request = Request(APIRequestFactory().get(
            '/api/system/execution/result/admin/list',
            {'result_state__in': 'available,未知状态'},
        ))

        self.assertIsNone(ExecutionResultViews.build_admin_filters(request))

    def test_admin_list_supports_multiple_result_states(self):
        available = self.create_result(target_id=401)
        cleaned = self.create_result(
            target_id=402,
            result_data=None,
            result_size=0,
            result_cleaned=True,
            result_cleaned_at=timezone.now(),
        )
        self.create_result(
            target_id=403,
            result_data=None,
            result_size=0,
            result_cleaned=False,
        )

        data, total = ExecutionResultService.admin_result_options({
            'result_state__in': ['available', 'cleaned'],
        })

        self.assertEqual(total, 2)
        self.assertEqual({item['id'] for item in data}, {available.id, cleaned.id})

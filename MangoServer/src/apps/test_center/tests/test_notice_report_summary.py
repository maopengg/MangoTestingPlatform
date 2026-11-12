from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.db.models import Sum
from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.test_center.services.reporting.test_suite.base_notice import NoticeMain
from src.apps.test_center.services.reporting.test_suite.detail_result import TestSuiteExecutionResultService


class FakeDetailQuerySet:

    def __init__(self, details):
        self.details = list(details)

    def __iter__(self):
        return iter(self.details)

    def filter(self, **kwargs):
        return FakeDetailQuerySet([
            detail for detail in self.details
            if self._matches(detail, kwargs)
        ])

    def exclude(self, **kwargs):
        return FakeDetailQuerySet([
            detail for detail in self.details
            if not self._matches(detail, kwargs)
        ])

    def select_related(self, *args):
        return self

    def aggregate(self, **kwargs):
        return {
            key: sum(getattr(detail, self._sum_field(expression), 0) or 0 for detail in self.details)
            for key, expression in kwargs.items()
        }

    @staticmethod
    def _matches(detail, kwargs):
        for key, value in kwargs.items():
            if key.endswith('__in'):
                field = key[:-4]
                if getattr(detail, field) not in value:
                    return False
            elif getattr(detail, key) != value:
                return False
        return True

    @staticmethod
    def _sum_field(expression):
        if isinstance(expression, Sum):
            return expression.get_source_expressions()[0].name
        raise AssertionError(f'不支持的聚合表达式：{expression!r}')


class NoticeReportSummaryTests(SimpleTestCase):
    def setUp(self):
        patcher = patch('src.apps.system.services.configuration.system_config.SystemConfigService.get_environment_display_names',
                        return_value={})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_notice_report_uses_normalized_api_counter_for_warning_steps(self):
        test_suite_id = 529516636147
        created_at = datetime(2026, 7, 8, 22, 0, 31)
        test_suite = SimpleNamespace(
            id=test_suite_id,
            create_time=created_at,
            update_time=created_at + timedelta(minutes=1, seconds=49),
            test_env=2,
            project_product=SimpleNamespace(
                name='开平接口',
                project=SimpleNamespace(name='示例项目'),
            ),
            tasks=SimpleNamespace(name='生产环境示例开平接口回归'),
        )
        api_result_data = [
                              {'id': index, 'parameter_id': index, 'status': TaskEnum.SUCCESS.value}
                              for index in range(634)
                          ] + [
                              {'id': 634, 'parameter_id': 634, 'status': TaskEnum.WARNING.value},
                              {'id': 635, 'parameter_id': 635, 'status': TaskEnum.WARNING.value},
                          ]
        api_detail = SimpleNamespace(
            is_excluded=False,
            id=1,
            type=TestCaseTypeEnum.API.value,
            status=TaskEnum.SUCCESS.value,
            case_sum=636,
            success=634,
            fail=0,
            warning=0,
            result_payload=SimpleNamespace(result_data=api_result_data),
        )

        with patch.object(TestSuite.objects, 'get', return_value=test_suite), \
                patch.object(TestSuiteDetails.objects, 'filter', return_value=FakeDetailQuerySet([api_detail])), \
                patch.object(TestSuiteExecutionResultService, 'get_result_data', return_value=api_result_data):
            test_report = NoticeMain._NoticeMain__test_report(test_suite_id)

        self.assertEqual(test_report.case_sum, 636)
        self.assertEqual(test_report.success, 634)
        self.assertEqual(test_report.fail, 0)
        self.assertEqual(test_report.warning, 2)
        self.assertEqual(test_report.api_case_sum, 636)
        self.assertEqual(test_report.api_fail, 0)
        self.assertEqual(test_report.success_rate, 99.69)

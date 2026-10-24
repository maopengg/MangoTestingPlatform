from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from mangotools.enums import TaskEnum

from src.apps.test_center.models import (
    ExecutionResult,
    Project,
    ProjectProduct,
    TestSuite,
    TestSuiteDetails,
)
from src.apps.test_center.services.execution_result import ExecutionResultService
from src.apps.test_center.services.test_suite.detail_result import TestSuiteExecutionResultService
from src.apps.user.models import User


class TestSuiteExecutionResultServiceTests(SimpleTestCase):
    @patch(
        'src.apps.test_center.services.test_suite.detail_result.ExecutionResultService.load_result_data'
    )
    def test_attach_children_keeps_legacy_string_result(self, load_result_data):
        load_result_data.return_value = '历史执行异常文本'
        payload = SimpleNamespace(result_size=24)
        data = [{'id': 1, 'type': 0, 'warning': 0}]

        TestSuiteExecutionResultService.attach_children(data, payload_map={1: payload})

        self.assertEqual(data[0]['children'], '历史执行异常文本')
        self.assertTrue(data[0]['has_result_data'])

    @patch(
        'src.apps.test_center.services.test_suite.detail_result.ExecutionResultService.load_result_data'
    )
    def test_attach_children_only_marks_structured_items(self, load_result_data):
        load_result_data.return_value = [
            {'name': '结构化步骤'},
            '历史文本步骤',
        ]
        payload = SimpleNamespace(result_size=48)
        data = [{'id': 1, 'type': 0, 'warning': 0}]

        TestSuiteExecutionResultService.attach_children(data, payload_map={1: payload})

        self.assertEqual(data[0]['children'][0]['case_type'], 0)
        self.assertEqual(data[0]['children'][1], '历史文本步骤')

    @patch(
        'src.apps.test_center.services.test_suite.detail_result.ApiInfoRuntimeService.resolve_runtime'
    )
    def test_build_api_warning_result_does_not_require_api_info_posterior_file(
            self,
            resolve_runtime,
    ):
        resolve_runtime.return_value = SimpleNamespace(
            id=11,
            name='测试接口',
            method=0,
            url='/api/example',
            protocol_type='http',
            body_type='none',
        )
        parameter = SimpleNamespace(
            id=22,
            name='测试场景',
            params=None,
            body_config=None,
            sse_config=None,
            case_detailed=SimpleNamespace(id=33, api_info_id=11),
        )

        result = TestSuiteExecutionResultService.build_api_warning_result(parameter)

        self.assertEqual(result['status'], TaskEnum.WARNING.value)
        self.assertIsNone(result['request']['posterior_file'])


class TestSuiteCaseExecutionHistoryTests(TestCase):
    def setUp(self):
        project = Project.objects.create(name='Case执行历史项目')
        product = ProjectProduct.objects.create(project=project, name='主服务')
        user = User.objects.create(
            name='执行历史用户',
            username='case_execution_history_user',
            password='pwd',
        )
        self.current_suite = TestSuite.objects.create(
            id=41001,
            project_product=product,
            test_env=0,
            user=user,
            status=TaskEnum.SUCCESS.value,
            is_notice=0,
        )
        other_suite = TestSuite.objects.create(
            id=41002,
            project_product=product,
            test_env=0,
            user=user,
            status=TaskEnum.SUCCESS.value,
            is_notice=0,
        )
        self.detail = TestSuiteDetails.objects.create(
            test_suite=self.current_suite,
            type=1,
            project_product=product,
            test_env=0,
            case_id=88,
            case_name='登录用例',
            status=TaskEnum.SUCCESS.value,
            retry=0,
        )
        other_detail = TestSuiteDetails.objects.create(
            test_suite=other_suite,
            type=1,
            project_product=product,
            test_env=0,
            case_id=88,
            case_name='登录用例',
            status=TaskEnum.FAIL.value,
            retry=0,
        )
        now = timezone.now()
        self.current_result = self.create_result(
            source_type=ExecutionResultService.SOURCE_REPORT,
            test_suite=self.current_suite,
            test_suite_detail=self.detail,
            status=TaskEnum.SUCCESS.value,
        )
        self.other_report_result = self.create_result(
            source_type=ExecutionResultService.SOURCE_REPORT,
            test_suite=other_suite,
            test_suite_detail=other_detail,
            status=TaskEnum.FAIL.value,
        )
        self.case_result = self.create_result(
            source_type=ExecutionResultService.SOURCE_PAGE,
            status=TaskEnum.SUCCESS.value,
        )
        ExecutionResult.objects.filter(id=self.current_result.id).update(create_time=now - timedelta(hours=3))
        ExecutionResult.objects.filter(id=self.other_report_result.id).update(create_time=now - timedelta(hours=2))
        ExecutionResult.objects.filter(id=self.case_result.id).update(create_time=now - timedelta(hours=1))

    @staticmethod
    def create_result(**kwargs):
        return ExecutionResult.objects.create(
            target_type=ExecutionResultService.TARGET_API_CASE,
            target_id=88,
            attempt_no=1,
            is_latest=True,
            result_data={},
            **kwargs,
        )

    def test_case_history_places_current_report_first_and_labels_sources(self):
        options = TestSuiteExecutionResultService.get_payload_options(self.detail.id, 20)

        self.assertEqual(
            [item['id'] for item in options],
            [self.current_result.id, self.case_result.id, self.other_report_result.id],
        )
        self.assertEqual(
            [item['source_scope_name'] for item in options],
            ['本测试报告', 'Case执行', '其他测试报告'],
        )
        self.assertFalse(options[0]['is_case_latest'])
        self.assertTrue(options[1]['is_case_latest'])

    def test_case_history_limit_is_applied_after_current_report_priority(self):
        options = TestSuiteExecutionResultService.get_payload_options(self.detail.id, 2)

        self.assertEqual(
            [item['id'] for item in options],
            [self.current_result.id, self.case_result.id],
        )

    def test_result_from_same_case_can_be_opened_across_sources(self):
        self.assertTrue(
            TestSuiteExecutionResultService.payload_matches_detail(self.detail, self.other_report_result)
        )
        self.assertTrue(TestSuiteExecutionResultService.payload_matches_detail(self.detail, self.case_result))
        unrelated = ExecutionResult.objects.create(
            source_type=ExecutionResultService.SOURCE_PAGE,
            target_type=ExecutionResultService.TARGET_API_CASE,
            target_id=99,
            status=TaskEnum.SUCCESS.value,
            result_data={},
        )
        self.assertFalse(TestSuiteExecutionResultService.payload_matches_detail(self.detail, unrelated))

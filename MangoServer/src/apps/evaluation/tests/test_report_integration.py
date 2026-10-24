from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum, TestCaseTypeEnum

from src.apps.evaluation.services.report import report_payload, sync_report
from src.apps.test_center.enums.environment import AutoTypeEnum
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.services.test_suite.retry import TestSuiteRetryService
from src.apps.test_center.services.test_suite.summary import TestSuiteSummaryService


class EvaluationReportTests(SimpleTestCase):
    def execution(self, **values):
        return SimpleNamespace(id=1, report_detail_id=11, execution_no="EV-TEST", status="completed", verdict="invalid",
            details={}, summary={"total": 2, "passed": 1, "failed": 0, "invalid": 1},
            snapshot={"case": {"id": 1}, "dataset": {"id": 2, "version_id": 3, "version_no": 1},
                "target": {"type": "script", "parameters": {"code": "private implementation"}, "content_hash": "hash"},
                "selection": {"item_ids": ["A", "B"]}, "grader_bindings": {}, "signatures": {},
                "environment": {"test_env": 3}}, **values)

    def test_type_values_are_additive_and_catalogs_include_evaluation(self):
        self.assertEqual(TestCaseTypeEnum.OTHER.value, 3)
        self.assertEqual(TestCaseTypeEnum.EVALUATION.value, 4)
        self.assertEqual(TestCaseTypeEnum.obj()[4], "效果测试")
        self.assertEqual(AutoTypeEnum.obj()[3], "效果测试")

    def test_report_keeps_version_and_omits_script_source(self):
        payload = report_payload(self.execution())
        self.assertEqual(payload["dataset"]["version_id"], 3)
        self.assertNotIn("parameters", payload["target"])

    @patch("src.apps.evaluation.services.report.EvaluationReportService.update")
    def test_invalid_results_are_separate_from_capability_failures(self, update):
        sync_report(self.execution())
        values = update.call_args.kwargs
        self.assertEqual(values["status"], TaskEnum.WARNING.value)
        self.assertEqual((values["success"], values["fail"], values["warning"]), (1, 0, 1))
        self.assertEqual(values["payload"]["summary"]["invalid"], 1)

    def test_report_type_counter_includes_all_evaluation_items(self):
        counter = TestSuiteSummaryService.counter_data_from_rows([
            {"type": 4, "case_sum": 10, "status": 4, "success": 7, "fail": 2, "warning": 1},
        ])
        self.assertEqual(counter["evaluation_case_sum"], 10)
        self.assertEqual(counter["evaluation_in_progress_case_sum"], 10)
        self.assertEqual(counter["api_case_sum"], 0)

    def test_generic_retry_rejects_evaluation_before_mutation(self):
        with self.assertRaises(TestCenterError):
            TestSuiteRetryService.ensure_retry_supported([SimpleNamespace(type=4)])

    @patch("src.apps.test_center.services.factory.TestObject.objects")
    def test_evaluation_test_object_prefers_dedicated_then_api_fallback(self, objects):
        from src.apps.test_center.services.factory import func_test_object_value
        dedicated = objects.filter.return_value.first.return_value
        self.assertIs(func_test_object_value(3, 22, AutoTypeEnum.EVALUATION.value), dedicated)
        objects.get.assert_not_called()
        objects.filter.return_value.first.return_value = None
        self.assertIs(func_test_object_value(3, 22, AutoTypeEnum.EVALUATION.value), objects.get.return_value)
        self.assertEqual(objects.get.call_args.kwargs['auto_type__in'], [AutoTypeEnum.API.value, AutoTypeEnum.CURRENCY.value])

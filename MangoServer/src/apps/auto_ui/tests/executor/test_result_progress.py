from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import TaskEnum

from src.apps.auto_ui.schemas.execution import UiPageStepResult
from src.apps.auto_ui.services.reporting.test_report_writing import TestReportWriting


def progress_result(*, sequence: int, is_final: bool = False) -> UiPageStepResult:
    return UiPageStepResult(
        execution_id="execution-1",
        progress_sequence=sequence,
        id=7,
        name="创建订单",
        type=0,
        project_product_id=1,
        project_product_name="订单",
        case_step_details_id=21,
        cache_data={},
        test_object="https://example.test",
        status=1 if is_final else 3,
        is_final=is_final,
        element_result_list=[],
    )


class MemoryCache:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, timeout=None):
        self.values[key] = value


class UiResultProgressOrderTest(SimpleTestCase):
    def setUp(self):
        self.cache = MemoryCache()
        self.cache_patch = patch(
            "src.apps.auto_ui.services.reporting.test_report_writing.cache",
            self.cache,
        )
        self.cache_patch.start()

    def tearDown(self):
        self.cache_patch.stop()

    def test_out_of_order_increment_is_ignored(self):
        newer = progress_result(sequence=2)
        older = progress_result(sequence=1)

        self.assertFalse(
            TestReportWriting._should_ignore_progress(TaskEnum.PROCEED.value, newer)
        )
        self.assertTrue(
            TestReportWriting._should_ignore_progress(TaskEnum.PROCEED.value, older)
        )

    def test_increment_after_final_is_ignored(self):
        final = progress_result(sequence=3, is_final=True)
        late_increment = progress_result(sequence=4)

        self.assertFalse(
            TestReportWriting._should_ignore_progress(TaskEnum.PROCEED.value, final)
        )
        TestReportWriting._mark_progress_final(final)

        self.assertTrue(
            TestReportWriting._should_ignore_progress(
                TaskEnum.PROCEED.value,
                late_increment,
            )
        )

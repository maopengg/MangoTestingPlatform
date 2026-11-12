from django.db import transaction
from mangotools.enums import StatusEnum

from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_CASE_EXECUTION_DUPLICATED,
    UI_CASE_CASE_EXECUTION_INVALID,
    UI_CASE_TEST_ENVIRONMENT_EXECUTION_REQUIRED,
)
from src.apps.auto_ui.models import UiCase
from src.apps.task_center.services.execution.add_tasks import AddTasks
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.reporting.test_suite.batch_execution_validation import BatchExecutionValidationService


class UiCaseBatchExecutionService:
    """UI Case 批量执行的统一业务入口。"""

    @classmethod
    @transaction.atomic
    def execute(
            cls,
            *,
            case_ids: list[int],
            test_env: int,
            user_id: int,
    ) -> dict:
        normalized_case_ids = cls.normalize_case_ids(case_ids)
        normalized_test_env = cls.normalize_test_env(test_env)
        cases = {
            case.id: case
            for case in UiCase.objects.filter(id__in=normalized_case_ids).select_related(
                "project_product",
                "project_product__project",
            )
        }
        BatchExecutionValidationService.ensure_all_cases_found(
            cases,
            normalized_case_ids,
            error_class=AutoUiError,
            error_message=UI_CASE_EXECUTION_DUPLICATED,
        )
        BatchExecutionValidationService.ensure_same_project(
            (
                (
                    cases[case_id].project_product.project_id,
                    cases[case_id].project_product.project.name,
                )
                for case_id in normalized_case_ids
            ),
            error_class=AutoUiError,
            error_message=UI_CASE_CASE_EXECUTION_INVALID,
        )

        first_case = cases[normalized_case_ids[0]]
        add_tasks = AddTasks(
            project_product=first_case.project_product_id,
            test_env=normalized_test_env,
            is_notice=StatusEnum.FAIL.value,
            user_id=user_id,
        )
        for case_id in normalized_case_ids:
            add_tasks.add_test_suite_details(case_id, TestCaseTypeEnum.UI)
        return {
            "case_ids": normalized_case_ids,
            "test_env": normalized_test_env,
            "test_suite_id": add_tasks.test_suite_id,
        }

    @staticmethod
    def normalize_case_ids(case_ids) -> list[int]:
        return BatchExecutionValidationService.normalize_case_ids(
            case_ids,
            error_class=AutoUiError,
            error_message=UI_CASE_EXECUTION_DUPLICATED,
        )

    @staticmethod
    def normalize_test_env(test_env) -> int:
        return BatchExecutionValidationService.normalize_test_environment(
            test_env,
            error_class=AutoUiError,
            error_message=UI_CASE_TEST_ENVIRONMENT_EXECUTION_REQUIRED,
        )

from django.db import transaction
from mangotools.enums import StatusEnum

from src.apps.auto_api.exceptions import (
    API_CASE_EXECUTION_REQUIRED,
    API_TASK_NAME_EXECUTION_INVALID,
    API_TASK_NAME_EXECUTION_TOO_LONG,
    API_TEST_ENVIRONMENT_EXECUTION_REQUIRED,
    API_VERSION_CASE_EXECUTION_INVALID,
    AutoApiError,
)
from src.apps.auto_api.models import ApiCase
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.task_center.services.execution.add_tasks import AddTasks
from src.apps.task_center.services.selection.api_concurrency import ApiConcurrencyService
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.test_suite.batch_execution_validation import BatchExecutionValidationService


class ApiCaseBatchExecutionService:
    """API Case 批量执行的统一业务入口。"""

    @classmethod
    @transaction.atomic
    def execute(
            cls,
            *,
            case_ids: list[int],
            execution_name: str,
            test_env: int,
            execution_version: str | None,
            user_id: int,
            api_concurrency_limit: int | None = None,
    ) -> dict:
        normalized_case_ids = cls.normalize_case_ids(case_ids)
        normalized_execution_name = cls._normalize_execution_name(execution_name)
        normalized_test_env = BatchExecutionValidationService.normalize_test_environment(
            test_env,
            error_class=AutoApiError,
            error_message=API_TEST_ENVIRONMENT_EXECUTION_REQUIRED,
        )
        normalized_execution_version = (
            ApiCaseRevisionService.normalize_batch_execution_version(execution_version)
        )
        normalized_concurrency_limit = ApiConcurrencyService.resolve_report_limit(
            api_concurrency_limit,
            AutoApiError,
        )
        selections = ApiCaseRevisionService.resolve_batch_executions(
            normalized_case_ids,
            execution_version=normalized_execution_version,
            operator_id=user_id,
        )
        cases = {
            case.id: case
            for case in ApiCase.objects.filter(id__in=normalized_case_ids).select_related(
                "project_product",
                "project_product__project",
            )
        }
        BatchExecutionValidationService.ensure_all_cases_found(
            cases,
            normalized_case_ids,
            error_class=AutoApiError,
            error_message=API_CASE_EXECUTION_REQUIRED,
        )
        BatchExecutionValidationService.ensure_same_project(
            (
                (
                    cases[case_id].project_product.project_id,
                    cases[case_id].project_product.project.name,
                )
                for case_id in normalized_case_ids
            ),
            error_class=AutoApiError,
            error_message=API_VERSION_CASE_EXECUTION_INVALID,
        )

        first_case = cases[normalized_case_ids[0]]
        add_tasks = AddTasks(
            project_product=first_case.project_product_id,
            test_env=normalized_test_env,
            is_notice=StatusEnum.FAIL.value,
            user_id=user_id,
            execution_name=normalized_execution_name,
            api_concurrency_limit=normalized_concurrency_limit,
        )
        for case_id in normalized_case_ids:
            selection = selections[case_id]
            add_tasks.add_test_suite_details(
                case_id,
                TestCaseTypeEnum.API,
                api_case_revision_id=selection.case_revision_id,
                api_case_release_id=selection.case_release_id,
                bound_checksum=selection.checksum,
            )

        executions = [
            {
                "case_id": case_id,
                "case_release_id": selections[case_id].case_release_id,
                "case_revision_id": selections[case_id].case_revision_id,
                "case_revision_no": selections[case_id].case_revision_no,
                "version_label": selections[case_id].version_label,
                "execution_source": selections[case_id].execution_source,
                "config_checksum": selections[case_id].checksum,
            }
            for case_id in normalized_case_ids
        ]
        return {
            "case_ids": normalized_case_ids,
            "executions": executions,
            "test_suite_id": add_tasks.test_suite_id,
            "execution_name": normalized_execution_name,
            "test_env": normalized_test_env,
            "api_concurrency_limit": normalized_concurrency_limit,
            "execution_version": normalized_execution_version,
        }

    @staticmethod
    def normalize_case_ids(case_ids) -> list[int]:
        return BatchExecutionValidationService.normalize_case_ids(
            case_ids,
            error_class=AutoApiError,
            error_message=API_CASE_EXECUTION_REQUIRED,
        )

    @staticmethod
    def _normalize_execution_name(execution_name) -> str:
        normalized = str(execution_name or "").strip()
        if not normalized:
            raise AutoApiError(API_TASK_NAME_EXECUTION_INVALID)
        if len(normalized) > 128:
            raise AutoApiError(API_TASK_NAME_EXECUTION_TOO_LONG)
        return normalized

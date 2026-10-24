from django.db import transaction
from mangotools.enums import StatusEnum

from src.apps.auto_pytest.enums import (
    PytestAssetStatusEnum,
    PytestSourceStatusEnum,
)
from src.apps.auto_pytest.exceptions import (
    AutoPytestError,
    PYTEST_EXECUTION_DUPLICATED,
    PYTEST_CASE_EXECUTION_INVALID,
    PYTEST_TEST_ENVIRONMENT_EXECUTION_REQUIRED,
    PYTEST_PROJECT_PRODUCT_BINDING_INVALID,
    PYTEST_FILE_EXECUTION_NOT_ALLOWED,
    PYTEST_FILE_PARSE_FAILED,
)
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.services.git_management.repository_service import RepositoryGitService
from src.apps.task_center.services.execution.add_tasks import AddTasks
from src.apps.test_center.enums import TestCaseTypeEnum
from src.apps.test_center.services.test_suite.batch_execution_validation import BatchExecutionValidationService


class PytestCaseBatchExecutionService:
    """Pytest Case 批量执行的统一业务入口。"""

    @classmethod
    @transaction.atomic
    def execute(cls, *, case_ids: list[int], test_env: int, user_id: int) -> dict:
        normalized_case_ids = cls.normalize_case_ids(case_ids)
        normalized_test_env = cls.normalize_test_env(test_env)
        cases = {
            case.id: case
            for case in PytestCase.objects.filter(id__in=normalized_case_ids).select_related(
                'project_product',
                'project_product__repository',
                'project_product__project_product',
                'project_product__project_product__project',
            )
        }
        BatchExecutionValidationService.ensure_all_cases_found(
            cases,
            normalized_case_ids,
            error_class=AutoPytestError,
            error_message=PYTEST_EXECUTION_DUPLICATED,
        )
        unbound_case_names = [
            cases[case_id].name
            for case_id in normalized_case_ids
            if (
                    cases[case_id].project_product is None
                    or cases[case_id].project_product.project_product is None
            )
        ]
        if unbound_case_names:
            raise AutoPytestError(PYTEST_PROJECT_PRODUCT_BINDING_INVALID,
                                  value=('、'.join(unbound_case_names),),
                                  )

        BatchExecutionValidationService.ensure_same_project(
            (
                (
                    cases[case_id].project_product.project_product.project_id,
                    cases[case_id].project_product.project_product.project.name,
                )
                for case_id in normalized_case_ids
            ),
            error_class=AutoPytestError,
            error_message=PYTEST_CASE_EXECUTION_INVALID,
        )
        execution_groups: dict[tuple, dict] = {}
        repository_refs: dict[int | None, dict] = {}
        for case_id in normalized_case_ids:
            case = cases[case_id]
            if case.asset_status in {
                PytestAssetStatusEnum.DISABLED.value,
                PytestAssetStatusEnum.ARCHIVED.value,
                PytestAssetStatusEnum.IGNORED.value,
            }:
                raise AutoPytestError(PYTEST_FILE_EXECUTION_NOT_ALLOWED)
            git_service = RepositoryGitService.for_product(case.project_product)
            if (
                    case.source_status in {
                PytestSourceStatusEnum.MISSING.value,
                PytestSourceStatusEnum.PARSE_FAILED.value,
                PytestSourceStatusEnum.CONFLICT.value,
            }
                    or not git_service.repository_file_exists(case.file_path)
            ):
                raise AutoPytestError(PYTEST_FILE_PARSE_FAILED)
            product = case.project_product
            repository_id = product.repository_id
            if repository_id not in repository_refs:
                repository_refs[repository_id] = git_service.current_ref_info()
            repo_info = repository_refs[repository_id]
            group_key = (
                product.repository_id,
                repo_info.get('commit_hash'),
                product.id,
                normalized_test_env,
            )
            execution_groups.setdefault(group_key, {
                'repository_id': product.repository_id,
                'repository_name': product.repository.name,
                'pytest_project_id': product.id,
                'pytest_project_name': product.name,
                'branch': repo_info.get('branch'),
                'commit_hash': repo_info.get('commit_hash'),
                'test_env': normalized_test_env,
                'case_ids': [],
            })['case_ids'].append(case_id)

        first_case = cases[normalized_case_ids[0]]
        add_tasks = AddTasks(
            project_product=first_case.project_product.project_product_id,
            test_env=normalized_test_env,
            is_notice=StatusEnum.FAIL.value,
            user_id=user_id,
        )
        for case_id in normalized_case_ids:
            add_tasks.add_test_suite_details(case_id, TestCaseTypeEnum.PYTEST)
        return {
            'case_ids': normalized_case_ids,
            'test_env': normalized_test_env,
            'test_suite_id': add_tasks.test_suite_id,
            'execution_group_count': len(execution_groups),
            'repository_count': len({group[0] for group in execution_groups}),
            'execution_groups': list(execution_groups.values()),
        }

    @staticmethod
    def normalize_case_ids(case_ids) -> list[int]:
        return BatchExecutionValidationService.normalize_case_ids(
            case_ids,
            error_class=AutoPytestError,
            error_message=PYTEST_EXECUTION_DUPLICATED,
        )

    @staticmethod
    def normalize_test_env(test_env) -> int:
        return BatchExecutionValidationService.normalize_test_environment(
            test_env,
            error_class=AutoPytestError,
            error_message=PYTEST_TEST_ENVIRONMENT_EXECUTION_REQUIRED,
        )

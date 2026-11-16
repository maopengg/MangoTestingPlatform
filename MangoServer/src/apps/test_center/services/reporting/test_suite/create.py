from src.apps.test_center.models import TestSuite, TestSuiteDetails
from src.apps.task_center.enums.execution import ReportRetentionPolicyEnum
from src.apps.task_center.models import Tasks
from src.apps.system.services.configuration.system_config import SystemConfigService
from src.apps.test_center.enums import TestCaseTypeEnum


class TestSuiteCreateService:
    """Create execution records without depending on the HTTP CRUD layer."""

    @staticmethod
    def create_suite(
            *,
            suite_id: int,
            project_product_id: int,
            module_id: int | None,
            test_env: int,
            execution_scenes: list[str],
            execution_scope: str,
            user_id: int,
            status: int,
            is_notice: int,
            task_id: int | None,
            execution_name: str | None,
            api_concurrency_limit: int | None,
    ) -> TestSuite:
        return TestSuite.objects.create(
            id=suite_id,
            project_product_id=project_product_id,
            module_id=module_id,
            test_env=test_env,
            execution_scenes=execution_scenes,
            execution_scope=execution_scope,
            user_id=user_id,
            status=status,
            is_notice=is_notice,
            tasks_id=task_id,
            execution_name=execution_name,
            api_concurrency_limit=api_concurrency_limit,
            api_count_by_scenario=SystemConfigService.get('API_REPORT_COUNT_BY_SCENARIO', default=True),
            report_retention_policy=(Tasks.objects.filter(id=task_id).values_list(
                'report_retention_policy', flat=True).first() or ReportRetentionPolicyEnum.ALL.value)
                if task_id else ReportRetentionPolicyEnum.ALL.value,
        )

    @staticmethod
    def create_detail(
            *,
            suite_id: int,
            case_type: int,
            project_product_id: int,
            test_env: int,
            case_id: int,
            case_name: str,
            parametrize: list,
            status: int,
            retry: int,
            case_sum: int,
            api_case_revision_id: int | None,
            api_case_release_id: int | None,
            config_checksum: str | None,
            api_count_by_scenario: bool = True,
    ) -> TestSuiteDetails:
        api = case_type == TestCaseTypeEnum.API.value
        snapshot = {'children': None, 'meta': {'api_count_by_scenario': api_count_by_scenario,
                                             'api_scene_count': case_sum}} if api else None
        return TestSuiteDetails.objects.create(
            test_suite_id=suite_id,
            type=case_type,
            project_product_id=project_product_id,
            test_env=test_env,
            case_id=case_id,
            case_name=case_name,
            parametrize=parametrize,
            status=status,
            error_message=None,
            retry=retry,
            case_sum=1 if api and not api_count_by_scenario else case_sum,
            summary_data=snapshot,
            api_case_revision_id=api_case_revision_id,
            api_case_release_id=api_case_release_id,
            config_checksum=config_checksum,
        )

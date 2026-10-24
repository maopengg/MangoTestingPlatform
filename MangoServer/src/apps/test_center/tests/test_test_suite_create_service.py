from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.test_center.services.test_suite.create import TestSuiteCreateService


class TestSuiteCreateServiceTests(SimpleTestCase):
    @patch('src.apps.test_center.services.test_suite.create.Tasks.objects.filter')
    @patch('src.apps.test_center.services.test_suite.create.TestSuite.objects.create')
    def test_create_suite_uses_model_ids_without_http_crud(self, create, tasks):
        tasks.return_value.values_list.return_value.first.return_value = 'abnormal_only'
        TestSuiteCreateService.create_suite(
            suite_id=100,
            project_product_id=2,
            module_id=3,
            test_env=1,
            execution_scenes=['regression'],
            execution_scope='manual',
            user_id=4,
            status=2,
            is_notice=0,
            task_id=5,
            execution_name='regression',
            api_concurrency_limit=6,
        )

        create.assert_called_once_with(
            id=100,
            project_product_id=2,
            module_id=3,
            test_env=1,
            execution_scenes=['regression'],
            execution_scope='manual',
            user_id=4,
            status=2,
            is_notice=0,
            tasks_id=5,
            report_retention_policy='abnormal_only',
            execution_name='regression',
            api_concurrency_limit=6,
        )

    @patch('src.apps.test_center.services.test_suite.create.TestSuiteDetails.objects.create')
    def test_create_detail_uses_model_ids_without_http_crud(self, create):
        TestSuiteCreateService.create_detail(
            suite_id=100,
            case_type=1,
            project_product_id=2,
            test_env=1,
            case_id=8,
            case_name='case',
            parametrize=[],
            status=2,
            retry=0,
            case_sum=3,
            api_case_revision_id=9,
            api_case_release_id=10,
            config_checksum='checksum',
        )

        create.assert_called_once_with(
            test_suite_id=100,
            type=1,
            project_product_id=2,
            test_env=1,
            case_id=8,
            case_name='case',
            parametrize=[],
            status=2,
            error_message=None,
            retry=0,
            case_sum=3,
            api_case_revision_id=9,
            api_case_release_id=10,
            config_checksum='checksum',
        )

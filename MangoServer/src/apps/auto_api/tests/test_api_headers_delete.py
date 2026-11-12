from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from mangotools.enums import StatusEnum

from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiHeaders
from src.apps.auto_api.services.configuration.api_header import ApiHeaderDeleteService


class ApiHeadersDeleteTestCase(SimpleTestCase):

    @staticmethod
    def _header(*, status=StatusEnum.FAIL.value):
        return ApiHeaders(id=101, status=status, project_product_id=202)

    @patch('django.db.models.Model.delete')
    @patch('src.apps.auto_api.models.ApiCaseDetailedParameter.objects.filter')
    @patch('src.apps.auto_api.models.ApiCase.objects.filter')
    def test_enabled_default_header_is_blocked_without_reference_query(
            self,
            case_filter,
            parameter_filter,
            model_delete,
    ):
        with self.assertRaisesMessage(AutoApiError, '请先关闭后再删除'):
            self._header(status=StatusEnum.SUCCESS.value).delete()

        case_filter.assert_not_called()
        parameter_filter.assert_not_called()
        model_delete.assert_not_called()

    @patch('django.db.models.Model.delete')
    @patch('src.apps.auto_api.models.ApiCaseDetailedParameter.objects.filter')
    @patch('src.apps.auto_api.models.ApiCase.objects.filter')
    def test_case_reference_blocks_delete_and_skips_parameter_query(
            self,
            case_filter,
            parameter_filter,
            model_delete,
    ):
        case_filter.return_value.exists.return_value = True

        with self.assertRaisesMessage(AutoApiError, 'API Case或场景使用'):
            self._header().delete()

        case_filter.assert_called_once_with(
            project_product_id=202,
            front_headers__contains=[101],
        )
        parameter_filter.assert_not_called()
        model_delete.assert_not_called()

    @patch('django.db.models.Model.delete')
    @patch('src.apps.auto_api.models.ApiCaseDetailedParameter.objects.filter')
    @patch('src.apps.auto_api.models.ApiCase.objects.filter')
    def test_parameter_reference_blocks_delete_with_product_scope(
            self,
            case_filter,
            parameter_filter,
            model_delete,
    ):
        case_filter.return_value.exists.return_value = False
        parameter_filter.return_value.exists.return_value = True

        with self.assertRaisesMessage(AutoApiError, 'API Case或场景使用'):
            self._header().delete()

        parameter_filter.assert_called_once_with(
            case_detailed__case__project_product_id=202,
            headers__contains=[101],
        )
        model_delete.assert_not_called()

    @patch('django.db.models.Model.delete')
    @patch('src.apps.auto_api.models.ApiCaseDetailedParameter.objects.filter')
    @patch('src.apps.auto_api.models.ApiCase.objects.filter')
    def test_unused_header_can_be_deleted(
            self,
            case_filter,
            parameter_filter,
            model_delete,
    ):
        case_filter.return_value.exists.return_value = False
        parameter_filter.return_value.exists.return_value = False
        header = self._header()

        header.delete()

        model_delete.assert_called_once_with()


class ApiHeaderBatchDeleteServiceTestCase(SimpleTestCase):

    @patch('src.apps.auto_api.services.configuration.api_header.ApiCaseDetailedParameter.objects.filter')
    @patch('src.apps.auto_api.services.configuration.api_header.ApiCase.objects.filter')
    def test_multiple_products_are_rejected_before_usage_query(
            self,
            case_filter,
            parameter_filter,
    ):
        headers = [
            SimpleNamespace(id=1, project_product_id=10, status=StatusEnum.FAIL.value),
            SimpleNamespace(id=2, project_product_id=20, status=StatusEnum.FAIL.value),
        ]

        with self.assertRaisesMessage(AutoApiError, '同一项目/产品'):
            ApiHeaderDeleteService.validate_batch(headers)

        case_filter.assert_not_called()
        parameter_filter.assert_not_called()

    @patch('src.apps.auto_api.services.configuration.api_header.ApiCaseDetailedParameter.objects.filter')
    @patch('src.apps.auto_api.services.configuration.api_header.ApiCase.objects.filter')
    def test_case_usage_short_circuits_parameter_query(
            self,
            case_filter,
            parameter_filter,
    ):
        headers = [
            SimpleNamespace(id=1, project_product_id=10, status=StatusEnum.FAIL.value),
            SimpleNamespace(id=2, project_product_id=10, status=StatusEnum.FAIL.value),
        ]
        case_filter.return_value.annotate.return_value.filter.return_value.exists.return_value = True

        with self.assertRaisesMessage(AutoApiError, 'API Case或场景使用'):
            ApiHeaderDeleteService.validate_batch(headers)

        case_filter.assert_called_once_with(project_product_id=10)
        parameter_filter.assert_not_called()

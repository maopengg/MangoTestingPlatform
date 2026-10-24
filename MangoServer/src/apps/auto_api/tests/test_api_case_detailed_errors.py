from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.api.views.api_case import ApiCaseCRUD
from src.apps.auto_api.api.views.api_case_detailed import ApiCaseDetailedCRUD
from src.apps.auto_api.exceptions import AutoApiError
from src.apps.auto_api.models import ApiCase


class ApiCaseDetailedErrorTests(SimpleTestCase):
    @patch('src.apps.auto_api.api.views.api_case_detailed.ApiCase.objects.select_for_update')
    def test_create_step_converts_missing_case_to_business_error(self, select_for_update):
        select_for_update.return_value.get.side_effect = ApiCase.DoesNotExist

        with self.assertRaisesMessage(AutoApiError, 'API用例不存在，Case ID：999999'):
            ApiCaseDetailedCRUD.get_case_for_update(999999)


class ApiCaseCrudErrorTests(SimpleTestCase):
    @patch.object(ApiCaseCRUD, 'serializer')
    @patch.object(ApiCaseCRUD, 'validate_case_config', return_value={})
    @patch.object(ApiCaseCRUD, 'split_identity_and_config', return_value=({}, {}))
    def test_internal_create_raises_tools_error_for_invalid_payload(
            self,
            _split_identity_and_config,
            _validate_case_config,
            serializer_class,
    ):
        serializer = serializer_class.return_value
        serializer.is_valid.return_value = False
        serializer.errors = {'name': ['This field is required.']}

        with self.assertRaisesMessage(AutoApiError, '内部保存失败'):
            ApiCaseCRUD._create_with_version({})

    @patch.object(ApiCaseCRUD, 'serializer')
    @patch.object(ApiCaseCRUD, 'capture_config_snapshot', return_value=SimpleNamespace(snapshot={}))
    @patch.object(ApiCaseCRUD, 'validate_case_config', return_value={})
    @patch.object(ApiCaseCRUD, 'split_identity_and_config', return_value=({}, {}))
    @patch('src.apps.auto_api.api.views.api_case.ApiCase.objects.get')
    def test_internal_update_raises_tools_error_for_invalid_payload(
            self,
            get_case,
            _split_identity_and_config,
            _validate_case_config,
            _capture_config_snapshot,
            serializer_class,
    ):
        get_case.return_value = SimpleNamespace(project_product_id=1)
        serializer = serializer_class.return_value
        serializer.is_valid.return_value = False
        serializer.errors = {'name': ['This field is required.']}

        with self.assertRaisesMessage(AutoApiError, '内部更新失败'):
            ApiCaseCRUD._update_with_version(999999, {})

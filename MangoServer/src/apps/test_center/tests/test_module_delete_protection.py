from contextlib import ExitStack, nullcontext
from types import SimpleNamespace
from unittest.mock import patch

from django.db import models
from django.db.models.deletion import ProtectedError
from django.http import QueryDict
from django.test import SimpleTestCase

from src.apps.auto_api.models import (
    ApiCase, ApiInfo, ModuleCoverageCase, ModuleCoverageInterfaceSnapshot, ModuleCoverageModuleInterface, ModuleCoverageScan,
)
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_ui.models import Page, PageSteps, UiCase
from src.apps.data_factory.models import DataFactoryEntity, DataFactoryExecution, DataFactoryTemplate
from src.apps.functional_test.models import ManualTestCase, ManualTestSuite
from src.apps.task_center.models import Tasks
from src.apps.test_center.exceptions import (
    PRODUCT_MODULE_COVERAGE_DELETE_PROTECTED, PRODUCT_MODULE_DELETE_PROTECTED, TestCenterError,
)
from src.apps.test_center.models import ProductModule
from src.common.responses.model_crud import ModelCRUD


class ModuleDeleteProtectionTests(SimpleTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.module = ProductModule(id=1, project_product_id=2, name='示例模块')
        self.stack.enter_context(patch.object(ProductModule, 'children', SimpleNamespace(exists=lambda: False)))
        for model in (ApiInfo, ApiCase, UiCase, Page, PageSteps, PytestCase, DataFactoryEntity,
                      DataFactoryTemplate, DataFactoryExecution, Tasks, ManualTestSuite, ManualTestCase):
            query = self.stack.enter_context(patch.object(model.objects, 'filter'))
            query.return_value.exists.return_value = False

    def test_coverage_references_remain_protected_and_raise_business_error(self):
        for model in (ModuleCoverageScan, ModuleCoverageModuleInterface, ModuleCoverageInterfaceSnapshot, ModuleCoverageCase):
            with self.subTest(model=model.__name__):
                self.assertIs(model._meta.get_field('module').remote_field.on_delete, models.PROTECT)
                related = model(id=7, module=self.module)
                original = ProtectedError('internal relation details', {related})
                with patch.object(models.Model, 'delete', side_effect=original):
                    with self.assertRaises(TestCenterError) as error:
                        self.module.delete()
                self.assertEqual(error.exception.code, PRODUCT_MODULE_COVERAGE_DELETE_PROTECTED.code)
                self.assertIn('覆盖', error.exception.msg)
                self.assertNotIn('internal relation details', error.exception.msg)

    def test_other_protected_relation_is_not_misreported_as_coverage(self):
        with patch.object(models.Model, 'delete', side_effect=ProtectedError('private details', {self.module})):
            with self.assertRaises(TestCenterError) as error:
                self.module.delete()
        self.assertEqual(error.exception.code, PRODUCT_MODULE_DELETE_PROTECTED.code)
        self.assertNotIn('private details', error.exception.msg)

    def test_empty_module_still_deletes_normally(self):
        with patch.object(models.Model, 'delete') as delete:
            self.module.delete()
        delete.assert_called_once_with()

    def test_http_delete_returns_business_message_without_recording_internal_error(self):
        crud = ModelCRUD()
        crud.model = ProductModule
        request = SimpleNamespace(query_params=QueryDict('id=1'), user={'id': 7})
        related = ModuleCoverageScan(id=7, module=self.module)
        manager = SimpleNamespace(get=lambda **kwargs: self.module)
        with patch.object(ProductModule._default_manager, 'using') as using, \
                patch('src.common.responses.model_crud.transaction.atomic', return_value=nullcontext()), \
                patch.object(crud, 'has_instance_data_scope_permission', return_value=True), \
                patch.object(crud, 'capture_config_snapshot', return_value=SimpleNamespace(snapshot={})), \
                patch.object(models.Model, 'delete', side_effect=ProtectedError('private details', {related})), \
                patch('src.common.decorators.error_response.report_system_error') as record:
            using.return_value.select_for_update.return_value = manager
            response = crud.delete(request)
        self.assertEqual(response.data['code'], PRODUCT_MODULE_COVERAGE_DELETE_PROTECTED.code)
        self.assertIn('覆盖', response.data['msg'])
        self.assertNotIn('private details', response.data['msg'])
        record.assert_not_called()

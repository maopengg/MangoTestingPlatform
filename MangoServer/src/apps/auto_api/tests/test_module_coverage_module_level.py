from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.auto_api.models import ModuleCoverageCase, ModuleCoverageInterfaceSnapshot
from src.apps.auto_api.services.coverage.module_coverage import ModuleCoverageService as Service
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.models import ProductModule
from src.apps.test_center.services.project.product_module import ProductModuleService


class CoverageModuleLevelTests(SimpleTestCase):
    def test_shared_binding_guard_rejects_parent_and_accepts_third_level(self):
        for level in (1, 2, 3):
            with self.subTest(level=level), patch.object(ProductModule.objects, 'filter') as query:
                query.return_value.exists.return_value = level == 3
                if level == 3:
                    ProductModuleService.validate_business_binding(9)
                else:
                    with self.assertRaises(TestCenterError) as error:
                        ProductModuleService.validate_business_binding(9)
                    self.assertIn('选择三级模块', error.exception.msg)
                query.assert_called_once_with(id=9, level=3)

    def test_scan_scope_still_accepts_parent_but_upload_requires_third_level(self):
        scan = SimpleNamespace(project_product_id=1, module_id=2, include_descendants=True)
        with patch.object(ProductModule.objects, 'filter') as query:
            query.return_value.exists.return_value = True
            Service.validate_module(1, 2)
            query.assert_called_once_with(id=2, project_product_id=1)
        with patch.object(Service, 'validate_module'), \
                patch.object(ProductModule.objects, 'filter') as query, \
                patch.object(Service, 'module_ids') as descendants:
            query.return_value.exists.return_value = False
            with self.assertRaises(TestCenterError):
                Service.validate_module_scope(scan, 2)
            descendants.assert_not_called()

    def test_project_interface_upload_cannot_bypass_binding_level(self):
        scan = SimpleNamespace(project_product_id=1, module_id=None, scope_type='project', summary={})
        with patch.object(Service, 'get_locked_uploading_scan', return_value=scan), \
                patch.object(Service, 'validate_module'), \
                patch.object(ProductModule.objects, 'filter') as query, \
                patch.object(ModuleCoverageInterfaceSnapshot.objects, 'create') as create:
            query.return_value.exists.return_value = False
            with self.assertRaises(TestCenterError):
                Service.upload_interfaces.__wrapped__(Service, 1, [
                    {'source_key': 'get:/api/contracts', 'module_id': 2, 'payload': {}}])
            create.assert_not_called()

    def test_changing_case_binding_on_parent_is_rejected_before_mutation(self):
        from src.apps.test_center.models import ProjectProduct
        item = SimpleNamespace(project_product_id=1, module_id=2, api_case_id=None)
        with patch.object(ModuleCoverageCase.objects, 'get', return_value=item), \
                patch.object(ModuleCoverageCase.objects, 'select_for_update') as locked, \
                patch.object(ProjectProduct.objects, 'select_for_update'), \
                patch.object(ProductModule.objects, 'filter') as query, \
                patch.object(Service, 'repair_case_target') as repair:
            locked.return_value.get.return_value = item
            query.return_value.exists.return_value = False
            with self.assertRaises(TestCenterError):
                Service.bind_api_case.__wrapped__(Service, 5, 6)
            repair.assert_not_called()

from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase
from django.utils.module_loading import import_string

from src.apps.test_center.services.product_module import ProductModuleService


class ModelCrudValidatorImportTests(SimpleTestCase):
    @patch.object(ProductModuleService, "validate_crud_binding")
    def test_module_validator_setting_resolves_to_callable(self, validate_crud_binding):
        validator = import_string(settings.MODEL_CRUD_MODULE_VALIDATOR)
        model = object()
        data = {"module": 1}
        instance = object()

        validator(model, data, instance)

        self.assertTrue(callable(validator))
        validate_crud_binding.assert_called_once_with(model, data, instance)

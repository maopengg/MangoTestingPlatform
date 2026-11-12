from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector


class DatasourceBindingSelectorTests(SimpleTestCase):
    @patch('src.apps.user.services.authorization.permission.PermissionMenuService.is_effective_super_admin', return_value=True)
    @patch('src.apps.data_factory.selectors.querysets.DataFactoryDatasourceBinding.objects.filter')
    def test_binding_list_includes_project_and_product_names(self, filter_bindings, is_super_admin):
        DataFactoryQuerySelector.database_bindings(1, user=object())

        filter_bindings.assert_called_once_with(database_id=1)
        fields = filter_bindings.return_value.values.call_args.args
        self.assertIn('datasource_alias__project_product__name', fields)
        self.assertIn('datasource_alias__project_product__project__name', fields)

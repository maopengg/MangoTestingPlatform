from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from src.apps.test_center.api.serializers.project_product import ProjectProductSerializers, ProjectProductSerializersC
from src.apps.test_center.models import ProjectProduct
from src.apps.user.services.permission import PermissionMenuService
from src.interfaces.mcp.tools.project.context import register_project_context_tools


class ProductDescriptionTests(SimpleTestCase):
    def test_optional_model_and_rest_field_contract(self):
        field = ProjectProduct._meta.get_field('description')
        self.assertEqual(field.verbose_name, '产品说明')
        self.assertTrue(field.blank)
        self.assertEqual(field.default, '')
        text = '订单管理与审批\nGit: https://git.example.com/team/product.git'
        for serializer in (ProjectProductSerializers(), ProjectProductSerializersC()):
            description = serializer.fields['description']
            self.assertFalse(description.required)
            self.assertEqual(description.run_validation(text), text)
            self.assertEqual(description.run_validation(''), '')
            with self.assertRaises(ValidationError):
                description.run_validation('x' * 5001)

    def test_menu_label_changes_without_changing_permission_identity(self):
        def flatten(items):
            for item in items:
                yield item
                yield from flatten(item.get('children', []))
        page = next(item for item in flatten(PermissionMenuService.permission_tree())
                    if item['menuUrl'] == '/config/product/index')
        self.assertEqual(page['menuName'], '产品配置')
        self.assertEqual(page['permissionKey'], 'config.product')

    def test_mcp_product_list_includes_description(self):
        tools = {}

        class Registry:
            def tool(self):
                def register(function):
                    tools[function.__name__] = function
                    return function
                return register

        register_project_context_tools(Registry())
        product = SimpleNamespace(id=7, name='示例产品', description='用途与仓库说明',
                                  project=SimpleNamespace(id=1, name='示例项目'),
                                  owners=MagicMock(), api_client_type=0, ui_client_type=0)
        product.owners.all.return_value = []
        with patch('src.interfaces.mcp.tools.project.context._project_product_queryset_for_current_user'), \
                patch('src.interfaces.mcp.tools.project.context.paginate_queryset', return_value=([product], 1, 1, 10)):
            result = tools['list_project_products']()
        self.assertEqual(result['data']['items'][0]['description'], product.description)

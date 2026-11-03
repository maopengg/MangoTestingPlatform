from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.test_center.api.serializers.product_module_mutation import ProductModuleSerializers
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.models import ProductModule, ProjectProduct


class ProductModuleNodeValidationTests(SimpleTestCase):
    def setUp(self):
        self.product = SimpleNamespace(id=10)
        self.root = SimpleNamespace(id=1, name='一级', level=1, parent=None, project_product_id=10)
        self.parent = SimpleNamespace(id=2, name='二级', level=2, parent=self.root, project_product_id=10)

    def validate(self, **overrides):
        attrs = {'project_product': self.product, 'name': '新模块', **overrides}
        with patch('src.apps.test_center.api.serializers.product_module_mutation.ProductModule.objects.filter') as query:
            query.return_value.exists.return_value = False
            return ProductModuleSerializers().validate(attrs)

    def test_root_and_children_derive_levels_from_parent(self):
        self.assertEqual(self.validate()['level'], 1)
        self.assertEqual(self.validate(parent=self.root)['level'], 2)
        self.assertEqual(self.validate(parent=self.parent)['level'], 3)

    def test_serializer_accepts_single_node_http_payload(self):
        product = ProjectProduct(id=10, name='测试产品')
        parent = ProductModule(id=1, name='一级', level=1, project_product=product)
        for parent_id in (None, 1):
            serializer = ProductModuleSerializers(data={
                'project_product': 10, 'parent': parent_id, 'name': ' 新模块 ',
            })
            with patch.object(serializer.fields['project_product'], 'run_validation', return_value=product), \
                    patch.object(serializer.fields['parent'], 'run_validation', return_value=parent if parent_id else None), \
                    patch('src.apps.test_center.api.serializers.product_module_mutation.ProductModule.objects.filter') as query:
                query.return_value.exists.return_value = False
                self.assertTrue(serializer.is_valid(), serializer.errors)
            self.assertEqual(serializer.validated_data['name'], '新模块')
            self.assertEqual(serializer.validated_data['level'], 2 if parent_id else 1)

    def test_cross_product_parent_is_rejected(self):
        self.root.project_product_id = 99
        with self.assertRaises(TestCenterError):
            self.validate(parent=self.root)

    def test_fourth_level_and_inconsistent_level_are_rejected(self):
        leaf = SimpleNamespace(id=3, level=3, project_product_id=10)
        for payload in ({'parent': leaf}, {'parent': self.root, 'level': 3}, {'level': 2}):
            with self.subTest(payload=payload), self.assertRaises(TestCenterError):
                self.validate(**payload)

    def test_duplicate_name_is_rejected(self):
        with patch('src.apps.test_center.api.serializers.product_module_mutation.ProductModule.objects.filter') as query:
            query.return_value.exists.return_value = True
            with self.assertRaises(TestCenterError):
                ProductModuleSerializers().validate({'project_product': self.product, 'name': '重复名称'})

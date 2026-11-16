from unittest.mock import patch

from django.test import SimpleTestCase

from src.apps.test_center.services.project.project_product_cache import ProjectProductCacheService


class ProductOptionDescriptionTests(SimpleTestCase):
    def test_cached_product_options_include_description_in_the_existing_query(self):
        with patch('src.apps.test_center.models.ProjectProduct.objects.filter') as products:
            products.return_value.values_list.return_value = [
                (10, '示例产品', '第一行说明\n第二行说明'),
                (11, '无说明产品', None),
            ]
            result = ProjectProductCacheService._load_options(1)
        products.assert_called_once_with(project_id=1)
        products.return_value.values_list.assert_called_once_with('id', 'name', 'description')
        self.assertEqual(result, [
            {'value': 10, 'label': '示例产品', 'description': '第一行说明\n第二行说明'},
            {'value': 11, 'label': '无说明产品', 'description': ''},
        ])

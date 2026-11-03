from unittest.mock import Mock

from django.test import SimpleTestCase
from rest_framework import serializers

from src.apps.test_center.models import ProjectProduct
from src.common.validators.serializer_fields import RelatedObjectField
from src.common.validators.serializer_fields import MAX_RELATED_REPRESENTATIONS


class RelatedObjectCacheTests(SimpleTestCase):
    @staticmethod
    def serializer(formatter, *, cache=True):
        render = lambda value: formatter(value)
        class Holder(serializers.Serializer):
            product = RelatedObjectField(formatter=render, cache_representation=cache)
        return Holder

    def test_repeated_product_formats_once_but_results_do_not_share_mutable_data(self):
        formatter = Mock(return_value={'id': 1, 'owners': [{'name': '示例用户'}]})
        serializer = self.serializer(formatter)
        data = [{'product': ProjectProduct(id=1)}, {'product': ProjectProduct(id=1)}]
        result = serializer(data, many=True).data
        formatter.assert_called_once()
        result[0]['product']['owners'][0]['name'] = 'changed'
        self.assertEqual(result[1]['product']['owners'][0]['name'], '示例用户')
        self.assertEqual(serializer(data, many=True).data[0]['product']['owners'][0]['name'], '示例用户')
        self.assertEqual(formatter.call_count, 2)

    def test_different_databases_and_ids_do_not_share_cached_results(self):
        formatter = Mock(side_effect=lambda value: {'id': value.pk})
        first = ProjectProduct(id=1)
        other_database = ProjectProduct(id=1)
        other_database._state.db = 'other'
        data = [{'product': first}, {'product': ProjectProduct(id=2)}, {'product': other_database}]
        self.serializer(formatter)(data, many=True).data
        self.assertEqual(formatter.call_count, 3)

    def test_unsaved_objects_and_non_opted_in_fields_keep_existing_behavior(self):
        for cache, values in ((True, [ProjectProduct(), ProjectProduct()]),
                              (False, [ProjectProduct(id=1), ProjectProduct(id=1)])):
            with self.subTest(cache=cache):
                formatter = Mock(return_value={'name': 'example'})
                self.serializer(formatter, cache=cache)([{'product': value} for value in values], many=True).data
                self.assertEqual(formatter.call_count, 2)

    def test_many_distinct_products_do_not_grow_the_cache_without_bound(self):
        formatter = Mock(side_effect=lambda value: {'id': value.pk})
        products = [ProjectProduct(id=index) for index in range(1, MAX_RELATED_REPRESENTATIONS + 10)]
        serializer = self.serializer(formatter)([{'product': value} for value in products], many=True)
        result = serializer.data
        self.assertEqual(len(result), len(products))
        self.assertEqual(len(serializer.context['_mango_related_representation_cache']), MAX_RELATED_REPRESENTATIONS)

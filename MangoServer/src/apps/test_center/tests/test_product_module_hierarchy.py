from types import SimpleNamespace

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import serializers
from rest_framework.test import APIRequestFactory

from src.apps.test_center.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.test_center.api.serializers.product_module_mutation import ProductModuleSerializers
from src.apps.test_center.api.views.project import ProjectViews
from src.apps.test_center.exceptions import TestCenterError
from src.apps.test_center.models import ProductModule, Project, ProjectProduct
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.test_center.services.product_module_cache import ProductModuleCacheService
from src.apps.test_center.services.project_product_cache import ProjectProductCacheService


class ModuleBindingSerializer(ProductModuleBindingSerializerMixin, serializers.Serializer):
    module = serializers.PrimaryKeyRelatedField(queryset=ProductModule.objects.all())


@override_settings(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'product-module-tests',
    }
})
class ProductModuleHierarchyTests(TestCase):
    def setUp(self):
        cache.clear()
        project = Project.objects.create(name='三级模块规则测试项目')
        self.product = ProjectProduct.objects.create(project=project, name='测试产品')

    def test_create_path_creates_complete_three_level_hierarchy(self):
        module = ProductModuleService.create_path(
            self.product.id,
            '一级分类',
            '二级分类',
            '三级业务模块',
        )

        self.assertEqual(module.level, 3)
        self.assertEqual(module.parent.level, 2)
        self.assertEqual(module.parent.parent.level, 1)
        self.assertEqual(module.parent.parent.parent_id, None)

    def test_full_path_uses_parent_hierarchy(self):
        module = ProductModuleService.create_path(
            self.product.id,
            '订单创建',
            '本地文件创建',
            '订单编辑',
        )
        ProductModule.objects.filter(id=module.id).update(
            superior_module_1='错误一级模块',
            superior_module_2='错误二级模块',
        )
        module.refresh_from_db()

        self.assertEqual(module.get_full_path(), '订单创建/本地文件创建/订单编辑')
        self.assertEqual(
            ProductModuleSerializers(instance=module).data['full_path'],
            '订单创建/本地文件创建/订单编辑',
        )

    def test_single_module_create_is_rejected(self):
        serializer = ProductModuleSerializers(data={
            'project_product': self.product.id,
            'name': '单层模块',
        })

        with self.assertRaises(TestCenterError):
            serializer.is_valid()

    def test_existing_module_cannot_change_to_wrong_level_parent(self):
        module = ProductModuleService.create_path(
            self.product.id,
            '固定一级',
            '固定二级',
            '固定三级',
        )
        serializer = ProductModuleSerializers(
            instance=module,
            data={'parent': module.parent.parent_id},
            partial=True,
        )

        with self.assertRaises(TestCenterError):
            serializer.is_valid()

    def test_existing_module_can_change_to_same_level_parent(self):
        module = ProductModuleService.create_path(
            self.product.id,
            '原一级',
            '原二级',
            '原三级',
        )
        target_parent = ProductModuleService.create_path(
            self.product.id,
            '新一级',
            '新二级',
            '占位三级',
        ).parent
        serializer = ProductModuleSerializers(
            instance=module,
            data={'parent': target_parent.id},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()

        self.assertEqual(updated.parent_id, target_parent.id)
        self.assertEqual(updated.level, 3)
        self.assertEqual(updated.superior_module_1, '新一级')
        self.assertEqual(updated.superior_module_2, '新二级')

    def test_new_binding_only_accepts_level_three(self):
        level_1 = ProductModule.objects.create(
            project_product=self.product,
            name='历史一级模块',
            level=1,
        )
        level_3 = ProductModuleService.create_path(
            self.product.id,
            '新一级分类',
            '新二级分类',
            '新三级模块',
        )

        with self.assertRaises(TestCenterError):
            ModuleBindingSerializer(data={'module': level_1.id}).is_valid()
        self.assertTrue(ModuleBindingSerializer(data={'module': level_3.id}).is_valid())

    def test_unchanged_legacy_binding_remains_editable(self):
        level_1 = ProductModule.objects.create(
            project_product=self.product,
            name='历史绑定模块',
            level=1,
        )
        serializer = ModuleBindingSerializer(
            instance=SimpleNamespace(module_id=level_1.id),
            data={'module': level_1.id},
        )

        self.assertTrue(serializer.is_valid())

    def test_module_tree_cache_is_isolated_by_project_product(self):
        other_product = ProjectProduct.objects.create(
            project=self.product.project,
            name='其他产品',
        )
        calls = []

        first = ProductModuleCacheService.get_tree(
            self.product.id,
            lambda: calls.append(self.product.id) or [{'id': 1}],
        )
        second = ProductModuleCacheService.get_tree(
            self.product.id,
            lambda: calls.append(self.product.id) or [{'id': 2}],
        )
        other = ProductModuleCacheService.get_tree(
            other_product.id,
            lambda: calls.append(other_product.id) or [{'id': 3}],
        )

        self.assertEqual(first, [{'id': 1}])
        self.assertEqual(second, first)
        self.assertEqual(other, [{'id': 3}])
        self.assertEqual(calls, [self.product.id, other_product.id])

    def test_module_save_clears_product_module_cache_after_commit(self):
        cache.set(ProductModuleCacheService.tree_key(self.product.id), [{'stale': True}], 300)
        cache.set(ProductModuleCacheService.name_key(self.product.id), [{'stale': True}], 300)

        with self.captureOnCommitCallbacks(execute=True):
            ProductModule.objects.create(
                project_product=self.product,
                name='触发缓存清理',
                level=1,
            )

        self.assertIsNone(cache.get(ProductModuleCacheService.tree_key(self.product.id)))
        self.assertIsNone(cache.get(ProductModuleCacheService.name_key(self.product.id)))

    def test_product_save_clears_product_module_cache_after_commit(self):
        cache.set(ProductModuleCacheService.tree_key(self.product.id), [{'stale': True}], 300)
        cache.set(ProductModuleCacheService.name_key(self.product.id), [{'stale': True}], 300)

        with self.captureOnCommitCallbacks(execute=True):
            self.product.name = '更新后的测试产品'
            self.product.save(update_fields=['name', 'update_time'])

        self.assertIsNone(cache.get(ProductModuleCacheService.tree_key(self.product.id)))
        self.assertIsNone(cache.get(ProductModuleCacheService.name_key(self.product.id)))

    def test_project_product_options_cache_is_isolated_by_project(self):
        other_project = Project.objects.create(name='其他项目')
        calls = []

        first = ProjectProductCacheService.get_options(
            self.product.project_id,
            lambda: calls.append(self.product.project_id) or [{'value': self.product.id}],
        )
        second = ProjectProductCacheService.get_options(
            self.product.project_id,
            lambda: calls.append(self.product.project_id) or [{'value': -1}],
        )
        other = ProjectProductCacheService.get_options(
            other_project.id,
            lambda: calls.append(other_project.id) or [],
        )

        self.assertEqual(first, [{'value': self.product.id}])
        self.assertEqual(second, first)
        self.assertEqual(other, [])
        self.assertEqual(calls, [self.product.project_id, other_project.id])

    def test_product_save_clears_old_and_new_project_options_cache_after_commit(self):
        old_project_id = self.product.project_id
        new_project = Project.objects.create(name='产品迁移目标项目')
        cache.set(ProjectProductCacheService.key(old_project_id), [{'stale': True}], 300)
        cache.set(ProjectProductCacheService.key(new_project.id), [{'stale': True}], 300)

        with self.captureOnCommitCallbacks(execute=True):
            self.product.project = new_project
            self.product.save(update_fields=['project', 'update_time'])

        self.assertIsNone(cache.get(ProjectProductCacheService.key(old_project_id)))
        self.assertIsNone(cache.get(ProjectProductCacheService.key(new_project.id)))

    def test_product_create_clears_project_options_cache_after_commit(self):
        project = Project.objects.create(name='新增产品所属项目')
        cache.set(ProjectProductCacheService.key(project.id), [{'stale': True}], 300)

        with self.captureOnCommitCallbacks(execute=True):
            ProjectProduct.objects.create(project=project, name='新产品')

        self.assertIsNone(cache.get(ProjectProductCacheService.key(project.id)))

    def test_product_delete_clears_project_options_cache_after_commit(self):
        project_id = self.product.project_id
        cache.set(ProjectProductCacheService.key(project_id), [{'stale': True}], 300)

        with self.captureOnCommitCallbacks(execute=True):
            self.product.delete()

        self.assertIsNone(cache.get(ProjectProductCacheService.key(project_id)))

    def test_project_save_clears_project_options_cache_after_commit(self):
        project = self.product.project
        cache.set(ProjectProductCacheService.key(project.id), [{'stale': True}], 300)

        with self.captureOnCommitCallbacks(execute=True):
            project.name = '更新后的项目名称'
            project.save(update_fields=['name', 'update_time'])

        self.assertIsNone(cache.get(ProjectProductCacheService.key(project.id)))

    def test_project_delete_clears_project_options_cache_after_commit(self):
        project = Project.objects.create(name='待删除空项目')
        project_id = project.id
        cache.set(ProjectProductCacheService.key(project_id), [{'stale': True}], 300)

        with self.captureOnCommitCallbacks(execute=True):
            project.delete()

        self.assertIsNone(cache.get(ProjectProductCacheService.key(project_id)))

    def test_product_config_project_options_include_enabled_project_without_product(self):
        empty_project = Project.objects.create(name='没有产品的启用项目')
        disabled_project = Project.objects.create(name='停用项目', status=0)
        request = APIRequestFactory().get('/api/system/product/project-options')

        response = ProjectViews.as_view({'get': 'product_config_project_options'})(request)
        option_names = [item['title'] for item in response.data['data']]

        self.assertIn(empty_project.name, option_names)
        self.assertIn(self.product.project.name, option_names)
        self.assertNotIn(disabled_project.name, option_names)

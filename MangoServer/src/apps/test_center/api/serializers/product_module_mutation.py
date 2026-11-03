from django.db import transaction
from rest_framework import serializers

from src.apps.test_center.exceptions import (
    SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_NOT_ALLOWED,
    SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_INVALID,
    TEST_CENTER_PRODUCT_MODULE_MODULE_NAME_DUPLICATED,
    TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED,
    TEST_CENTER_PRODUCT_MODULE_PROJECT_PRODUCT_MODULE_INVALID,
    TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID,
    TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID_CODE_MODULE_INVALID,
    TEST_CENTER_PRODUCT_MODULE_PROJECT_PRODUCT_MODULE_NOT_ALLOWED,
    TEST_CENTER_PRODUCT_MODULE_MODULE_SAVE_NOT_ALLOWED,
    TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED_CODE_MODULE_NOT_ALLOWED,
    TestCenterError,
)
from src.apps.test_center.models import ProductModule


class ProductModuleSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    full_path = serializers.CharField(source='get_full_path', read_only=True)

    class Meta:
        model = ProductModule
        fields = '__all__'

    def validate(self, attrs):
        instance = self.instance
        if instance and (
                (
                        'project_product' in attrs
                        and getattr(attrs.get('project_product'), 'id', None) != instance.project_product_id
                )
                or ('level' in attrs and attrs.get('level') != instance.level)
        ):
            raise TestCenterError(SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_NOT_ALLOWED)
        parent = attrs.get('parent', getattr(instance, 'parent', None))
        project_product = attrs.get('project_product', getattr(instance, 'project_product', None))
        level = attrs.get('level', getattr(instance, 'level', None))

        if parent:
            if instance and parent.id == instance.id:
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED)
            if parent.project_product_id != getattr(project_product, 'id', project_product):
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_PROJECT_PRODUCT_MODULE_INVALID)
            expected_level = (parent.level or 0) + 1
            if expected_level not in (2, 3):
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID)
            if instance is None and level is not None and level != expected_level:
                raise TestCenterError(SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_INVALID)
            if instance and expected_level != instance.level:
                raise TestCenterError(SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_INVALID)
            if expected_level == 3 and (
                    parent.parent is None
                    or parent.parent.level != 1
                    or parent.parent.project_product_id != parent.project_product_id
            ):
                raise TestCenterError(SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_INVALID)
            attrs['level'] = expected_level
            if instance:
                ancestor = parent
                while ancestor:
                    if ancestor.id == instance.id:
                        raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED_CODE_MODULE_NOT_ALLOWED)
                    ancestor = ancestor.parent
        else:
            attrs['level'] = level or 1
            if attrs['level'] != 1:
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID_CODE_MODULE_INVALID)

        if attrs['level'] == 1:
            attrs['superior_module_1'] = None
            attrs['superior_module_2'] = None
        elif attrs['level'] == 2:
            attrs['superior_module_1'] = parent.name
            attrs['superior_module_2'] = None
        else:
            attrs['superior_module_1'] = parent.parent.name
            attrs['superior_module_2'] = parent.name

        name = attrs.get('name', getattr(instance, 'name', None))
        if instance and instance.children.exists():
            if project_product and instance.project_product_id != getattr(project_product, 'id', project_product):
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_PROJECT_PRODUCT_MODULE_NOT_ALLOWED)
            if attrs['level'] + self._descendant_depth(instance) > 3:
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_SAVE_NOT_ALLOWED)
        duplicate = ProductModule.objects.filter(
            project_product=project_product,
            parent=parent,
            name=name,
        )
        if instance:
            duplicate = duplicate.exclude(id=instance.id)
        if duplicate.exists():
            raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_NAME_DUPLICATED)
        return attrs

    @staticmethod
    def _descendant_depth(instance):
        children = list(instance.children.all())
        if not children:
            return 0
        return 1 + max(ProductModuleSerializers._descendant_depth(child) for child in children)

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        self._sync_descendant_levels(instance)
        return instance

    @classmethod
    def _sync_descendant_levels(cls, parent):
        children = list(parent.children.all())
        changed = []
        for child in children:
            expected_level = (parent.level or 1) + 1
            if child.level != expected_level:
                child.level = expected_level
            superior_module_1 = parent.name if expected_level == 2 else parent.parent.name
            superior_module_2 = None if expected_level == 2 else parent.name
            if (
                    child.superior_module_1 != superior_module_1
                    or child.superior_module_2 != superior_module_2
            ):
                child.superior_module_1 = superior_module_1
                child.superior_module_2 = superior_module_2
            changed.append(child)
        if changed:
            ProductModule.objects.bulk_update(
                changed,
                ['level', 'superior_module_1', 'superior_module_2'],
            )
        for child in children:
            cls._sync_descendant_levels(child)

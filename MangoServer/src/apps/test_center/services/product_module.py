from django.db import models, transaction
from django.db.models import Q

from src.apps.test_center.exceptions import (
    SYSTEM_MODULE_MODULE_BINDING_INVALID,
    SYSTEM_MODULE_MODULE_NAME_REQUIRED,
    SYSTEM_MODULE_MODULE_CREATE_DUPLICATED,
    SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_NOT_ALLOWED,
    SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_INVALID,
    TEST_CENTER_PRODUCT_MODULE_MODULE_NAME_DUPLICATED,
    TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED,
    TEST_CENTER_PRODUCT_MODULE_PROJECT_PRODUCT_MODULE_INVALID,
    TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID,
    TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID_CODE_MODULE_INVALID,
    TEST_CENTER_PRODUCT_MODULE_MODULE_SAVE_NOT_ALLOWED,
    TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED_CODE_MODULE_NOT_ALLOWED,
    TestCenterError,
)
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.common.database import save_model


class ProductModuleService:
    @staticmethod
    def validate_crud_binding(model, data: dict, instance=None) -> None:
        try:
            module_field = model._meta.get_field("module")
        except Exception:
            return
        if not isinstance(module_field, models.ForeignKey) or module_field.related_model is not ProductModule:
            return
        module_key = "module" if "module" in data else "module_id" if "module_id" in data else None
        if module_key is None:
            return
        module_id = data.get(module_key)
        if isinstance(module_id, (list, tuple)):
            module_id = module_id[-1] if module_id else None
        elif isinstance(module_id, dict):
            module_id = module_id.get("id") or module_id.get("key") or module_id.get("value")
        if module_id in (None, ""):
            return
        if instance is not None and str(getattr(instance, "module_id", "")) == str(module_id):
            return
        if not ProductModule.objects.filter(id=module_id, level=3).exists():
            raise TestCenterError(SYSTEM_MODULE_MODULE_BINDING_INVALID)

    @staticmethod
    def with_full_paths(queryset, *relation_fields):
        relation_fields = relation_fields or (None,)
        select_fields = []
        for relation_field in relation_fields:
            prefix = f'{relation_field}__' if relation_field else ''
            if relation_field:
                select_fields.append(relation_field)
            select_fields.extend([
                f'{prefix}parent',
                f'{prefix}parent__parent',
            ])
        return queryset.select_related(*select_fields)

    @staticmethod
    def module_scope_ids(module_id: int | None) -> list[int]:
        if not module_id:
            return []
        return list(
            ProductModule.objects.filter(
                Q(id=module_id) | Q(parent_id=module_id) | Q(parent__parent_id=module_id)
            ).values_list('id', flat=True)
        )

    @staticmethod
    @transaction.atomic
    def update(module_id: int, payload: dict) -> ProductModule:
        instance = ProductModule.objects.select_for_update().get(id=module_id)
        normalized = ProductModuleService.normalize_update(instance, payload)
        instance = save_model(ProductModule, normalized, instance=instance, partial=True)
        ProductModuleService.sync_descendant_levels(instance)
        return instance

    @staticmethod
    def normalize_update(instance: ProductModule, payload: dict) -> dict:
        attrs = dict(payload)
        project_product_value = attrs.get("project_product", instance.project_product)
        project_product_id = getattr(project_product_value, "id", project_product_value)
        if "project_product" in attrs and project_product_id != instance.project_product_id:
            raise TestCenterError(SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_NOT_ALLOWED)
        if "level" in attrs and attrs["level"] != instance.level:
            raise TestCenterError(SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_NOT_ALLOWED)

        parent_value = attrs.get("parent", instance.parent)
        parent_id = getattr(parent_value, "id", parent_value)
        parent = ProductModule.objects.select_related("parent").filter(id=parent_id).first() if parent_id else None
        if parent:
            if parent.id == instance.id:
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED)
            if parent.project_product_id != instance.project_product_id:
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_PROJECT_PRODUCT_MODULE_INVALID)
            expected_level = (parent.level or 0) + 1
            if expected_level not in (2, 3):
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID)
            if expected_level != instance.level:
                raise TestCenterError(SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_INVALID)
            if expected_level == 3 and (
                    parent.parent is None
                    or parent.parent.level != 1
                    or parent.parent.project_product_id != parent.project_product_id
            ):
                raise TestCenterError(SYSTEM_MODULE_PROJECT_PRODUCT_MODULE_INVALID)
            ancestor = parent
            while ancestor:
                if ancestor.id == instance.id:
                    raise TestCenterError(
                        TEST_CENTER_PRODUCT_MODULE_MODULE_NOT_ALLOWED_CODE_MODULE_NOT_ALLOWED
                    )
                ancestor = ancestor.parent
            attrs["parent"] = parent.id
            attrs["level"] = expected_level
        else:
            attrs["parent"] = None
            attrs["level"] = instance.level or 1
            if attrs["level"] != 1:
                raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_INVALID_CODE_MODULE_INVALID)

        if attrs["level"] == 1:
            attrs["superior_module_1"] = None
            attrs["superior_module_2"] = None
        elif attrs["level"] == 2:
            attrs["superior_module_1"] = parent.name
            attrs["superior_module_2"] = None
        else:
            attrs["superior_module_1"] = parent.parent.name
            attrs["superior_module_2"] = parent.name

        if instance.children.exists() and attrs["level"] + ProductModuleService.descendant_depth(instance) > 3:
            raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_SAVE_NOT_ALLOWED)
        name = attrs.get("name", instance.name)
        if ProductModule.objects.filter(
                project_product_id=instance.project_product_id,
                parent_id=parent.id if parent else None,
                name=name,
        ).exclude(id=instance.id).exists():
            raise TestCenterError(TEST_CENTER_PRODUCT_MODULE_MODULE_NAME_DUPLICATED)
        attrs.pop("project_product", None)
        return attrs

    @staticmethod
    def descendant_depth(instance: ProductModule) -> int:
        children = list(instance.children.all())
        return 0 if not children else 1 + max(ProductModuleService.descendant_depth(child) for child in children)

    @staticmethod
    def sync_descendant_levels(parent: ProductModule) -> None:
        children = list(parent.children.all())
        for child in children:
            expected_level = (parent.level or 1) + 1
            child.level = expected_level
            child.superior_module_1 = parent.name if expected_level == 2 else parent.parent.name
            child.superior_module_2 = None if expected_level == 2 else parent.name
        if children:
            ProductModule.objects.bulk_update(
                children,
                ["level", "superior_module_1", "superior_module_2"],
            )
        for child in children:
            ProductModuleService.sync_descendant_levels(child)

    @staticmethod
    @transaction.atomic
    def delete(module_id: int) -> None:
        ProductModule.objects.select_for_update().get(id=module_id).delete()

    @staticmethod
    @transaction.atomic
    def create_path(
            project_product_id: int,
            level_1_name: str,
            level_2_name: str,
            level_3_name: str,
            *,
            sort: int = 0,
            update_user_id: int | None = None,
    ) -> ProductModule:
        names = [str(name or '').strip() for name in (level_1_name, level_2_name, level_3_name)]
        if not all(names):
            raise TestCenterError(SYSTEM_MODULE_MODULE_NAME_REQUIRED)

        project_product = ProjectProduct.objects.select_for_update().get(id=project_product_id)
        level_1, _ = ProductModule.objects.get_or_create(
            project_product=project_product,
            parent=None,
            name=names[0],
            defaults={'level': 1, 'sort': 0, 'update_user_id': update_user_id},
        )
        if level_1.level != 1:
            level_1.level = 1
            level_1.save(update_fields=['level', 'update_time'])

        level_2, _ = ProductModule.objects.get_or_create(
            project_product=project_product,
            parent=level_1,
            name=names[1],
            defaults={'level': 2, 'sort': 0, 'update_user_id': update_user_id},
        )
        if level_2.level != 2:
            level_2.level = 2
            level_2.save(update_fields=['level', 'update_time'])

        if ProductModule.objects.filter(
                project_product=project_product,
                parent=level_2,
                name=names[2],
        ).exists():
            raise TestCenterError(SYSTEM_MODULE_MODULE_CREATE_DUPLICATED)
        return ProductModule.objects.create(
            project_product=project_product,
            parent=level_2,
            name=names[2],
            level=3,
            sort=sort,
            update_user_id=update_user_id,
        )


def validate_crud_module_binding(model, data: dict, instance=None) -> None:
    """Expose the module binding validator as a Django-importable callable."""
    ProductModuleService.validate_crud_binding(model, data, instance)

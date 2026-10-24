from __future__ import annotations

from src.apps.auto_ui.models import Page, PageSteps
from src.apps.test_center.models import ProjectProduct, ProductModule
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


class PageStepAssetService:
    """页面步骤资产选择器数据，供用例详情跨产品拼接步骤使用。"""

    @classmethod
    def product_options(cls, request) -> list[dict]:
        product_ids = PageSteps.objects.values_list("project_product_id", flat=True).distinct()
        queryset = ProjectProduct.objects.select_related("project").filter(id__in=product_ids)
        queryset = cls._filter_product_by_user_scope(request, queryset).order_by("project__id", "id")
        project_map: dict[int, dict] = {}
        for product in queryset:
            project = product.project
            project_node = project_map.setdefault(
                project.id,
                {
                    "key": f"project:{project.id}",
                    "value": f"project:{project.id}",
                    "title": project.name,
                    "label": project.name,
                    "id": project.id,
                    "node_type": "project",
                    "children": [],
                },
            )
            project_node["children"].append(
                {
                    "key": product.id,
                    "value": product.id,
                    "title": product.name,
                    "label": product.name,
                    "id": product.id,
                    "node_type": "project_product",
                    "project_id": project.id,
                    "project_name": project.name,
                    "full_title": f"{project.name} / {product.name}",
                }
            )
        return [node for node in project_map.values() if node["children"]]

    @classmethod
    def module_options(cls, request, project_product_id: int | str | None) -> list[dict]:
        if not project_product_id:
            return []
        try:
            project_product_id = int(project_product_id)
        except (TypeError, ValueError):
            return []
        queryset = ProductModule.objects.filter(project_product_id=project_product_id)
        queryset = cls._filter_module_by_user_scope(request, queryset)
        module_ids = Page.objects.filter(
            project_product_id=project_product_id,
            module_id__in=queryset.values("id"),
        ).values_list("module_id", flat=True).distinct()
        modules = queryset.select_related("parent", "parent__parent").filter(id__in=module_ids).order_by("sort", "id")
        return [
            {
                "key": item.id,
                "value": item.id,
                "title": cls._module_path(item),
                "label": cls._module_path(item),
                "name": item.name,
                "level": item.level,
                "parent_id": item.parent_id,
                "project_product_id": item.project_product_id,
            }
            for item in modules
        ]

    @classmethod
    def step_options(
            cls,
            request,
            project_product_id: int | str | None,
            module_id: int | str | None,
    ) -> list[dict]:
        try:
            project_product_id = int(project_product_id)
            module_id = int(module_id)
        except (TypeError, ValueError):
            return []
        allowed_module = cls._filter_module_by_user_scope(
            request,
            ProductModule.objects.filter(
                id=module_id,
                project_product_id=project_product_id,
            ),
        ).exists()
        if not allowed_module:
            return []
        steps = PageSteps.objects.select_related(
            "page",
            "module",
            "project_product",
            "project_product__project",
        ).filter(
            project_product_id=project_product_id,
            module_id=module_id,
        ).order_by("page__name", "name", "id")
        return [cls._step_option(step) for step in steps]

    @classmethod
    def _step_option(cls, step: PageSteps) -> dict:
        project_product = step.project_product
        project = project_product.project
        return {
            "key": step.id,
            "value": step.id,
            "title": step.name,
            "label": step.name,
            "step_id": step.id,
            "step_name": step.name,
            "page_id": step.page_id,
            "page_name": step.page.name,
            "page_url": step.page.url,
            "module_id": step.module_id,
            "module_name": step.module.name,
            "module_path": cls._module_path(step.module),
            "project_product_id": project_product.id,
            "project_product_name": project_product.name,
            "project_id": project.id,
            "project_name": project.name,
            "product_path": f"{project.name} / {project_product.name}",
        }

    @staticmethod
    def _module_path(module) -> str:
        names = []
        current = module
        while current:
            names.append(current.name)
            current = current.parent
        return " / ".join(reversed(names))

    @staticmethod
    def _filter_product_by_user_scope(request, queryset):
        user = getattr(getattr(request, "user", None), "user_obj", None)
        if (
                user is None or
                PermissionMenuService.is_effective_super_admin(user) or
                ProjectProductScopeService.can_view_all_project_data(user)
        ):
            return queryset
        allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        return queryset.filter(id__in=allowed_ids) if allowed_ids else queryset.none()

    @classmethod
    def _filter_module_by_user_scope(cls, request, queryset):
        user = getattr(getattr(request, "user", None), "user_obj", None)
        if (
                user is None or
                PermissionMenuService.is_effective_super_admin(user) or
                ProjectProductScopeService.can_view_all_project_data(user)
        ):
            return queryset
        allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        return queryset.filter(project_product_id__in=allowed_ids) if allowed_ids else queryset.none()

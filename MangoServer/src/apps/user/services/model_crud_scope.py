"""通用 CRUD 的项目产品数据范围策略。"""

from django.db.models.query import QuerySet

from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


class ModelCrudDataScopePolicy:
    @staticmethod
    def _user(request):
        return getattr(getattr(request, "user", None), "user_obj", None)

    @classmethod
    def _unrestricted(cls, user) -> bool:
        return (
                user is None
                or PermissionMenuService.is_effective_super_admin(user)
                or ProjectProductScopeService.can_view_all_project_data(user)
        )

    @classmethod
    def filter_queryset(cls, model, request, queryset: QuerySet, pytest_models: set[str]) -> QuerySet:
        user = cls._user(request)
        if cls._unrestricted(user):
            return queryset
        allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        if model._meta.label_lower == "test_center.projectproduct":
            return queryset.filter(id__in=allowed_ids) if allowed_ids else queryset.none()
        if not hasattr(model, "project_product"):
            return queryset
        if not allowed_ids:
            return queryset.none()
        if model.__name__ in pytest_models:
            return queryset.filter(project_product__project_product_id__in=allowed_ids)
        return queryset.filter(project_product_id__in=allowed_ids)

    @classmethod
    def has_data_permission(cls, model, request, data: dict, pytest_models: set[str]) -> bool:
        user = cls._user(request)
        if cls._unrestricted(user):
            return True
        if model._meta.label_lower == "test_center.projectproduct":
            project_product_id = data.get("id")
            if not project_product_id:
                return True
            try:
                return ProjectProductScopeService.has_project_product(user, int(project_product_id))
            except (TypeError, ValueError):
                return False
        if not hasattr(model, "project_product"):
            return True
        project_product_id = data.get("project_product") or data.get("project_product_id")
        if not project_product_id:
            return True
        if model.__name__ in pytest_models:
            pytest_product = model.objects.filter(id=project_product_id).first()
            project_product_id = pytest_product.project_product_id if pytest_product else None
        try:
            project_product_id = int(project_product_id)
        except (TypeError, ValueError):
            return False
        return ProjectProductScopeService.has_project_product(user, project_product_id)

    @classmethod
    def has_instance_permission(cls, model, request, instance, pytest_models: set[str]) -> bool:
        if model._meta.label_lower == "test_center.projectproduct":
            return cls.has_data_permission(model, request, {"id": getattr(instance, "id", None)}, pytest_models)
        if not hasattr(instance, "project_product_id"):
            return True
        return cls.has_data_permission(
            model,
            request,
            {"project_product": getattr(instance, "project_product_id", None)},
            pytest_models,
        )

    @staticmethod
    def apply_project_context(model, query_dict: dict, project_id, project_product_id, pytest_models: set[str]) -> None:
        if query_dict.get("project_product") is not None or not hasattr(model, "project_product"):
            return
        if model.__name__ in pytest_models:
            if project_product_id:
                products = model.objects.filter(project_product_id=project_product_id)
            elif project_id:
                products = model.objects.filter(project_product__project_id=project_id)
            else:
                products = None
            if products is not None:
                query_dict["project_product_id__in"] = products.values_list("id", flat=True)
        elif project_product_id:
            query_dict["project_product_id"] = project_product_id
        elif project_id:
            query_dict["project_product__project_id"] = project_id

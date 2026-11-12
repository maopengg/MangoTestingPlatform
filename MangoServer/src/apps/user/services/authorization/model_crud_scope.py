"""通用 CRUD 的项目产品数据范围策略。"""

from django.db.models.query import QuerySet
from django.db.models import Q

from src.apps.user.constants import RELATED_PRODUCT_SCOPE_PATHS
from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


class ModelCrudDataScopePolicy:
    @staticmethod
    def _allowed_ids(request, user):
        if not hasattr(request, '_mango_scope_product_ids'):
            request._mango_scope_product_ids = ProjectProductScopeService.project_product_ids_for_user(user)
        return request._mango_scope_product_ids

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
        allowed_ids = cls._allowed_ids(request, user)
        if model._meta.label_lower == "test_center.projectproduct":
            return queryset.filter(id__in=allowed_ids) if allowed_ids else queryset.none()
        paths = RELATED_PRODUCT_SCOPE_PATHS.get(model._meta.label_lower)
        if paths:
            if not allowed_ids:
                return queryset.none()
            predicate = Q()
            for path in paths:
                predicate |= Q(**{f'{path}__in': allowed_ids})
            return queryset.filter(predicate)
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
                return int(project_product_id) in cls._allowed_ids(request, user)
            except (TypeError, ValueError):
                return False
        paths = RELATED_PRODUCT_SCOPE_PATHS.get(model._meta.label_lower)
        if paths:
            supplied = False
            for field_name in {path.split('__', 1)[0] for path in paths}:
                target_id = data.get(field_name) or data.get(f'{field_name}_id')
                if target_id in (None, ''):
                    continue
                supplied = True
                if isinstance(target_id, dict):
                    target_id = target_id.get('id')
                if isinstance(target_id, (list, tuple)):
                    target_id = target_id[-1] if target_id else None
                target_model = model._meta.get_field(field_name).related_model
                try:
                    target = target_model.objects.filter(pk=target_id)
                    if not cls.filter_queryset(target_model, request, target, pytest_models).exists():
                        return False
                except (TypeError, ValueError):
                    return False
            return supplied or request.method.lower() != 'post'
        if not hasattr(model, "project_product"):
            return True
        project_product_id = data.get("project_product") or data.get("project_product_id")
        if not project_product_id:
            return True
        if isinstance(project_product_id, dict):
            project_product_id = project_product_id.get('id') or project_product_id.get('value')
        if isinstance(project_product_id, (list, tuple)):
            project_product_id = project_product_id[-1] if project_product_id else None
        if model.__name__ in pytest_models:
            product_model = model._meta.get_field('project_product').related_model
            pytest_product = product_model.objects.filter(id=project_product_id).first()
            project_product_id = pytest_product.project_product_id if pytest_product else None
        try:
            project_product_id = int(project_product_id)
        except (TypeError, ValueError):
            return False
        return project_product_id in cls._allowed_ids(request, user)

    @classmethod
    def has_instance_permission(cls, model, request, instance, pytest_models: set[str]) -> bool:
        model = type(instance) if hasattr(type(instance), '_meta') else model
        if model._meta.label_lower in RELATED_PRODUCT_SCOPE_PATHS:
            return cls.filter_queryset(model, request, model.objects.filter(pk=instance.pk), pytest_models).exists()
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

    @classmethod
    def has_request_permission(cls, model, request, pytest_models: set[str]) -> bool:
        if not cls.has_data_permission(model, request, request.query_params if request.method.lower() == 'get' else request.data, pytest_models):
            return False
        if request.method.lower() not in {'get', 'put', 'patch', 'delete'}:
            return True
        ids = request.query_params.getlist('id[]') if hasattr(request.query_params, 'getlist') else request.query_params.get('id[]', [])
        item_id = request.query_params.get('id') or request.data.get('id')
        if item_id:
            ids = [*ids, item_id]
        if not ids:
            return True
        user = cls._user(request)
        if cls._unrestricted(user):
            return True
        if not hasattr(model, 'project_product') and model._meta.label_lower not in RELATED_PRODUCT_SCOPE_PATHS and model._meta.label_lower != 'test_center.projectproduct':
            return True
        try:
            requested = model.objects.filter(pk__in=ids)
            visible = cls.filter_queryset(model, request, requested, pytest_models)
            if request.method.lower() == 'get':
                # 列表筛选允许不存在的 ID；只拒绝实际存在但不在调用者范围内的记录。
                return not requested.exclude(pk__in=visible.values('pk')).exists()
            return visible.count() == len(set(ids))
        except (TypeError, ValueError):
            return False

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

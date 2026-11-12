"""功能测试数据范围查询。

REST、AI、MCP 和其他后端调用方都应复用这里的数据范围规则，避免通过 CRUD/View
间接取得权限过滤能力。
"""

from rest_framework.request import Request

from src.apps.user.services.authorization.permission import PermissionMenuService, ProjectProductScopeService


def _request_user(request: Request):
    return getattr(getattr(request, "user", None), "user_obj", None)


def filter_project_product_scope(request: Request, queryset, *, field_name: str = "project_product_id"):
    user = _request_user(request)
    if (
            user is None
            or PermissionMenuService.is_effective_super_admin(user)
            or ProjectProductScopeService.can_view_all_project_data(user)
    ):
        return queryset
    allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
    if not allowed_ids:
        return queryset.none()
    return queryset.filter(**{f"{field_name}__in": allowed_ids})


def filter_manual_case_by_data_scope(request: Request, queryset):
    return filter_project_product_scope(request, queryset)


def filter_manual_suite_by_data_scope(request: Request, queryset):
    return filter_project_product_scope(request, queryset)


def filter_plan_by_data_scope(request: Request, queryset):
    return filter_project_product_scope(request, queryset)


def has_manual_case_project_product_scope(request: Request, project_product_id) -> bool:
    user = _request_user(request)
    if (
            user is None
            or PermissionMenuService.is_effective_super_admin(user)
            or ProjectProductScopeService.can_view_all_project_data(user)
    ):
        return True
    try:
        project_product_id = int(project_product_id)
    except (TypeError, ValueError):
        return False
    return ProjectProductScopeService.has_project_product(user, project_product_id)

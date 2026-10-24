from src.apps.auto_api.exceptions import QUALITY_COVERAGE_PROJECT_PRODUCT_PERMISSION_INVALID
from src.apps.functional_test.exceptions import FunctionalTestError

from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


def request_user_id(request):
    if isinstance(request.user, dict):
        return request.user.get("id")
    return getattr(getattr(request.user, "user_obj", None), "id", None)


def require_project_scope(request, project_product_id: int):
    user = getattr(getattr(request, "user", None), "user_obj", None)
    if user is not None and not ProjectProductScopeService.has_project_product(user, int(project_product_id)):
        raise FunctionalTestError(QUALITY_COVERAGE_PROJECT_PRODUCT_PERMISSION_INVALID)


def scope_queryset(request, queryset, field="project_product_id"):
    user = getattr(getattr(request, "user", None), "user_obj", None)
    if user is None or PermissionMenuService.is_effective_super_admin(
            user) or ProjectProductScopeService.can_view_all_project_data(user):
        return queryset
    allowed_ids = ProjectProductScopeService.project_product_ids_for_user(user)
    return queryset.filter(**{f"{field}__in": allowed_ids}) if allowed_ids else queryset.none()


def filter_module_scope(request, queryset):
    raw_module_ids = request.query_params.get("module__in")
    if raw_module_ids not in (None, ""):
        module_ids = [int(value) for value in str(raw_module_ids).split(",") if value.strip()]
        return queryset.filter(module_id__in=module_ids) if module_ids else queryset.none()
    module_id = request.query_params.get("module")
    return queryset.filter(module_id=module_id) if module_id not in (None, "") else queryset


def page_response(queryset, request, serializer_class):
    try:
        page = max(1, int(request.query_params.get("page", 1)))
        page_size = min(100, max(1, int(request.query_params.get("pageSize", 20))))
    except (TypeError, ValueError):
        page, page_size = 1, 20
    count = queryset.count()
    rows = queryset[(page - 1) * page_size:page * page_size]
    return {
        "items": serializer_class(rows, many=True).data,
        "count": count,
        "page": page,
        "page_size": page_size,
    }

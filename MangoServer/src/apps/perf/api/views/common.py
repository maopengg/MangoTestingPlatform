from rest_framework.request import Request

from src.apps.perf.exceptions import (
    PERF_PROJECT_PRODUCT_PERF_ACCESS_DENIED,
    PerfError,
)
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService


def ensure_perf_data_scope(request: Request, project_product_id: int | None):
    user = getattr(getattr(request, "user", None), "user_obj", None)
    if user is None or PermissionMenuService.is_effective_super_admin(user):
        return
    if not ProjectProductScopeService.has_project_product(user, project_product_id):
        raise PerfError(PERF_PROJECT_PRODUCT_PERF_ACCESS_DENIED)

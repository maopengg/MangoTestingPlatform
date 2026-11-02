"""Published HTTP/SSE/MCP targets within the Case's product boundary."""

from django.db.models import F, OuterRef, Subquery
from src.apps.auto_api.enums.protocol import ApiProtocolTypeEnum
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.evaluation.exceptions import EVALUATION_TARGET_ACCESS_DENIED, EvaluationError
from src.apps.evaluation.selectors.case import get_case
from src.apps.user.services.permission import PermissionMenuService


def published_interfaces(product_id):
    release = ApiQuerySelector.current_published_info_releases().filter(
        api_info_id=OuterRef("pk"),
    ).order_by("-id")
    return ApiQuerySelector.api_info().filter(
        project_product_id=product_id,
        protocol_type__in=[ApiProtocolTypeEnum.HTTP.value, ApiProtocolTypeEnum.SSE.value, ApiProtocolTypeEnum.MCP.value],
    ).annotate(published_release_id=Subquery(release.values("id")[:1]))


def interface_choices(case_id, user, *, module_id=None, selected_id=None, search="", page=1, page_size=50):
    case = get_case(case_id, user)
    if not PermissionMenuService.is_effective_super_admin(user) and "api.info:read" not in PermissionMenuService.permission_keys_for_user(user):
        raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)
    queryset = published_interfaces(case.project_product_id)
    if selected_id:
        queryset = queryset.filter(pk=selected_id)
    elif module_id:
        queryset = queryset.filter(module_id=module_id)
    else:
        return {"items": [], "count": 0}
    if search:
        queryset = queryset.filter(name__icontains=search)
    count = queryset.count()
    queryset = queryset.order_by(F("published_release_id").desc(nulls_last=True), "name", "id")
    items = [{"id": row.id, "name": row.name, "module_id": row.module_id,
              "protocol_type": row.protocol_type, "published": bool(row.published_release_id)}
             for row in queryset[(page - 1) * page_size:page * page_size]]
    return {"items": items, "count": count}

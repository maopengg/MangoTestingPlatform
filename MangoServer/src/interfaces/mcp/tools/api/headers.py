from __future__ import annotations

from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_header import ApiHeaderMutationService
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    ok,
    paginate_queryset,
)
from .helper_parts.execution import _api_header_summary, _list_same_api_headers
from .helpers import (
    Any,
    validate_dangerous_action_confirmation,
)


def register_headers_tools(mcp):
    @mcp.tool()
    def list_api_headers(project_product_id: int, enabled_only: bool = False, page: int = 1,
                         page_size: int = 10) -> dict:
        """查询项目产品公共请求头。"""
        queryset = ApiQuerySelector.api_headers().filter(project_product_id=project_product_id)
        if enabled_only:
            queryset = queryset.filter(status=1)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("-id"), page, page_size)
        return ok(
            {
                "items": [
                    {
                        "id": item.id,
                        "key": item.key,
                        "value": item.value,
                        "status": item.status,
                    }
                    for item in queryset
                ],
                "count": count,
                "page": page,
                "page_size": page_size,
            }
        )

    @mcp.tool()
    def preview_create_api_header_impact(project_product_id: int, key: str, value: str, status: int = 0) -> dict:
        """预览创建项目产品公共请求头的影响。

        公共请求头会被 API case/front_headers 或场景 headers 复用。只有接口执行必需的认证、租户、
        CSRF、业务网关等请求头才允许创建；accept-language、user-agent、sec-*、traceparent 等
        非必须浏览器噪声请求头不要添加。预览后必须由用户手动确认，才能调用 create_api_header。
        同一项目产品允许创建多个相同 key 的公共请求头，用于不同场景绑定不同值；预览会提示已有同 key 记录，
        由用户确认是否继续新增。
        """
        same_headers = _list_same_api_headers(project_product_id, key)
        return ok(
            create_dangerous_action_preview(
                "create_api_header",
                f"{project_product_id}:{key}",
                f"CREATE_API_HEADER:{project_product_id}:{key}",
                {
                    "project_product_id": project_product_id,
                    "key": key,
                    "value_preview": value[:80],
                    "status": status,
                    "same_key_headers": [_api_header_summary(item) for item in same_headers],
                    "manual_check_required": [
                        "请确认该请求头是接口执行必需项。",
                        "同一项目产品允许多个相同 key 的公共请求头，请确认本次新增值确实需要作为独立 header_id 绑定。",
                        "非必须请求头不允许添加到 ApiHeaders 公共请求头池。",
                        "浏览器自动生成的 sec-*、priority、traceparent、user-agent 等通常不要添加。",
                    ],
                },
            ),
            "已生成公共请求头创建预览，请用户确认后再创建",
        )

    @mcp.tool()
    def create_api_header(
            project_product_id: int,
            key: str,
            value: str,
            status: int = 0,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """确认后创建项目产品公共请求头。

        必须先调用 preview_create_api_header_impact，并由用户确认该 header 是接口执行必需请求头。
        同一项目产品允许多个相同 key 的公共请求头；非必须请求头不允许创建，不要把浏览器噪声请求头写入公共请求头池。
        """
        error = validate_dangerous_action_confirmation(
            "create_api_header",
            f"{project_product_id}:{key}",
            preview_token,
            confirm_text,
        )
        if error:
            return error
        data = ApiHeaderMutationService.create(
            {
                "project_product": project_product_id,
                "key": key,
                "value": value,
                "status": status,
            },
            operator_id=mcp_current_user_id(),
        )
        return ok({"header_id": data["id"], **data}, "公共请求头创建成功")

    @mcp.tool()
    def update_api_header(
            header_id: int,
            key: str | None = None,
            value: str | None = None,
            status: int | None = None,
    ) -> dict:
        """更新项目产品公共请求头。"""
        payload: dict[str, Any] = {"id": header_id}
        if key is not None:
            payload["key"] = key
        if value is not None:
            payload["value"] = value
        if status is not None:
            payload["status"] = status
        data = ApiHeaderMutationService.update(
            header_id,
            payload,
            operator_id=mcp_current_user_id(),
        )
        return ok({"header_id": data["id"], **data}, "公共请求头更新成功")

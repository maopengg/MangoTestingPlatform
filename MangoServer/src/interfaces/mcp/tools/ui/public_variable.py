from __future__ import annotations

from django.db.models import Q
from mangotools.enums import StatusEnum

from src.apps.auto_ui.enums import UiPublicTypeEnum
from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.auto_ui.services.asset_mutation import UiAssetMutationService
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.common.utils.environment_scope import normalize_test_envs, test_envs_query, test_envs_titles
from src.interfaces.mcp.audit import mcp_with_update_user
from .helpers import (
    fail,
    ok,
)


def register_public_variable_tools(mcp):
    @mcp.tool()
    def list_ui_public_variables(
            project_product_id: int,
            enabled_only: bool = False,
            type: int | None = None,
            test_env_id: int | None = None,
            common_only: bool = False,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询 UI 公共变量。test_env_id 不为空时返回环境通用和包含该环境的变量；common_only=True 只查环境通用变量。"""
        queryset = UiQuerySelector.ui_public().select_related("project_product", "datasource_alias").filter(
            project_product_id=project_product_id)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        if type is not None:
            if type not in UiPublicTypeEnum.get_key_list():
                return fail("UI 公共变量类型只支持 0=自定义、1=SQL、2=代码变量。", "UI_PUBLIC_TYPE_INVALID")
            queryset = queryset.filter(type=type)
        if common_only:
            queryset = queryset.filter(Q(test_envs=[]) | Q(test_envs__isnull=True))
        elif test_env_id is not None:
            queryset = queryset.filter(test_envs_query(test_env_id))
        if keyword:
            queryset = (
                    queryset.filter(name__contains=keyword)
                    | queryset.filter(key__contains=keyword)
                    | queryset.filter(value__contains=keyword)
            )
        count = queryset.count()
        offset = max(page - 1, 0) * page_size
        items = [
            {
                "id": item.id,
                "project_product_id": item.project_product_id,
                "test_env": item.test_env,
                "test_envs": item.test_envs or [],
                "test_env_titles": test_envs_titles(item.test_envs or [], EnvironmentEnum),
                "type": item.type,
                "type_title": UiPublicTypeEnum.get_value(item.type),
                "name": item.name,
                "key": item.key,
                "value": item.value,
                "datasource_alias_id": item.datasource_alias_id,
                "datasource_alias_name": item.datasource_alias.name if item.datasource_alias_id else None,
                "status": item.status,
            }
            for item in queryset.order_by("type", "-id")[offset: offset + page_size]
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def create_ui_public_variable(
            project_product_id: int,
            type: int,
            name: str,
            key: str,
            value: str,
            test_env_id: int | None = None,
            test_env_ids: list[int] | None = None,
            datasource_alias_id: int | None = None,
            status: int = 0,
    ) -> dict:
        """创建 UI 公共变量。test_env_ids 为空表示环境通用；传 [0,3] 表示测试环境和开发环境可用。test_env_id 仅兼容旧单环境入参。"""
        if type not in UiPublicTypeEnum.get_key_list():
            return fail("UI 公共变量类型只支持 0=自定义、1=SQL、2=代码变量。", "UI_PUBLIC_TYPE_INVALID")
        if type == UiPublicTypeEnum.SQL.value and not datasource_alias_id:
            return fail("SQL UI 公共变量必须传逻辑数据库 datasource_alias_id。", "UI_PUBLIC_DATASOURCE_ALIAS_REQUIRED")
        data = UiAssetMutationService.create_public_variable(
            mcp_with_update_user({
                "project_product": project_product_id,
                "test_envs": normalize_test_envs(test_env_ids, test_env_id),
                "type": type,
                "name": name,
                "key": key,
                "value": value,
                "datasource_alias": datasource_alias_id,
                "status": status,
            })
        )
        return ok({"public_variable_id": data["id"], **data}, "UI 公共变量创建成功")

    @mcp.tool()
    def update_ui_public_variable(
            public_variable_id: int,
            type: int | None = None,
            test_env_id: int | None = None,
            test_env_ids: list[int] | None = None,
            test_env_is_common: bool = False,
            name: str | None = None,
            key: str | None = None,
            value: str | None = None,
            datasource_alias_id: int | None = None,
            status: int | None = None,
    ) -> dict:
        """更新 UI 公共变量。test_env_ids 为空或 test_env_is_common=True 表示环境通用；status: 1=默认开启，0=默认关闭。"""
        payload = {"id": public_variable_id}
        for field, field_value in {
            "type": type,
            "name": name,
            "key": key,
            "value": value,
            "datasource_alias": datasource_alias_id,
            "status": status,
        }.items():
            if field_value is not None:
                payload[field] = field_value
        if test_env_is_common:
            payload["test_envs"] = []
        elif test_env_ids is not None:
            payload["test_envs"] = normalize_test_envs(test_env_ids)
        elif test_env_id is not None:
            payload["test_envs"] = normalize_test_envs(test_env_id)
        data = UiAssetMutationService.update_public_variable(
            public_variable_id,
            mcp_with_update_user(payload),
        )
        return ok({"public_variable_id": data["id"], **data}, "UI 公共变量更新成功")

    @mcp.tool()
    def set_ui_public_variable_status(public_variable_id: int, status: int) -> dict:
        """设置 UI 公共变量默认加载状态。status: 1=默认开启，所有 case 自动加载；0=默认关闭，需要在 case 前置里显式选择 front_public 后使用。"""
        data = UiAssetMutationService.update_public_variable(
            public_variable_id,
            mcp_with_update_user({"id": public_variable_id, "status": status}),
        )
        return ok({"public_variable_id": data["id"], "status": data["status"]}, "UI 公共变量状态更新成功")

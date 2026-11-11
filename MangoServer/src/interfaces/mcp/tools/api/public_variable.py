from __future__ import annotations

from django.db.models import Q
from src.apps.auto_api.selectors.public_variable import ApiPublicTagSelector
from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import ApiPublicTypeEnum
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_public import ApiPublicMutationService
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.common.utils.environment_scope import normalize_test_envs, test_envs_query, test_envs_titles
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import create_dangerous_action_preview, ok
from .helpers import (
    fail,
    validate_dangerous_action_confirmation,
)


def register_public_variable_tools(mcp):
    @mcp.tool()
    def list_api_public_variables(
            project_product_id: int,
            enabled_only: bool = False,
            type: int | None = None,
            test_env_id: int | None = None,
            common_only: bool = False,
            keyword: str | None = None,
            page: int = 1,
            page_size: int = 10,
            tag: str | None = None,
            untagged: bool = False,
            include_tag_summary: bool = False,
    ) -> dict:
        """查询 API 全局变量。test_env_id 返回通用和适用该环境的变量；common_only 仅查通用变量。

        tag 精确筛选分类；untagged 仅查未分类。include_tag_summary 返回分页前、分类筛选前的分类数量，
        可分析当前产品的变量整理情况。分类仅用于管理，不改变变量执行和加载顺序。
        """
        queryset = ApiQuerySelector.api_public().select_related("project_product", "datasource_alias").filter(
            project_product_id=project_product_id)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        if type is not None:
            if type not in ApiPublicTypeEnum.get_key_list():
                return fail("API 全局变量类型只支持 0=自定义、1=SQL、2=代码变量。", "API_PUBLIC_TYPE_INVALID")
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
        tag_summary = ApiPublicTagSelector.summarize(queryset) if include_tag_summary else None
        queryset = ApiPublicTagSelector.filter(queryset, tag, untagged)
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
                "type_title": ApiPublicTypeEnum.get_value(item.type),
                "name": item.name,
                "tags": item.tags or [],
                "key": item.key,
                "value": item.value,
                "datasource_alias_id": item.datasource_alias_id,
                "datasource_alias_name": item.datasource_alias.name if item.datasource_alias_id else None,
                "status": item.status,
            }
            for item in queryset.order_by("type", "-id")[offset: offset + page_size]
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size,
                   **({"tag_summary": tag_summary} if include_tag_summary else {})})

    @mcp.tool()
    def create_api_public_variable(
            project_product_id: int,
            type: int,
            name: str,
            key: str,
            value: str,
            test_env_id: int | None = None,
            test_env_ids: list[int] | None = None,
            datasource_alias_id: int | None = None,
            status: int = 0,
            tags: list[str] | None = None,
    ) -> dict:
        """创建 API 全局变量。test_env_ids 为空表示环境通用；test_env_id 仅兼容旧单环境入参。

        tags 为可选分类标签列表，最多20个、每个32字，仅用于管理。
        项目产品、环境集合、类型、key、value 五项完全相同时不允许重复创建。
        """
        if type not in ApiPublicTypeEnum.get_key_list():
            return fail("API 全局变量类型只支持 0=自定义、1=SQL、2=代码变量。", "API_PUBLIC_TYPE_INVALID")
        if type == ApiPublicTypeEnum.SQL.value and not datasource_alias_id:
            return fail("SQL API 全局变量必须传 datasource_alias_id。", "API_PUBLIC_DATASOURCE_ALIAS_REQUIRED")
        data = ApiPublicMutationService.create(
            {
                "project_product": project_product_id,
                "test_envs": normalize_test_envs(test_env_ids, test_env_id),
                "type": type,
                "name": name,
                "tags": tags or [],
                "key": key,
                "value": value,
                "datasource_alias": datasource_alias_id,
                "status": status,
            },
            operator_id=mcp_current_user_id(),
        )
        return ok({"public_variable_id": data["id"], **data}, "API 全局变量创建成功")

    @mcp.tool()
    def update_api_public_variable(
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
            tags: list[str] | None = None,
    ) -> dict:
        """更新 API 全局变量。test_env_ids 为空或 test_env_is_common=True 表示环境通用；status: 1=默认开启，0=默认关闭。

        tags 是可选分类标签列表；不传保留原标签，传 [] 清空。仅整理变量，不改变加载和授权匹配。
        """
        payload: dict[str, Any] = {"id": public_variable_id}
        for field, field_value in {
            "type": type,
            "name": name,
            "tags": tags,
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
        data = ApiPublicMutationService.update(
            public_variable_id,
            payload,
            operator_id=mcp_current_user_id(),
        )
        return ok({"public_variable_id": data["id"], **data}, "API 全局变量更新成功")

    @mcp.tool()
    def set_api_public_variable_status(public_variable_id: int, status: int) -> dict:
        """设置 API 全局变量默认加载状态。status: 1=默认开启，所有 case 自动加载；0=默认关闭，需要在 case 前置里显式选择 front_public 后使用。"""
        data = ApiPublicMutationService.update(
            public_variable_id,
            {"id": public_variable_id, "status": status},
            operator_id=mcp_current_user_id(),
        )
        return ok({"public_variable_id": data["id"], "status": data["status"]}, "API 全局变量状态更新成功")

    @mcp.tool()
    def preview_delete_api_public_variable_impact(public_variable_id: int) -> dict:
        """预览删除 API 全局变量的影响，并生成二次确认 token。"""
        item = ApiQuerySelector.api_public().select_related("project_product", "datasource_alias").get(
            id=public_variable_id)
        from src.apps.auto_api.services.api_case.snapshot import ApiExecutableSnapshotService

        referenced_cases = []
        for case in ApiQuerySelector.api_case().only("id", "name", "project_product_id"):
            case_config = ApiExecutableSnapshotService.current_case_config(case.id, case.project_product_id)
            if public_variable_id in (case_config.get("front_public") or []):
                referenced_cases.append({"id": case.id, "name": case.name})
        impact = {
            "public_variable": {
                "id": item.id,
                "name": item.name,
                "key": item.key,
                "project_product_id": item.project_product_id,
                "project_product_name": item.project_product.name if item.project_product else None,
                "test_envs": item.test_envs or [],
                "type": item.type,
                "status": item.status,
            },
            "explicit_case_references": referenced_cases,
            "explicit_case_reference_count": len(referenced_cases),
            "risk": (
                "删除后变量不再参与 API 和 API Case 执行；已显式引用该变量的 Case 将保留失效 ID，"
                "依赖该变量 key 的请求可能执行失败。"
            ),
            "safer_alternative": "如需临时停用，请优先调用 set_api_public_variable_status(status=0)。",
        }
        confirm_text = f"DELETE_API_PUBLIC_VARIABLE:{item.id}:{item.name}"
        return ok(
            create_dangerous_action_preview(
                "delete_api_public_variable",
                item.id,
                confirm_text,
                impact,
            ),
            "已生成 API 全局变量删除影响预览",
        )

    @mcp.tool()
    def delete_api_public_variable(
            public_variable_id: int,
            preview_token: str | None = None,
            confirm_text: str | None = None,
    ) -> dict:
        """删除 API 全局变量。必须先调用 preview_delete_api_public_variable_impact。"""
        confirm_error = validate_dangerous_action_confirmation(
            "delete_api_public_variable",
            public_variable_id,
            preview_token,
            confirm_text,
        )
        if confirm_error:
            return confirm_error
        try:
            ApiPublicMutationService.delete(public_variable_id)
        except Exception as exc:
            return fail(str(exc), "API_PUBLIC_VARIABLE_DELETE_FAILED")
        return ok({"public_variable_id": public_variable_id}, "API 全局变量已删除")

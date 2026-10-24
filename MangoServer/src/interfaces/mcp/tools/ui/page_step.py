from __future__ import annotations

from mangotools.enums import TaskEnum

from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.auto_ui.services.asset_mutation import UiAssetMutationService
from src.apps.auto_ui.services.step_ordering import UiStepOrderingService
from src.apps.auto_ui.services.test_case.test_case import TestCase
from src.interfaces.mcp.audit import mcp_current_user_id, mcp_with_update_user
from .helpers import (
    PageStepDetailMutationService,
    current_user,
    model_to_dict,
    ok,
    paginate_queryset,
)
from .helpers import _paged, _selected_env, _validate_flow_data


def register_page_step_tools(mcp):
    @mcp.tool()
    def search_ui_page_steps(project_product_id: int | None = None, page_id: int | None = None,
                             module_id: int | None = None, keyword: str | None = None, page: int = 1,
                             page_size: int = 10) -> dict:
        """搜索 UI 页面步骤。"""
        qs = UiQuerySelector.page_steps().select_related("project_product", "module", "page").all()
        if project_product_id is not None:
            qs = qs.filter(project_product_id=project_product_id)
        if page_id is not None:
            qs = qs.filter(page_id=page_id)
        if module_id is not None:
            qs = qs.filter(module_id=module_id)
        if keyword:
            qs = qs.filter(name__contains=keyword)
        return ok(_paged(qs.order_by("-id"), page, page_size))

    @mcp.tool()
    def get_ui_page_step_detail_full(page_step_id: int) -> dict:
        """查询 UI 页面步骤及步骤详情。"""
        step = UiQuerySelector.page_steps().get(id=page_step_id)
        return ok({"page_step": model_to_dict(step), "details": [model_to_dict(item) for item in
                                                                 UiQuerySelector.page_steps_detailed().filter(
                                                                     page_step_id=page_step_id).order_by("step_sort",
                                                                                                         "id")]})

    @mcp.tool()
    def create_ui_page_step(
            project_product_id: int,
            module_id: int,
            page_id: int,
            name: str,
            flow_data: dict | None = None,
            goal: str | None = None,
            entry_criteria: dict | None = None,
            success_criteria: dict | None = None,
            healing_enabled: bool = False,
            healing_policy: dict | None = None,
    ) -> dict:
        """创建 UI 页面步骤。启用自愈时必须同时配置 goal 和 success_criteria。"""
        error = _validate_flow_data(flow_data)
        if error:
            return error
        data = UiAssetMutationService.create_page_step(mcp_with_update_user({
            "project_product": project_product_id,
            "module": module_id,
            "page": page_id,
            "name": name,
            "flow_data": flow_data or {},
            "goal": goal,
            "entry_criteria": entry_criteria or {},
            "success_criteria": success_criteria or {},
            "healing_enabled": healing_enabled,
            "healing_policy": healing_policy or {},
            "status": TaskEnum.STAY_BEGIN.value,
        }))
        return ok({"page_step_id": data["id"], **data}, "UI 页面步骤创建成功")

    @mcp.tool()
    def update_ui_page_step(page_step_id: int, fields: dict) -> dict:
        """更新 UI 页面步骤。支持 goal、entry_criteria、success_criteria、healing_enabled 和 healing_policy。"""
        if "flow_data" in fields:
            error = _validate_flow_data(fields.get("flow_data"),
                                        require_config_ids=bool(fields.get("flow_data", {}).get("nodes")))
            if error:
                return error
        data = UiAssetMutationService.update_page_step(
            page_step_id,
            mcp_with_update_user({"id": page_step_id, **fields}),
        )
        return ok({"page_step_id": data["id"], **data}, "UI 页面步骤更新成功")

    @mcp.tool()
    def run_ui_page_step(page_step_id: int, test_env_id: int | None = None, is_send: bool = True) -> dict:
        """执行 UI 页面步骤，依赖执行器在线。"""
        user = current_user()
        env_id = _selected_env(user.id, test_env_id)
        result = TestCase(user.id, user.username, env_id, is_send=is_send).test_steps(page_step_id)
        return ok(result.model_dump(), "UI 页面步骤执行完成")

    @mcp.tool()
    def list_ui_page_step_details(page_step_id: int, page: int = 1, page_size: int = 10) -> dict:
        """查询页面步骤详情。"""
        queryset = UiQuerySelector.page_steps_detailed().filter(page_step_id=page_step_id).order_by("step_sort", "id")
        queryset, count, page, page_size = paginate_queryset(queryset, page, page_size)
        return ok(
            {"items": [model_to_dict(item) for item in queryset], "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def create_ui_page_step_detail(page_step_id: int, node_id: str, type: int, flow_data: dict,
                                   ope_key: str | None = None, ope_value: list | None = None,
                                   ele_name_id: int | None = None, sql_execute: list | None = None,
                                   custom: list | None = None, condition_value: dict | None = None,
                                   func: str | None = None, precondition: dict | None = None,
                                   postcondition: dict | None = None, step_sort: int = 0,
                                   page_type: int | None = None) -> dict:
        """创建页面步骤详情，并把新 id 回写到 flow_data.nodes[].config.id。"""
        payload = {"page_step": page_step_id, "type": type, "ope_key": ope_key, "ope_value": ope_value or [],
                   "ele_name": ele_name_id, "sql_execute": sql_execute, "custom": custom,
                   "condition_value": condition_value, "func": func, "precondition": precondition or {},
                   "postcondition": postcondition or {}, "step_sort": step_sort}
        data = PageStepDetailMutationService.save(
            page_step_id=page_step_id,
            node_id=node_id,
            flow_data=flow_data,
            payload=payload,
            page_type=page_type,
            operator_id=mcp_current_user_id(),
        )
        return ok(data, "页面步骤详情创建成功")

    @mcp.tool()
    def update_ui_page_step_detail(detail_id: int, fields: dict, page_type: int | None = None) -> dict:
        """更新页面步骤详情。fields 使用 PageStepsDetailed 字段名；修改方法相关字段时会校验 type/ope_key/ope_value。"""
        current = UiQuerySelector.page_steps_detailed().get(id=detail_id)
        data = PageStepDetailMutationService.save(
            detail_id=detail_id,
            page_step_id=current.page_step_id,
            payload=fields,
            page_type=page_type,
            operator_id=mcp_current_user_id(),
        )
        return ok(data, "页面步骤详情更新成功")

    @mcp.tool()
    def sort_ui_page_step_details(page_step_id: int, details: list[dict]) -> dict:
        """排序页面步骤详情。details 格式为 [{id, step_sort}]。"""
        UiStepOrderingService.sort_page_step_details(
            page_step_id,
            details,
            mcp_current_user_id(),
        )
        return ok({"page_step_id": page_step_id, "details": details}, "页面步骤详情排序成功")

from __future__ import annotations

from django.db.models import Q

from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.auto_ui.selectors.case_publication import UiCasePublicationSelector
from src.apps.auto_ui.services.asset_mutation import UiAssetMutationService
from src.apps.auto_ui.services.case_publication import UiCasePublicationService
from src.apps.auto_ui.exceptions import AutoUiError
from src.apps.auto_ui.exceptions.definitions import UI_CASE_PUBLICATION_INVALID_TRANSITION
from src.apps.auto_ui.services.batch_execution import UiCaseBatchExecutionService
from src.apps.auto_ui.services.case_step_cache import UiCaseStepCacheService
from src.apps.auto_ui.services.step_ordering import UiStepOrderingService
from src.apps.auto_ui.services.test_case.test_case import TestCase
from src.apps.system.enums import ClientNameEnum
from src.interfaces.mcp.audit import mcp_current_user_id, mcp_with_update_user
from .helpers import _case_tree, _paged, _selected_env
from .helpers import (
    current_user,
    model_to_dict,
    ok,
    paginate_queryset,
)


def register_case_tools(mcp):
    @mcp.tool()
    def search_ui_cases(project_product_id: int | None = None, module_id: int | None = None, keyword: str | None = None,
                        case_people_id: int | None = None, level: int | None = None, scenario_layer: int | None = None,
                        scenario_type: int | None = None, scenario_tags: list[str] | None = None,
                        status: int | None = None, page: int = 1, page_size: int = 10,
                        publication_status: str | None = None) -> dict:
        """搜索 UI case。"""
        qs = UiQuerySelector.ui_case().select_related("project_product", "module", "case_people").all()
        qs = UiCasePublicationSelector.filter_status(qs, publication_status)
        for field, value in {"project_product_id": project_product_id, "module_id": module_id,
                             "case_people_id": case_people_id, "level": level, "scenario_layer": scenario_layer,
                             "scenario_type": scenario_type, "status": status}.items():
            if value is not None:
                qs = qs.filter(**{field: value})
        if scenario_tags:
            tag_query = Q()
            for tag in scenario_tags:
                tag_query |= Q(scenario_tags__contains=[tag])
            qs = qs.filter(tag_query)
        if keyword:
            qs = qs.filter(name__contains=keyword)
        return ok(_paged(qs.order_by("-id"), page, page_size))

    @mcp.tool()
    def get_ui_case_detail_full(case_id: int, include_result_data: bool = True) -> dict:
        """查询 UI case 完整详情树。"""
        return ok(_case_tree(case_id, include_result_data=include_result_data))

    @mcp.tool()
    def create_ui_case(project_product_id: int, module_id: int, name: str, case_people_id: int | None = None,
                       level: int = 1, scenario_layer: int = 0, scenario_type: int = 0,
                       scenario_tags: list[str] | None = None, scenario_description: str | None = None,
                       parametrize: list | None = None, front_custom: list | None = None, front_sql: list | None = None,
                       front_public: list[int] | None = None, front_auth_config: list[int] | None = None,
                       posterior_sql: list | None = None) -> dict:
        """创建 UI case 主体。负责人未传时使用当前 MCP 用户；生产巡检/生产回归标签不允许任何数据库操作。

        front_public/front_auth_config 只传 ID 数组，表示本 case 显式选择的 UiPublic/UiAuthConfig；执行时与默认开启项合并为加载范围。
        parametrize 内参数项和 front_custom 均可传 test_envs 环境 ID 数组；字段缺失、null 或 [] 表示环境通用。
        """
        if case_people_id is None:
            case_people_id = current_user().id
        data = UiAssetMutationService.create_case(mcp_with_update_user(
            {"project_product": project_product_id, "module": module_id, "name": name, "case_people": case_people_id,
             "level": level, "scenario_layer": scenario_layer, "scenario_type": scenario_type,
             "scenario_tags": scenario_tags or [], "scenario_description": scenario_description,
             "parametrize": parametrize or [], "front_custom": front_custom or [], "front_sql": front_sql or [],
             "front_public": front_public or [], "front_auth_config": front_auth_config or [],
             "posterior_sql": posterior_sql or []}))
        return ok({"case_id": data["id"], **data}, "UI case 创建成功")

    @mcp.tool()
    def update_ui_case(case_id: int, fields: dict) -> dict:
        """更新 UI case 主体。fields 使用 UiCase 字段名。

        发布流转时 fields 只能包含 publication_status：unpublished → prepublished → published。
        提交预发布和通过发布均要求用例执行通过；仅产品负责人可通过发布或退回 unpublished。
        发布状态以 publication_status 为唯一来源，不能在一次请求中同时编辑内容和流转发布状态。

        fields.front_public 保存 UiPublic.id 列表；fields.front_auth_config 保存 UiAuthConfig.id 列表。
        fields.parametrize 内参数项和 fields.front_custom 均支持 test_envs 多环境数组；字段缺失、null 或 [] 表示环境通用。
        它们只决定加载范围，不改变平台已有变量类型加载顺序。
        """
        if 'publication_status' in fields:
            if set(fields) != {'publication_status'}:
                raise AutoUiError(UI_CASE_PUBLICATION_INVALID_TRANSITION)
            case = UiCasePublicationService.transition(
                case_id, fields['publication_status'], operator_id=current_user().id,
            )
            return ok({'case_id': case.id, 'publication_status': case.publication_status}, 'UI Case 发布状态已更新')
        data = UiAssetMutationService.update_case(case_id, mcp_with_update_user({"id": case_id, **fields}))
        return ok({"case_id": data["id"], **data}, "UI case 更新成功")

    @mcp.tool()
    def add_ui_case_step(case_id: int, page_step_id: int, case_sort: int | None = None, switch_step_open_url: int = 0,
                         error_retry: int | None = None, retry_interval: int | None = None) -> dict:
        """给 UI case 添加页面步骤。添加后建议调用 refresh_ui_case_step_cache_data；当前模型未保存 retry_interval。"""
        if case_sort is None:
            case_sort = UiQuerySelector.ui_case_steps_detailed().filter(case_id=case_id).count()
        data = UiAssetMutationService.add_case_step(mcp_with_update_user(
            {"case": case_id, "page_step": page_step_id, "case_sort": case_sort,
             "switch_step_open_url": switch_step_open_url, "error_retry": error_retry}))
        warnings = [
            "当前 UiCaseStepsDetailed 模型没有 retry_interval 字段，已忽略该参数。"] if retry_interval is not None else []
        return ok({"case_step_id": data["id"], **data}, "UI case 步骤添加成功", warnings=warnings)

    @mcp.tool()
    def list_ui_case_steps(case_id: int, page: int = 1, page_size: int = 10) -> dict:
        """查询 UI case 步骤。"""
        queryset = UiQuerySelector.ui_case_steps_detailed().filter(case_id=case_id).order_by("case_sort")
        queryset, count, page, page_size = paginate_queryset(queryset, page, page_size)
        items = [model_to_dict(item) for item in queryset]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def sort_ui_case_steps(case_id: int, steps: list[dict]) -> dict:
        """排序 UI case 步骤。steps 格式为 [{id, case_sort}]。"""
        UiStepOrderingService.sort_case_steps(
            case_id,
            steps,
            mcp_current_user_id(),
        )
        return ok({"case_id": case_id, "steps": steps}, "UI case 步骤排序成功")

    @mcp.tool()
    def refresh_ui_case_step_cache_data(case_step_id: int | None = None, case_id: int | None = None) -> dict:
        """按节点增量同步页面步骤到 UI case step；未变化节点会保留 Case 入参。"""
        result = UiCaseStepCacheService.refresh(
            case_step_id=case_step_id,
            case_id=case_id,
            operator_id=mcp_current_user_id(),
        )
        return ok(result, "UI case step 缓存数据刷新成功")

    @mcp.tool()
    def run_ui_case(case_id: int, test_env_id: int | None = None, is_send: bool = True) -> dict:
        """执行 UI case，依赖执行器在线。"""
        user = current_user()
        env_id = _selected_env(user.id, test_env_id)
        result = TestCase(user.id, user.username, env_id, is_send=is_send).test_case(case_id)
        return ok(result.model_dump(), "UI case 执行完成")

    @mcp.tool()
    def run_ui_case_batch(case_ids: list[int], test_env_id: int | None = None) -> dict:
        """批量执行 UI case，复用任务队列创建逻辑。"""
        user = current_user()
        env_id = _selected_env(user.id, test_env_id)
        result = UiCaseBatchExecutionService.execute(
            case_ids=case_ids,
            test_env=env_id,
            user_id=user.id,
        )
        result["test_env_id"] = result["test_env"]
        result["client"] = ClientNameEnum.DRIVER.value
        return ok(result, "UI case 批量执行任务创建成功")

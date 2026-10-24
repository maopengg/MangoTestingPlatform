from __future__ import annotations

from django.db import transaction
from mangotools.enums import TaskEnum

from src.apps.auto_ui.models import PageStepsDetailed
from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.auto_ui.services.asset_mutation import UiAssetMutationService
from src.apps.auto_ui.services.element_service import PageElementService
from src.apps.auto_ui.services.page_service import PageService
from src.apps.auto_ui.services.persistence import UiPersistenceService
from src.interfaces.mcp.audit import mcp_current_user_id, mcp_with_update_user
from src.interfaces.mcp.exceptions import MCP_IMPORTED_STEP_INVALID, McpError
from .helpers import (
    ElementExpEnum,
    ElementOperationEnum,
    PageStepDetailMutationService,
    fail,
    ok,
)
from .helpers import (
    _create_import_flow_data,
    _find_pages_by_normalized_url,
    _method_value_from_tree,
    _normalize_ui_page_url,
    _page_name_from_url,
    _parse_playwright_import_code,
    _validate_element_category,
    _validate_import_detail_payload,
)


def _expected_event_preview_from_action(action: dict) -> dict:
    if action.get("step_type") != ElementOperationEnum.OPE.value:
        return {}
    return {
        "ope_key": action.get("ope_key"),
        "ope_value": _method_value_from_tree("operation", action.get("ope_key"), action.get("values") or {}),
    }


def register_playwright_import_tools(mcp):
    @mcp.tool()
    def import_ui_page_step_from_playwright_code(
            page_step_name: str,
            playwright_code: str,
            project_product_id: int | None = None,
            module_id: int | None = None,
            page_id: int | None = None,
            page_name: str | None = None,
            element_category: str | None = None,
            reuse_page_by_url: bool = True,
            dedupe_elements: bool = True,
            include_page_actions: bool = False,
            dry_run: bool = False,
    ) -> dict:
        """
        从 Playwright codegen 代码导入 UI 页面、页面元素和页面步骤。

        规则：
        - page_step_name 只能保存页面步骤本身的业务描述，例如“创建二级订单类型”；不允许包含“MCP导入”“测试”“来源”等与步骤描述无关的前后缀；如果无法确定，应先询问用户。
        - 自动识别 page/page1 等变量前缀，只保存 get_by_role()/locator() 等定位链。
        - 识别第一条非空 goto(url) 作为页面 URL；URL 唯一命中已有页面时直接复用。
        - 如果 URL 命中多个页面，必须传 page_id；如果需要新建页面，必须传 project_product_id/module_id/page_name。
        - 如果会创建新元素，element_category 必填；如果不知道分类，应先询问用户。
        - 按代码顺序创建页面步骤详情，并生成线性 flow_data。
        - 新建元素时会根据脚本动作自动写入 expected_event：
          例如 fill("账号") 会写入 {"ope_key":"w_input","ope_value":[{"f":"input_value",...,"v":"账号"}]}；
          后续在页面步骤工作台再次选择该元素时，会自动带入预期事件和预期输入。
        - 复用已有元素时不会覆盖已有 expected_event，避免覆盖人工维护的模板。
        - 默认不把 goto/wait_for_url 等页面级操作导入节点；include_page_actions=True 时导入页面级操作。
        - 支持常见元素操作：click/dblclick/hover/fill/clear/type/press/check/select/tap/upload/wait/highlight 等。
        - 如果识别到 click() 后紧跟 set_input_files()，会合并为平台统一的 w_upload_files；运行时会自动判断 input[type=file] 或文件选择器上传。
        - 支持部分 expect 断言：可见、不可见、启用、禁用、可编辑、选中、为空、数量、不包含文本等。
        """
        if not playwright_code or not playwright_code.strip():
            return fail("playwright_code 不能为空。", "PLAYWRIGHT_CODE_REQUIRED")
        if not page_step_name or not page_step_name.strip():
            return fail("page_step_name 不能为空，且只能填写页面步骤本身的业务描述；如果不知道，请先询问用户。",
                        "PAGE_STEP_NAME_REQUIRED")
        page_step_name = page_step_name.strip()
        try:
            goto_url, actions, warnings = _parse_playwright_import_code(playwright_code,
                                                                        include_page_actions=include_page_actions)
        except ValueError as exc:
            return fail(str(exc), "INVALID_PLAYWRIGHT_CODE")
        if not actions:
            return fail("未识别到可导入的 UI 步骤，请确认代码中包含 click/fill/check/expect 等操作。",
                        "NO_IMPORTABLE_UI_ACTION")

        found_page = None
        page_reused_by_url = False
        normalized_goto_url = _normalize_ui_page_url(goto_url)
        if page_id:
            found_page = PageService.get_instance(page_id)
            if project_product_id is not None and found_page.project_product_id != project_product_id:
                return fail(
                    f"page_id={page_id} 属于 project_product_id={found_page.project_product_id}，与传入 project_product_id={project_product_id} 不一致。",
                    "UI_PAGE_PROJECT_PRODUCT_MISMATCH",
                )
            if module_id is not None and found_page.module_id != module_id:
                return fail(
                    f"page_id={page_id} 属于 module_id={found_page.module_id}，与传入 module_id={module_id} 不一致。",
                    "UI_PAGE_MODULE_MISMATCH",
                )
        elif goto_url and reuse_page_by_url:
            matched_pages = _find_pages_by_normalized_url(goto_url, project_product_id, module_id)[:10]
            if len(matched_pages) == 1:
                found_page = matched_pages[0]
                page_reused_by_url = True
            elif len(matched_pages) > 1:
                return fail(
                    "当前 URL 命中多个 UI 页面，请明确传 page_id，或补充 project_product_id/module_id 缩小范围。",
                    "UI_PAGE_URL_AMBIGUOUS",
                    details={
                        "url": goto_url,
                        "normalized_url": normalized_goto_url,
                        "candidates": [
                            {
                                "id": item.id,
                                "name": item.name,
                                "url": item.url,
                                "project_product_id": item.project_product_id,
                                "module_id": item.module_id,
                            }
                            for item in matched_pages
                        ],
                    },
                )
        if not found_page and not goto_url:
            return fail(
                "代码中未找到非空 goto(url)，且未传 page_id，无法确定页面。请提供 page_id 或在代码中提供有效 goto(url)。",
                "UI_PAGE_REQUIRED")

        resolved_project_product_id = found_page.project_product_id if found_page else project_product_id
        resolved_module_id = found_page.module_id if found_page else module_id
        element_actions = [action for action in actions if action.get("locator")]
        will_create_elements = []
        if found_page and element_actions:
            for action in element_actions:
                exists = (
                        dedupe_elements
                        and UiQuerySelector.page_element().filter(
                    page_id=found_page.id,
                    exp=ElementExpEnum.LOCATOR.value,
                    loc=action["locator"],
                ).exists()
                )
                if not exists:
                    will_create_elements.append({
                        "element_name": action["element_name"],
                        "loc": action["locator"],
                        "expected_event": _expected_event_preview_from_action(action),
                    })
        elif element_actions:
            will_create_elements = [
                {
                    "element_name": action["element_name"],
                    "loc": action["locator"],
                    "expected_event": _expected_event_preview_from_action(action),
                }
                for action in element_actions
            ]
        if will_create_elements:
            error = _validate_element_category(element_category)
            if error:
                error["details"] = {
                    "missing_fields": ["element_category"],
                    "will_create_element_count": len(will_create_elements),
                    "will_create_elements": will_create_elements[:20],
                }
                return error
            element_category = element_category.strip()
        if not found_page:
            missing = []
            if resolved_project_product_id is None:
                missing.append("project_product_id")
            if resolved_module_id is None:
                missing.append("module_id")
            if not page_name:
                missing.append("page_name")
            if missing:
                return fail(
                    f"需要新建 UI 页面时必须提供：{', '.join(missing)}。",
                    "UI_PAGE_CREATE_FIELDS_REQUIRED",
                    details={"missing_fields": missing, "url": normalized_goto_url},
                )

        preview = {
            "page": {
                "id": found_page.id if found_page else None,
                "name": found_page.name if found_page else (page_name or _page_name_from_url(goto_url, page_step_name)),
                "url": found_page.url if found_page else normalized_goto_url,
                "source_url": goto_url,
                "reused_by_url": page_reused_by_url,
                "will_create": found_page is None,
            },
            "page_step": {"name": page_step_name, "will_create": True},
            "actions": actions,
            "element_category": element_category,
            "will_create_elements": will_create_elements,
        }
        if dry_run:
            return ok(preview, "Playwright 代码解析成功，dry_run 未落库。", warnings=warnings)

        try:
            with transaction.atomic():
                if found_page:
                    page_obj = found_page
                else:
                    page_data = PageService.create_page(
                        resolved_project_product_id,
                        resolved_module_id,
                        page_name,
                        normalized_goto_url,
                        mcp_current_user_id(),
                    )
                    page_obj = UiQuerySelector.page().get(id=page_data["page_id"])

                page_step_data = UiAssetMutationService.create_page_step(
                    mcp_with_update_user({
                        "project_product": resolved_project_product_id,
                        "module": resolved_module_id,
                        "page": page_obj.id,
                        "name": page_step_name[:64],
                        "flow_data": {"nodes": [], "edges": []},
                        "status": TaskEnum.STAY_BEGIN.value,
                    })
                )
                page_step_id = page_step_data["id"]

                created_elements = []
                reused_elements = []
                created_details = []
                for action in actions:
                    element = None
                    kind = "assertion" if action["step_type"] == ElementOperationEnum.ASS.value else "operation"
                    ope_value = _method_value_from_tree(kind, action["ope_key"], action["values"])
                    if action.get("locator") and dedupe_elements:
                        element = UiQuerySelector.page_element().filter(
                            page_id=page_obj.id,
                            exp=ElementExpEnum.LOCATOR.value,
                            loc=action["locator"],
                        ).order_by("id").first()
                    if element:
                        reused_elements.append({"id": element.id, "name": element.name, "loc": element.loc})
                    elif action.get("locator"):
                        element_data = PageElementService.create_element(
                            page_id=page_obj.id,
                            name=action["element_name"],
                            category=element_category,
                            exp=ElementExpEnum.LOCATOR.value,
                            loc=action["locator"],
                            is_iframe=0,
                            expected_event={
                                "ope_key": action["ope_key"],
                                "ope_value": ope_value,
                            } if action["step_type"] == ElementOperationEnum.OPE.value else {},
                            user_id=mcp_current_user_id(),
                        )
                        element = UiQuerySelector.page_element().get(id=element_data["element_id"])
                        created_elements.append({
                            "id": element.id,
                            "name": element.name,
                            "loc": element.loc,
                            "expected_event": element.expected_event or {},
                        })

                    detail_payload = {
                        "page_step": page_step_id,
                        "type": action["step_type"],
                        "ele_name": element.id if element else None,
                        "step_sort": action["index"],
                        "ope_key": action["ope_key"],
                        "ope_value": ope_value,
                    }
                    error = _validate_import_detail_payload(detail_payload)
                    if error:
                        raise McpError(MCP_IMPORTED_STEP_INVALID, value=(error["message"],))
                    detail_data = UiPersistenceService.create_model(
                        PageStepsDetailed,
                        mcp_with_update_user(detail_payload),
                    )
                    created_details.append(
                        {
                            "detail_id": detail_data["id"],
                            "element_id": element.id if element else None,
                            "element_name": element.name if element else action.get("element_name"),
                            "step_type": action["step_type"],
                            "ope_key": action["ope_key"],
                            "ope_value": ope_value,
                            "step_sort": action["index"],
                        }
                    )

                flow_data = _create_import_flow_data(created_details)
                UiAssetMutationService.update_page_step(
                    page_step_id,
                    mcp_with_update_user({"id": page_step_id, "flow_data": flow_data}),
                )
                PageStepDetailMutationService.refresh_run_flow(page_step_id)
        except ValueError as exc:
            return fail(str(exc), "IMPORT_UI_PAGE_STEP_FAILED")

        return ok(
            {
                "page": {
                    "id": page_obj.id,
                    "name": page_obj.name,
                    "url": page_obj.url,
                    "reused_by_url": page_reused_by_url,
                },
                "page_step": {"id": page_step_id, "name": page_step_name[:64]},
                "created_elements": created_elements,
                "reused_elements": reused_elements,
                "created_details": created_details,
                "flow_data": flow_data,
            },
            "Playwright 代码已导入为 UI 页面步骤。",
            warnings=warnings,
        )

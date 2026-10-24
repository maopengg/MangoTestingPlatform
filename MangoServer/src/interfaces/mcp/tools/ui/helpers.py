from __future__ import annotations

import ast
import re
from urllib.parse import urlsplit

from django.forms import model_to_dict

from src.apps.auto_ui.enums import DriveTypeEnum, ElementExpEnum, ElementOperationEnum
from src.apps.auto_ui.models import (
    Page,
)
from src.apps.auto_ui.selectors.page import normalize_page_url
from src.apps.auto_ui.selectors.querysets import UiQuerySelector
from src.apps.auto_ui.services.page_step_detail import PageStepDetailMutationService
from src.common.exceptions import MangoServerError
from src.interfaces.mcp.common import (
    create_dangerous_action_preview,
    current_user,
    fail,
    ok,
    paginate_queryset,
)
from src.interfaces.mcp.exceptions import (
    MCP_PLAYWRIGHT_CODE_INVALID,
    MCP_TEST_ENVIRONMENT_REQUIRED,
    McpError,
)


def _enum_options(enum_cls) -> list[dict]:
    return [{"value": key, "label": value} for key, value in enum_cls.obj().items()]


def _ui_service_call(func, *args, **kwargs) -> dict:
    try:
        return ok(func(*args, **kwargs))
    except MangoServerError as error:
        return fail(error.msg, f"UI_ERROR_{error.code}")


UI_METHOD_CACHE_KEYS = PageStepDetailMutationService.METHOD_CACHE_KEYS


def _cache_method_tree(key: str) -> list:
    return PageStepDetailMutationService.cache_method_tree(key)


def _selected_env(user_id: int, test_env_id: int | None) -> int:
    if test_env_id is not None:
        return test_env_id
    user = current_user(user_id)
    from src.apps.user.services.user_cache import UserCacheService

    selected_environment = UserCacheService.selected_environment(user)
    if selected_environment is None:
        raise McpError(MCP_TEST_ENVIRONMENT_REQUIRED)
    return selected_environment


def _paged(queryset, page: int, page_size: int, serializer=None) -> dict:
    if serializer is None:
        items, count, page, page_size = paginate_queryset(
            queryset,
            page,
            page_size,
            max_page_size=100,
        )
        return {
            "items": [model_to_dict(item) for item in items],
            "count": count,
            "page": page,
            "page_size": page_size,
        }
    try:
        queryset = serializer.setup_eager_loading(queryset)
    except (AttributeError, TypeError):
        pass
    items, count, page, page_size = paginate_queryset(
        queryset,
        page,
        page_size,
        max_page_size=100,
    )
    data = serializer(instance=items, many=True).data
    return {"items": [dict(item) for item in data], "count": count, "page": page, "page_size": page_size}


def _method_tree_for(kind: str, page_type: int | None = None) -> list:
    return PageStepDetailMutationService.method_tree(kind, page_type)


def _find_method(method_tree: list, method_value: str | None) -> dict | None:
    return PageStepDetailMutationService.find_method(method_tree, method_value)


def _validate_flow_data(flow_data: dict | None, require_config_ids: bool = False) -> dict | None:
    if flow_data is None:
        return None
    if not isinstance(flow_data, dict):
        return fail("flow_data 必须是对象。", "INVALID_FLOW_DATA")
    nodes = flow_data.get("nodes")
    edges = flow_data.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return fail("flow_data 必须包含 nodes 和 edges 数组。", "INVALID_FLOW_DATA")
    for node in nodes:
        if not isinstance(node, dict):
            return fail("flow_data.nodes 每一项必须是对象。", "INVALID_FLOW_DATA")
        if not isinstance(node.get("position"), dict):
            return fail("flow_data.nodes[].position 必须是 {x,y}。", "INVALID_FLOW_DATA")
        if node.get("type") not in ElementOperationEnum.get_key_list():
            return fail("flow_data.nodes[].type 必须属于 ElementOperationEnum。", "INVALID_FLOW_DATA")
        if require_config_ids and not (isinstance(node.get("config"), dict) and node["config"].get("id")):
            return fail("flow_data.nodes[].config.id 必须指向已保存的 PageStepsDetailed.id。", "INVALID_FLOW_DATA")
    return None


def _validate_element_exp(value: int | None, name: str) -> dict | None:
    if value is not None and value not in ElementExpEnum.get_key_list():
        return fail(f"{name} 必须属于 ElementExpEnum。", "INVALID_ELEMENT_EXP")
    return None


def _validate_element_category(category: str | None) -> dict | None:
    if not str(category or "").strip():
        return fail("元素分类不能为空。请提供 category，例如：搜索区域、表格、弹窗、表单区域。",
                    "UI_ELEMENT_CATEGORY_REQUIRED")
    return None


def _case_tree(case_id: int, include_result_data: bool = True) -> dict:
    case = UiQuerySelector.ui_case().select_related("project_product", "module", "case_people").get(id=case_id)
    data = model_to_dict(case)
    if include_result_data:
        data["result_data"] = case.result_data if hasattr(case, "result_data") else None
    steps = []
    for step in UiQuerySelector.ui_case_steps_detailed().select_related("page_step").filter(case_id=case_id).order_by(
            "case_sort"):
        step_data = model_to_dict(step)
        if step.page_step:
            step_data["page_step_detail"] = model_to_dict(step.page_step)
            step_data["page_step_details"] = [
                model_to_dict(item)
                for item in
                UiQuerySelector.page_steps_detailed().filter(page_step_id=step.page_step_id).order_by("step_sort", "id")
            ]
        steps.append(step_data)
    data["steps"] = steps
    return data


def _delete_preview(action: str, target_id: int, confirm_text: str, impact: dict) -> dict:
    return ok(create_dangerous_action_preview(action, target_id, confirm_text, impact), "已生成危险操作影响预览")


PLAYWRIGHT_IMPORT_ACTIONS = {
    "click": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_click", "values": {}},
    "dblclick": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_dblclick", "values": {}},
    "hover": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_hover", "values": {}},
    "fill": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_input", "values": {"input_value": 0}},
    "clear": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_clear", "values": {}},
    "type": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_type", "values": {"text": 0}},
    "press_sequentially": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_press_sequentially",
                           "values": {"text": 0}},
    "press": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_press", "values": {"key": 0}},
    "focus": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_focus", "values": {}},
    "blur": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_blur", "values": {}},
    "check": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_check", "values": {}},
    "uncheck": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_uncheck", "values": {}},
    "set_checked": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_set_checked", "values": {"checked": 0}},
    "select_option": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_select_option",
                      "values": {"values": 0}},
    "select_text": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_select_text", "values": {}},
    "tap": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_tap", "values": {}},
    "dispatch_event": {
        "step_type": ElementOperationEnum.OPE.value,
        "ope_key": "w_dispatch_event",
        "values": {"event_type": 0, "event_init": 1},
    },
    "get_attribute": {
        "step_type": ElementOperationEnum.OPE.value,
        "ope_key": "w_get_attribute",
        "values": {"name": 0, "set_cache_key": None},
        "cache_required": True,
    },
    "input_value": {
        "step_type": ElementOperationEnum.OPE.value,
        "ope_key": "w_get_input_value",
        "values": {"set_cache_key": None},
        "cache_required": True,
    },
    "inner_html": {
        "step_type": ElementOperationEnum.OPE.value,
        "ope_key": "w_get_inner_html",
        "values": {"set_cache_key": None},
        "cache_required": True,
    },
    "all_text_contents": {
        "step_type": ElementOperationEnum.OPE.value,
        "ope_key": "w_get_texts",
        "values": {"set_cache_key": None},
        "cache_required": True,
    },
    "wait_for": {
        "step_type": ElementOperationEnum.OPE.value,
        "ope_key": "w_wait_for_element_state",
        "values": {"state": "visible", "timeout": None},
        "keyword_values": {"state": "state", "timeout": "timeout"},
    },
    "highlight": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_highlight", "values": {}},
    "scroll_into_view_if_needed": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_scroll_to_element",
                                   "values": {}},
    "set_input_files": {"step_type": ElementOperationEnum.OPE.value, "ope_key": "w_upload_files",
                        "values": {"file_path": 0}},
}

PLAYWRIGHT_PAGE_ACTIONS = {
    "goto": {"ope_key": "w_goto", "values": {"url": 0}},
    "wait_for_load_state": {"ope_key": "w_wait_for_load_state", "values": {"state": 0, "timeout": None},
                            "keyword_values": {"timeout": "timeout"}},
    "wait_for_url": {"ope_key": "w_wait_for_url", "values": {"url": 0, "timeout": None},
                     "keyword_values": {"timeout": "timeout"}},
    "wait_for_selector": {
        "ope_key": "w_wait_for_selector",
        "values": {"selector": 0, "state": "visible", "timeout": None},
        "keyword_values": {"state": "state", "timeout": "timeout"},
    },
    "wait_for_function": {"ope_key": "w_wait_for_function", "values": {"expression": 0, "timeout": None},
                          "keyword_values": {"timeout": "timeout"}},
    "set_viewport_size": {"ope_key": "w_set_viewport_size", "values": {"width": None, "height": None}},
    "set_extra_http_headers": {"ope_key": "w_set_extra_http_headers", "values": {"headers": 0}},
    "add_init_script": {"ope_key": "w_add_init_script", "values": {"script": 0}},
    "evaluate": {"ope_key": "w_evaluate", "values": {"script": 0, "set_cache_key": None}, "cache_required": True},
    "title": {"ope_key": "w_get_title", "values": {"set_cache_key": None}, "cache_required": True},
    "url": {"ope_key": "w_get_url", "values": {"set_cache_key": None}, "cache_required": True},
    "content": {"ope_key": "w_content", "values": {"set_cache_key": None}, "cache_required": True},
    "reload": {"ope_key": "w_refresh", "values": {}},
    "go_back": {"ope_key": "w_go_back", "values": {}},
    "go_forward": {"ope_key": "w_go_forward", "values": {}},
    "close": {"ope_key": "w_close_current_tab", "values": {}},
}

PLAYWRIGHT_EXPECT_ACTIONS = {
    "to_be_visible": {"ope_key": "w_to_be_visible", "values": {}},
    "not_to_be_visible": {"ope_key": "w_not_to_be_visible", "values": {}},
    "to_be_hidden": {"ope_key": "w_not_to_be_visible", "values": {}},
    "to_be_enabled": {"ope_key": "w_to_be_enabled", "values": {}},
    "not_to_be_enabled": {"ope_key": "w_not_to_be_enabled", "values": {}},
    "to_be_disabled": {"ope_key": "w_to_be_disabled", "values": {}},
    "to_be_editable": {"ope_key": "w_to_be_editable", "values": {}},
    "to_be_checked": {"ope_key": "w_to_be_checked", "values": {}},
    "to_be_empty": {"ope_key": "w_to_be_empty", "values": {}},
    "not_to_be_empty": {"ope_key": "w_not_to_be_empty", "values": {}},
    "to_have_count": {"ope_key": "w_to_have_count", "values": {"expect": 0}},
    "not_to_contain_text": {"ope_key": "w_not_to_contain_text", "values": {"expect": 0}},
}

PLAYWRIGHT_UNSUPPORTED_WITH_WARNING = {
    "drag_to": "drag_to 需要两个独立定位器，当前页面步骤详情只绑定一个主元素，已跳过。",
    "to_have_text": "当前 Web 断言方法树没有直接对应的 to_have_text，已跳过。",
    "to_contain_text": "当前 Web 断言方法树没有直接对应的 to_contain_text，已跳过。",
    "to_have_value": "当前 Web 断言方法树没有直接对应的 to_have_value，已跳过。",
}


def _safe_literal(node: ast.AST | None):
    if node is None:
        return None
    try:
        return ast.literal_eval(node)
    except Exception:
        try:
            return ast.unparse(node)
        except Exception:
            return None


def _source_segment(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""
    segment = ast.get_source_segment(source, node)
    if segment:
        return segment.strip()
    try:
        return ast.unparse(node).strip()
    except Exception:
        return ""


def _strip_page_variable(expr: str) -> str:
    return re.sub(r"^[A-Za-z_]\w*\.", "", expr.strip(), count=1)


def _first_text_match(expr: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, expr)
        if match:
            return match.group(match.lastindex or 1)
    return None


def _locator_name(locator_expr: str) -> str:
    name = _first_text_match(
        locator_expr,
        [
            r"has_text\s*=\s*['\"]([^'\"]+)['\"]",
            r"name\s*=\s*['\"]([^'\"]+)['\"]",
            r"get_by_placeholder\(\s*['\"]([^'\"]+)['\"]",
            r"get_by_text\(\s*['\"]([^'\"]+)['\"]",
            r"get_by_label\(\s*['\"]([^'\"]+)['\"]",
            r"get_by_title\(\s*['\"]([^'\"]+)['\"]",
            r"get_by_test_id\(\s*['\"]([^'\"]+)['\"]",
            r"get_by_role\(\s*['\"]([^'\"]+)['\"]",
            r"locator\(\s*['\"]([^'\"]+)['\"]",
        ],
    )
    if not name:
        name = locator_expr
    name = re.sub(r"\s+", " ", str(name)).strip()
    return name[:64] or "未命名元素"


def _page_name_from_url(url: str | None, fallback: str) -> str:
    if not url:
        return fallback[:64]
    name = url.rstrip("/").split("/")[-1] or fallback
    return name[:64]


def _normalize_ui_page_url(url: str | None) -> str | None:
    if not url:
        return None
    url = str(url).strip()
    if not url:
        return None
    parsed = urlsplit(url)
    if parsed.scheme and parsed.netloc:
        normalized = parsed.path or "/"
        if parsed.query:
            normalized = f"{normalized}?{parsed.query}"
        return normalized
    return url


def _find_pages_by_normalized_url(url: str | None, project_product_id: int | None = None,
                                  module_id: int | None = None) -> list[Page]:
    normalized = normalize_page_url(_normalize_ui_page_url(url) or url)
    if not normalized:
        return []
    queryset = UiQuerySelector.page().all()
    if project_product_id is not None:
        queryset = queryset.filter(project_product_id=project_product_id)
    if module_id is not None:
        queryset = queryset.filter(module_id=module_id)
    return [
        item
        for item in queryset.order_by("id").only("id", "name", "url", "project_product_id", "module_id")
        if normalize_page_url(item.url) == normalized
    ]


def _method_value_from_tree(kind: str, ope_key: str, values: dict) -> list[dict]:
    try:
        method = _find_method(_method_tree_for(kind, DriveTypeEnum.WEB.value), ope_key)
    except Exception:
        method = None
    parameters = method.get("parameter") if method else None
    if not parameters:
        locating_field = "actual" if kind == "assertion" else "locating"
        parameters = [{"f": locating_field, "d": False}]
        for field, value in values.items():
            parameters.append({"f": field, "d": True, "v": value})
    result = []
    for item in parameters:
        if not isinstance(item, dict):
            continue
        parameter = dict(item)
        field = parameter.get("f")
        if field in values:
            parameter["v"] = values[field]
        result.append(parameter)
    return result


def _validate_import_detail_payload(payload: dict) -> dict | None:
    if payload.get("type") not in [ElementOperationEnum.OPE.value, ElementOperationEnum.ASS.value]:
        return fail("导入 Playwright 代码只支持元素操作和断言操作。", "INVALID_IMPORT_UI_STEP_TYPE")
    if not payload.get("ope_key"):
        return fail("导入步骤缺少 ope_key。", "INVALID_IMPORT_UI_METHOD")
    for item in payload.get("ope_value") or []:
        if not isinstance(item, dict):
            return fail("导入步骤 ope_value 每一项必须是对象。", "INVALID_IMPORT_OPE_VALUE")
        if item.get("d") is True and item.get("v") in [None, ""]:
            return fail(f"导入步骤参数 {item.get('f')} 不能为空。", "IMPORT_OPE_VALUE_REQUIRED")
    return None


def _extract_action_values(call: ast.Call, action_config: dict) -> dict:
    values = {}
    for field, arg_index in action_config.get("values", {}).items():
        if isinstance(arg_index, int):
            if arg_index < len(call.args):
                values[field] = _safe_literal(call.args[arg_index])
        else:
            values[field] = arg_index
    for keyword in call.keywords or []:
        field = (action_config.get("keyword_values") or {}).get(keyword.arg)
        if field:
            values[field] = _safe_literal(keyword.value)
    if action_config.get("cache_required"):
        values["set_cache_key"] = values.get("set_cache_key") or "playwright_import_value"
    if action_config.get("ope_key") == "w_set_viewport_size" and call.args:
        first_arg = _safe_literal(call.args[0])
        if isinstance(first_arg, dict):
            values["width"] = first_arg.get("width")
            values["height"] = first_arg.get("height")
    return {key: value for key, value in values.items() if value is not None}


def _is_expect_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Name) and node.func.id == "expect")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "expect")
    )


def _parse_expect_target(source: str, node: ast.AST) -> str:
    if not _is_expect_call(node) or not node.args:
        return ""
    return _strip_page_variable(_source_segment(source, node.args[0]))


def _parse_playwright_import_code(playwright_code: str, include_page_actions: bool = False) -> tuple[
    str | None, list[dict], list[str]]:
    warnings = []
    actions = []
    goto_url = None
    try:
        tree = ast.parse(playwright_code)
    except SyntaxError as exc:
        raise McpError(MCP_PLAYWRIGHT_CODE_INVALID, value=(str(exc),)) from exc

    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not isinstance(call.func, ast.Attribute):
            continue
        action = call.func.attr
        target = call.func.value
        if action == "goto":
            current_goto_url = _safe_literal(call.args[0]) if call.args else None
            if current_goto_url and goto_url is None:
                goto_url = current_goto_url
            elif current_goto_url and current_goto_url != goto_url:
                warnings.append(f"检测到后续 goto({current_goto_url})，页面归属仍使用首个 goto({goto_url})。")
            if include_page_actions:
                if not current_goto_url:
                    warnings.append("已跳过空 URL 的 goto 操作。")
                    continue
                action_config = PLAYWRIGHT_PAGE_ACTIONS[action]
                actions.append(
                    {
                        "index": len(actions),
                        "action": action,
                        "step_type": ElementOperationEnum.OPE.value,
                        "ope_key": action_config["ope_key"],
                        "locator": None,
                        "element_name": None,
                        "values": _extract_action_values(call, action_config),
                    }
                )
            continue
        if action in PLAYWRIGHT_EXPECT_ACTIONS:
            locator_expr = _parse_expect_target(playwright_code, target)
            if not locator_expr:
                warnings.append(f"已跳过无法识别断言目标的 expect 操作：{action}")
                continue
            action_config = PLAYWRIGHT_EXPECT_ACTIONS[action]
            actions.append(
                {
                    "index": len(actions),
                    "action": action,
                    "step_type": ElementOperationEnum.ASS.value,
                    "ope_key": action_config["ope_key"],
                    "locator": locator_expr,
                    "element_name": _locator_name(locator_expr),
                    "values": _extract_action_values(call, action_config),
                }
            )
            continue
        if action in PLAYWRIGHT_UNSUPPORTED_WITH_WARNING:
            warnings.append(PLAYWRIGHT_UNSUPPORTED_WITH_WARNING[action])
            continue
        if _is_expect_call(target):
            warnings.append(f"已跳过暂未映射的 Playwright expect 操作：{action}")
            continue
        if action in PLAYWRIGHT_PAGE_ACTIONS and include_page_actions:
            action_config = PLAYWRIGHT_PAGE_ACTIONS[action]
            actions.append(
                {
                    "index": len(actions),
                    "action": action,
                    "step_type": ElementOperationEnum.OPE.value,
                    "ope_key": action_config["ope_key"],
                    "locator": None,
                    "element_name": action,
                    "values": _extract_action_values(call, action_config),
                }
            )
            continue
        if action not in PLAYWRIGHT_IMPORT_ACTIONS:
            continue
        locator_expr = _strip_page_variable(_source_segment(playwright_code, target))
        if not locator_expr:
            warnings.append(f"已跳过无法识别定位器的操作：{action}")
            continue
        action_config = dict(PLAYWRIGHT_IMPORT_ACTIONS[action])
        if action == "set_input_files" and actions:
            previous_action = actions[-1]
            if (
                    previous_action.get("step_type") == ElementOperationEnum.OPE.value
                    and previous_action.get("ope_key") in {"w_click", "w_force_click"}
                    and previous_action.get("locator")
            ):
                previous_action["action"] = "click_set_input_files"
                previous_action["ope_key"] = "w_upload_files"
                previous_action["values"] = _extract_action_values(call, action_config)
                warnings.append(
                    "检测到 click() 后紧跟 set_input_files()，已合并为“上传文件”，运行时会自动处理文件选择器。"
                )
                continue
        if action == "click":
            keyword_values = {keyword.arg: _safe_literal(keyword.value) for keyword in call.keywords or []}
            if keyword_values.get("button") == "right":
                action_config["ope_key"] = "w_right_click"
            elif keyword_values.get("force") is True:
                action_config["ope_key"] = "w_force_click"
        actions.append(
            {
                "index": len(actions),
                "action": action,
                "step_type": action_config["step_type"],
                "ope_key": action_config["ope_key"],
                "locator": locator_expr,
                "element_name": _locator_name(locator_expr),
                "values": _extract_action_values(call, action_config),
            }
        )
    return goto_url, actions, warnings


def _create_import_flow_data(details: list[dict]) -> dict:
    nodes = []
    edges = []
    previous_node_id = None
    for index, detail in enumerate(details):
        node_id = f"node-{index + 1}-{detail['detail_id']}"
        nodes.append(
            {
                "id": node_id,
                "position": {"x": 180, "y": index * 110 + 40},
                "type": detail.get("step_type", ElementOperationEnum.OPE.value),
                "label": detail.get("element_name") or detail.get("ope_key") or "元素操作",
                "config": {"id": detail["detail_id"]},
            }
        )
        if previous_node_id:
            edges.append(
                {
                    "id": f"edge-{previous_node_id}-{node_id}",
                    "source": {"node_id": previous_node_id, "position": "bottom"},
                    "target": {"node_id": node_id, "position": "top"},
                }
            )
        previous_node_id = node_id
    return {"nodes": nodes, "edges": edges}


__all__ = [name for name in globals() if not name.startswith("__")]

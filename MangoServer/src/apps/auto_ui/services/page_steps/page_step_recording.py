from copy import deepcopy

from django.db import transaction

from src.apps.auto_ui.enums import ElementOperationEnum
from src.apps.auto_ui.exceptions import (
    AutoUiError,
    UI_STEP_STEP_PAGE_INVALID,
    UI_STEP_STEP_PAGE_CONFIG_INVALID,
)
from src.apps.auto_ui.models import Page, PageElement, PageSteps, PageStepsDetailed
from src.apps.auto_ui.services.page_steps.page_step_detail import PageStepDetailMutationService


class PageStepRecordingService:
    """将浏览器录制草稿一次性转换为页面元素、步骤详情和线性画布。"""

    ACTION_METHODS = {
        "click": ("w_click", []),
        "double_click": ("w_dblclick", []),
        "right_click": ("w_right_click", []),
        "input": ("w_input", [{"f": "input_value", "v": ""}]),
        "key_press": ("w_press", [{"f": "key", "v": "Enter"}]),
        "scroll": (
            "w_mouse_wheel_xy",
            [{"f": "x", "v": 0}, {"f": "y", "v": 0}],
        ),
        "navigation": ("w_goto", [{"f": "url", "v": ""}]),
        "select": ("w_select_option", [{"f": "values", "v": ""}]),
        "check": ("w_check", []),
        "uncheck": ("w_uncheck", []),
        "wait": ("w_wait_for_timeout", [{"f": "_time", "v": 1}]),
        "assert_page_text": ("w_page_to_contain_text", [{"f": "expect", "v": ""}]),
        "custom_variable": (None, []),
    }
    ELEMENT_ACTIONS = {
        "click", "double_click", "right_click", "input", "key_press", "select", "check", "uncheck",
    }

    @classmethod
    @transaction.atomic
    def commit(
            cls,
            *,
            page_id: int,
            name: str,
            nodes: list[dict],
            operator_id: int | None,
    ) -> dict:
        page = Page.objects.select_related("project_product", "module").select_for_update().filter(
            id=page_id
        ).first()
        if page is None:
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("录制页面不存在",))
        step_name = str(name or "").strip()
        if not step_name:
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("页面步骤名称不能为空",))
        normalized_nodes = [item for item in (nodes or []) if isinstance(item, dict)]
        if not normalized_nodes:
            raise AutoUiError(UI_STEP_STEP_PAGE_INVALID, value=("录制节点不能为空",))

        page_step = PageSteps.objects.create(
            project_product_id=page.project_product_id,
            module_id=page.module_id,
            page_id=page.id,
            update_user_id=operator_id,
            name=step_name[:64],
            status=2,
            flow_data={"nodes": [], "edges": []},
        )
        details = []
        flow_nodes = []
        edges = []
        previous_node_id = None
        previous_position = None
        element_ids = set()
        for index, node in enumerate(normalized_nodes, start=1):
            detail_payload = cls._detail_payload(page, node, index, operator_id)
            detail = PageStepsDetailed.objects.create(page_step=page_step, **detail_payload)
            details.append(detail)
            if detail.ele_name_id:
                element_ids.add(detail.ele_name_id)
            node_id = f"recorded-{index}"
            row = (index - 1) // 4
            column_in_row = (index - 1) % 4
            column = column_in_row if row % 2 == 0 else 3 - column_in_row
            position = {"x": 120 + column * 260, "y": 100 + row * 150}
            flow_nodes.append({
                "id": node_id,
                "position": position,
                "type": int(detail.type),
                "label": cls._node_label(node, detail),
                "config": {"id": detail.id, "recorded": True},
            })
            if previous_node_id:
                if previous_position["y"] != position["y"]:
                    source_position, target_position = "bottom", "top"
                elif previous_position["x"] < position["x"]:
                    source_position, target_position = "right", "left"
                else:
                    source_position, target_position = "left", "right"
                edges.append({
                    "id": f"recorded-edge-{index - 1}-{index}",
                    "source": {"node_id": previous_node_id, "position": source_position},
                    "target": {"node_id": node_id, "position": target_position},
                })
            previous_node_id = node_id
            previous_position = position

        flow_data = PageStepDetailMutationService.normalize_flow_data(
            {"nodes": flow_nodes, "edges": edges}
        )
        PageStepDetailMutationService.validate_flow_detail_references(page_step.id, flow_data)
        page_step.flow_data = flow_data
        page_step.run_flow = PageStepDetailMutationService.build_run_flow(
            flow_data,
            page_step_id=page_step.id,
        )
        page_step.config_version += 1
        page_step.save(update_fields=["flow_data", "run_flow", "config_version", "update_time"])
        return {
            "page_step_id": page_step.id,
            "name": page_step.name,
            "detail_count": len(details),
            "detail_ids": [detail.id for detail in details],
            "element_ids": sorted(element_ids),
            "flow_data": page_step.flow_data,
            "run_flow": page_step.run_flow,
        }

    @classmethod
    def _detail_payload(cls, page: Page, node: dict, index: int, operator_id: int | None) -> dict:
        action_type = str(node.get("action") or "")
        detail = deepcopy(node.get("detail") or {})
        method = cls._resolve_method(node)
        if not detail and method is None:
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=(f"不支持的录制动作：{action_type or '-'}",))
        detail_type = int(detail.get("type", ElementOperationEnum.OPE.value))
        ope_key = detail.get("ope_key") or (method[0] if method else None)
        input_value = node.get("input_value")
        if node.get("sensitive") and not str(input_value or "").startswith("${{"):
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("敏感输入必须改成变量后保存",))
        if detail_type == ElementOperationEnum.CUSTOM.value:
            custom = detail.get("custom") or [{"key": node.get("key"), "value": node.get("value", "")}]
            key = str((custom[0] if custom else {}).get("key") or "").strip()
            if not key:
                raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("自定义变量名称不能为空",))
            payload = {
                "update_user_id": operator_id,
                "type": detail_type,
                "ele_name_id": None,
                "step_sort": index,
                "ope_key": None,
                "ope_value": None,
                "custom": custom,
                "key": key,
                "value": str(custom[0].get("value", "")),
            }
            cls._validate_page_step_detail(page, payload)
            return payload

        if detail_type == ElementOperationEnum.SQL.value:
            payload = {
                "update_user_id": operator_id,
                "type": detail_type,
                "ele_name_id": None,
                "step_sort": index,
                "ope_key": None,
                "ope_value": None,
                "sql_execute": deepcopy(detail.get("sql_execute") or []),
            }
            cls._validate_page_step_detail(page, payload)
            return payload

        if detail_type == ElementOperationEnum.PYTHON_CODE.value:
            payload = {
                "update_user_id": operator_id,
                "type": detail_type,
                "ele_name_id": None,
                "step_sort": index,
                "ope_key": None,
                "ope_value": None,
                "func": detail.get("func"),
            }
            cls._validate_page_step_detail(page, payload)
            return payload

        if detail_type == ElementOperationEnum.FORCE_WAIT.value:
            payload = {
                "update_user_id": operator_id,
                "type": detail_type,
                "ele_name_id": None,
                "step_sort": index,
                "ope_key": None,
                "ope_value": deepcopy(detail.get("ope_value") or [{"f": "seconds", "v": 1}]),
            }
            cls._validate_page_step_detail(page, payload)
            return payload

        if detail_type == ElementOperationEnum.CONDITION.value:
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID,
                              value=("录制区不支持插入条件判断，请保存后在页面步骤画布中配置",),
                              )

        if detail_type not in (ElementOperationEnum.OPE.value, ElementOperationEnum.ASS.value):
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=(f"不支持的录制节点类型：{detail_type}",))

        kind = "operation" if detail_type == ElementOperationEnum.OPE.value else "assertion"
        method_info = PageStepDetailMutationService.find_method(
            PageStepDetailMutationService.validation_method_tree(
                kind,
                getattr(page.project_product, "ui_client_type", None),
            ),
            ope_key,
        )
        if method_info is None:
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=(f"页面步骤方法不存在：{ope_key or '-'}",))
        values = deepcopy(method_info.get("parameter") or [])
        configured_values = {
            item.get("f"): item.get("v")
            for item in detail.get("ope_value") or []
            if isinstance(item, dict) and item.get("f")
        }
        value_map = {
            "input_value": input_value,
            "key": node.get("key"),
            "x": node.get("delta_x", 0),
            "y": node.get("delta_y", 0),
            "url": node.get("url") or (node.get("page") or {}).get("url"),
            "_time": node.get("seconds", 1),
            "expect": node.get("expect"),
            "values": input_value,
            "n": node.get("drag_distance"),
        }
        for item in values:
            field = item.get("f")
            if field in configured_values:
                item["v"] = configured_values[field]
            elif field in value_map and value_map[field] is not None:
                item["v"] = value_map[field]

        requires_element = any(
            item.get("f") in {"locating", "actual"}
            for item in values
            if isinstance(item, dict)
        )
        element_id = detail.get("ele_name") or node.get("element_id")
        if requires_element:
            if not str(node.get("name") or "").strip():
                raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("录制元素名称不能为空",))
            element_id = cls._resolve_element(
                page,
                {**node, "element_id": element_id},
                operator_id,
                ope_key,
                values,
            ).id
        else:
            element_id = None
        payload = {
            "update_user_id": operator_id,
            "type": detail_type,
            "ele_name_id": element_id,
            "step_sort": index,
            "ope_key": ope_key,
            "ope_value": values,
        }
        cls._validate_page_step_detail(page, payload)
        return payload

    @staticmethod
    def _validate_page_step_detail(page: Page, payload: dict):
        PageStepDetailMutationService.validate_detail_payload(
            {**payload, "ele_name": payload.get("ele_name_id")},
            page_type=getattr(page.project_product, "ui_client_type", None),
            project_product_id=page.project_product_id,
        )

    @classmethod
    def _resolve_method(cls, action: dict):
        action_type = str(action.get("action") or "")
        if action_type != "drag":
            return cls.ACTION_METHODS.get(action_type)
        delta_x = float(action.get("drag_delta_x") or 0)
        delta_y = float(action.get("drag_delta_y") or 0)
        if not delta_x and not delta_y:
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("拖拽步骤缺少有效位移",))
        if abs(delta_x) >= abs(delta_y):
            ope_key = "w_drag_right_pixel" if delta_x > 0 else "w_drag_left_pixel"
            distance = abs(delta_x)
        else:
            ope_key = "w_drag_down_pixel" if delta_y > 0 else "w_drag_up_pixel"
            distance = abs(delta_y)
        action["drag_distance"] = max(1, round(distance))
        return ope_key, [{"f": "n", "v": action["drag_distance"]}]

    @staticmethod
    def _resolve_element(
            page: Page,
            node: dict,
            operator_id: int | None,
            ope_key: str | None,
            ope_value: list,
    ) -> PageElement:
        existing_id = node.get("element_id")
        if existing_id:
            existing = PageElement.objects.filter(id=existing_id, page_id=page.id).first()
            if existing:
                return existing
        element = node.get("element") or {}
        locators = [item for item in (element.get("locators") or []) if item.get("loc")][:3]
        if not locators:
            raise AutoUiError(UI_STEP_STEP_PAGE_CONFIG_INVALID, value=("录制元素缺少有效定位器",))
        primary = locators[0]
        existing = PageElement.objects.filter(
            page_id=page.id,
            exp=primary.get("exp"),
            loc=primary.get("loc"),
        ).first()
        if existing:
            return existing
        name = (
                node.get("name")
                or element.get("accessible_name")
                or element.get("text")
                or element.get("label")
                or element.get("placeholder")
                or element.get("tag")
                or "录制元素"
        )
        create_data = {
            "page_id": page.id,
            "update_user_id": operator_id,
            "name": str(name).strip()[:64] or "录制元素",
            "category": str(node.get("category") or "未分类")[:64],
            "exp": primary.get("exp"),
            "loc": primary.get("loc"),
            "sub": primary.get("sub"),
            "prompt": str(name).strip()[:512],
            "expected_event": {
                "ope_key": ope_key,
                "ope_value": [item for item in ope_value if item.get("f") not in {"locating", "actual"}],
            },
        }
        for group, locator in enumerate(locators[1:], start=2):
            create_data[f"exp{group}"] = locator.get("exp")
            create_data[f"loc{group}"] = locator.get("loc")
            create_data[f"sub{group}"] = locator.get("sub")
        return PageElement.objects.create(**create_data)

    @staticmethod
    def _node_label(action: dict, detail: PageStepsDetailed) -> str:
        return str(
            action.get("name")
            or (action.get("element") or {}).get("accessible_name")
            or (action.get("element") or {}).get("text")
            or detail.ope_key
            or "录制步骤"
        )[:64]

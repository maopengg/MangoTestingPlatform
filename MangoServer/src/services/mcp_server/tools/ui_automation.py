from __future__ import annotations

from django.forms import model_to_dict
from django.db.models import Q

from src.apps.auto_system.service.tasks.add_tasks import AddTasks
from src.apps.auto_system.service.cache_data_value import CacheDataValue
from src.apps.auto_ui.models import Page, PageElement, PageSteps, PageStepsDetailed, UiCase, UiCaseStepsDetailed, UiPublic
from src.apps.auto_ui.service.test_case.test_case import TestCase
from src.apps.auto_ui.views.ui_case import UiCaseCRUD
from src.apps.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailedCRUD
from src.apps.auto_ui.views.ui_element import PageElementCRUD
from src.apps.auto_ui.views.ui_page import PageCRUD
from src.apps.auto_ui.views.ui_page_steps import PageStepsCRUD
from src.apps.auto_ui.views.ui_page_steps_detailed import PageStepsDetailedCRUD
from src.apps.auto_ui.views.ui_public import UiPublicCRUD
from src.common.enums.system_enum import ClientNameEnum
from src.common.enums.tools_enum import (
    ApiCaseScenarioLayerEnum,
    ApiCaseScenarioTagEnum,
    ApiCaseScenarioTypeEnum,
    CaseLevelEnum,
    EnvironmentEnum,
    StatusEnum,
    TaskEnum,
    TestCaseTypeEnum,
)
from src.common.enums.ui_enum import DriveTypeEnum, ElementExpEnum, ElementOperationEnum, UiPublicTypeEnum
from src.services.mcp_server.common import (
    create_dangerous_action_preview,
    current_user,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)


def _enum_options(enum_cls) -> list[dict]:
    return [{"value": key, "label": value} for key, value in enum_cls.obj().items()]


UI_METHOD_CACHE_KEYS = {
    "playwright_operation": "playwright_operation_method",
    "uiautomator_operation": "uiautomator_operation_method",
    "playwright_assertion": "playwright_assertion_method",
    "uiautomator_assertion": "uiautomator_assertion_method",
    "public_assertion": "public_assertion_method",
    "sql_assertion": "sql_assertion_method",
}


def _cache_method_tree(key: str) -> list:
    data = CacheDataValue.get_cache_value(key=key)
    return data if isinstance(data, list) else []


def _selected_env(user_id: int, test_env_id: int | None) -> int:
    if test_env_id is not None:
        return test_env_id
    user = current_user(user_id)
    if user.selected_environment is None:
        raise ValueError("当前用户未选择测试环境，请先调用 switch_user_test_environment。")
    return user.selected_environment


def _paged(queryset, page: int, page_size: int, serializer) -> dict:
    data, count = PageCRUD.paging_list(page_size, page, queryset, serializer)
    return {"items": [dict(item) for item in data], "count": count, "page": page, "page_size": page_size}


def _method_tree_for(kind: str, page_type: int | None = None) -> list:
    if kind == "operation":
        if page_type is None:
            data = []
            playwright = _cache_method_tree(UI_METHOD_CACHE_KEYS["playwright_operation"])
            if playwright:
                data.append({"value": "playwright", "label": "WEB", "children": playwright})
            uiautomator = _cache_method_tree(UI_METHOD_CACHE_KEYS["uiautomator_operation"])
            if uiautomator:
                data.append({"value": "uiautomator", "label": "安卓", "children": uiautomator})
            return data
        if int(page_type) == DriveTypeEnum.WEB.value:
            return _cache_method_tree(UI_METHOD_CACHE_KEYS["playwright_operation"])
        if int(page_type) == DriveTypeEnum.ANDROID.value:
            return _cache_method_tree(UI_METHOD_CACHE_KEYS["uiautomator_operation"])
        return []

    if kind == "assertion":
        if page_type is None:
            return _cache_method_tree(UI_METHOD_CACHE_KEYS["public_assertion"])
        if int(page_type) == DriveTypeEnum.WEB.value:
            data = _cache_method_tree(UI_METHOD_CACHE_KEYS["playwright_assertion"])
        elif int(page_type) == DriveTypeEnum.ANDROID.value:
            data = _cache_method_tree(UI_METHOD_CACHE_KEYS["uiautomator_assertion"])
        else:
            data = []
        public_assertion = _cache_method_tree(UI_METHOD_CACHE_KEYS["public_assertion"])
        sql_assertion = _cache_method_tree(UI_METHOD_CACHE_KEYS["sql_assertion"])
        if isinstance(data, list):
            data = list(data)
            data.append({"value": "PublicAssertion", "label": "元素文本", "children": public_assertion})
            if sql_assertion:
                data.append(sql_assertion[0])
        return data

    return []


def _find_method(method_tree: list, method_value: str | None) -> dict | None:
    if not method_value:
        return None
    for item in method_tree or []:
        if not isinstance(item, dict):
            continue
        if item.get("value") == method_value:
            return item
        found = _find_method(item.get("children") or [], method_value)
        if found:
            return found
    return None


def _validate_ope_value(method: dict, ope_value: list | None) -> dict | None:
    expected = method.get("parameter") or []
    actual = ope_value or []
    actual_by_f = {item.get("f"): item for item in actual if isinstance(item, dict)}
    expected_fields = {item.get("f") for item in expected if isinstance(item, dict)}
    for item in actual:
        if isinstance(item, dict) and item.get("f") not in expected_fields:
            return fail(f"ope_value 参数 {item.get('f')} 不属于方法 {method.get('value')}。", "INVALID_UI_METHOD_PARAMETER")
    for item in expected:
        if not isinstance(item, dict):
            continue
        field = item.get("f")
        if item.get("d") is True and field not in actual_by_f:
            return fail(f"ope_value 缺少必填参数 {field}。", "UI_METHOD_PARAMETER_REQUIRED")
        if item.get("d") is True and actual_by_f.get(field, {}).get("v") in [None, ""]:
            return fail(f"ope_value 参数 {field} 的 v 不能为空。", "UI_METHOD_PARAMETER_REQUIRED")
    return None


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


def _validate_page_step_detail_payload(payload: dict, page_type: int | None = None) -> dict | None:
    step_type = payload.get("type")
    if step_type not in ElementOperationEnum.get_key_list():
        return fail("type 必须属于 ElementOperationEnum。", "INVALID_UI_STEP_TYPE")
    if step_type in [ElementOperationEnum.OPE.value, ElementOperationEnum.ASS.value, ElementOperationEnum.CONDITION.value]:
        kind = "operation" if step_type == ElementOperationEnum.OPE.value else "assertion"
        method_tree = _method_tree_for(kind, page_type)
        method = _find_method(method_tree, payload.get("ope_key"))
        if not method:
            return fail("ope_key 必须来自 UI 方法树叶子 value，请先调用 get_ui_operation_methods 或 get_ui_assertion_methods。", "INVALID_UI_METHOD")
        error = _validate_ope_value(method, payload.get("ope_value"))
        if error:
            return error
    if step_type == ElementOperationEnum.SQL.value and not payload.get("sql_execute"):
        return fail("type=2 时 sql_execute 必填，格式为 [{sql,key_list}]。", "SQL_EXECUTE_REQUIRED")
    if step_type == ElementOperationEnum.CUSTOM.value and not payload.get("custom"):
        return fail("type=3 时 custom 必填，格式为 [{key,value}]。", "CUSTOM_REQUIRED")
    if step_type == ElementOperationEnum.CONDITION.value and payload.get("condition_value") is not None:
        if not isinstance(payload.get("condition_value"), dict) or "expect" not in payload["condition_value"]:
            return fail("condition_value 必须是 {expect}。", "INVALID_CONDITION_VALUE")
    if step_type == ElementOperationEnum.PYTHON_CODE.value and not payload.get("func"):
        return fail("type=5 时 func 必填。", "FUNC_REQUIRED")
    return None


def _case_tree(case_id: int, include_result_data: bool = True) -> dict:
    case = UiCase.objects.select_related("project_product", "module", "case_people").get(id=case_id)
    data = model_to_dict(case)
    if include_result_data:
        data["result_data"] = case.result_data if hasattr(case, "result_data") else None
    steps = []
    for step in UiCaseStepsDetailed.objects.select_related("page_step").filter(case_id=case_id).order_by("case_sort"):
        step_data = model_to_dict(step)
        if step.page_step:
            step_data["page_step_detail"] = model_to_dict(step.page_step)
            step_data["page_step_details"] = [
                model_to_dict(item)
                for item in PageStepsDetailed.objects.filter(page_step_id=step.page_step_id).order_by("step_sort", "id")
            ]
        steps.append(step_data)
    data["steps"] = steps
    return data


def _delete_preview(action: str, target_id: int, confirm_text: str, impact: dict) -> dict:
    return ok(create_dangerous_action_preview(action, target_id, confirm_text, impact), "已生成危险操作影响预览")


def register_ui_automation_tools(mcp):
    @mcp.tool()
    def get_ui_automation_schema() -> dict:
        """返回 UI 自动化 MCP 字段、枚举、方法来源和 JSON 格式说明。"""
        ui_public_sql_schema = {
            "type": "object",
            "fields": ["project_product_id", "test_env_id", "type", "name", "key", "value", "datasource_alias_id", "status"],
            "format": {
                "type": "0=自定义公共变量，1=SQL 公共变量。",
                "value": "SQL 类型时填写 SQL 语句，自定义类型时填写普通值。",
                "datasource_alias_id": "SQL 类型必填，传逻辑数据源 DataFactoryDatasourceAlias.id；自定义类型可不传。",
            },
            "lookup_rule": "创建或更新 SQL 公共变量前，先调用 list_data_factory_datasource_aliases(project_product_id=当前产品ID) 查询逻辑数据源 ID，然后把返回的 datasource_alias_id 传给本字段。",
            "query_rule": "已有 UI 公共变量可调用 list_ui_public_variables(project_product_id=当前产品ID, type=1) 查询，返回 datasource_alias_id 和 datasource_alias_name。",
            "example": {
                "project_product_id": 1,
                "test_env_id": 0,
                "type": 1,
                "name": "查询登录用户",
                "key": "login_user",
                "value": "SELECT id,name FROM user WHERE id=${{user_id}}",
                "datasource_alias_id": 2,
                "status": 1,
            },
        }
        ui_case_sql_schema = {
            "type": "list[object]",
            "format": [{"sql": "SQL语句", "key_list": "查询结果缓存key，可为空", "datasource_alias": "逻辑数据源ID，可为空"}],
            "datasource_alias": {
                "field": "datasource_alias",
                "type": "int | null",
                "source": "数据工厂逻辑数据源 DataFactoryDatasourceAlias.id",
                "lookup_tool": "list_data_factory_datasource_aliases(project_product_id=当前产品ID)",
                "rule": "多数据库测试环境下，UI case 的 SQL 前置或后置必须传 datasource_alias；单库老数据可为空并由后端/执行器兜底。",
            },
            "variable_support": "sql 支持 ${{变量}}、${{随机方法()}}、${{数据工厂.字段}} 等表达式，执行前由测试数据引擎替换。",
        }
        return ok(
            {
                "enums": {
                    "drive_type": _enum_options(DriveTypeEnum),
                    "element_exp": _enum_options(ElementExpEnum),
                    "element_operation": _enum_options(ElementOperationEnum),
                    "ui_public_type": _enum_options(UiPublicTypeEnum),
                    "case_level": _enum_options(CaseLevelEnum),
                    "task_status": _enum_options(TaskEnum),
                    "scenario_layer": _enum_options(ApiCaseScenarioLayerEnum),
                    "scenario_type": _enum_options(ApiCaseScenarioTypeEnum),
                    "scenario_tags": _enum_options(ApiCaseScenarioTagEnum),
                    "environment": _enum_options(EnvironmentEnum),
                },
                "ui_case_fields": {
                    "scenario_layer": "与 API case 一致：0=接口/组件层、1=Integration集成、2=E2E端到端。",
                    "scenario_type": "正常/异常/边界/权限/数据/流程。",
                    "scenario_tags": {
                        "description": "辅助标签：0=冒烟、1=回归、2=主流程、3=核心链路、4=高频、5=阻塞、6=线上巡检。",
                        "selection_guidance": [
                            "UI case 的 API/Integration/E2E 分层放在 scenario_layer，不放在 scenario_tags。",
                            "如果 UI case 不涉及 SQL 前后置、页面步骤 SQL、SQL 断言或数据工厂造数/清理，可默认增加 6=线上巡检。",
                            "依赖数据库状态、数据工厂准备数据或执行后清理的数据型 UI 用例，不建议默认打线上巡检标签。",
                        ],
                    },
                    "parametrize": [{"name": "参数组", "parametrize": [{"key": "name", "value": "AUTO"}]}],
                    "front_custom": [{"key": "tenant_id", "value": "${{tenant_id}}"}],
                    "front_sql": {
                        **ui_case_sql_schema,
                        "description": "UI case 执行前执行 SQL。sql 是 SQL 语句；查询结果第一行写入 SQL 缓存 key_list。",
                        "example": [{"sql": "SELECT id FROM user LIMIT 1", "key_list": "user", "datasource_alias": 2}],
                    },
                    "posterior_sql": {
                        **ui_case_sql_schema,
                        "description": "UI case 执行结束后执行 SQL。sql 是 SQL 语句；写操作通常不需要 key_list。",
                        "example": [{"sql": "UPDATE table SET valid=0 WHERE id=${{id}}", "datasource_alias": 2}],
                    },
                },
                "ui_public": ui_public_sql_schema,
                "flow_data": {
                    "format": {
                        "nodes": [{"id": "node-id", "position": {"x": 0, "y": 0}, "type": 0, "label": "点击", "config": {"id": 1}}],
                        "edges": [{"id": "edge-id", "source": {"node_id": "a", "position": "bottom"}, "target": {"node_id": "b", "position": "top"}}],
                    },
                    "rule": "nodes[].config.id 必须指向已保存的 PageStepsDetailed.id；保存步骤详情后同步更新对应节点 config.id。",
                },
                "page_step_detail": {
                    "type_0_or_1": "必须传 ope_key，ope_key 来自 get_ui_operation_methods/get_ui_assertion_methods 的叶子 value；ope_value 保存方法 parameter 数组并把输入写到 v。",
                    "type_2": {"sql_execute": [{"sql": "SELECT ...", "key_list": "cache_key"}]},
                    "type_3": {"custom": [{"key": "name", "value": "value"}]},
                    "type_4": {"condition_value": {"expect": "预期值"}},
                    "type_5": {"func": "python code"},
                },
                "case_data": "推荐通过 refresh_ui_case_step_cache_data 生成，不建议 AI 手工拼。",
                "dangerous_actions": "删除类必须先 preview_delete_*_impact，再传回 preview_token 和 confirm_text。",
                "notes": [
                    "创建 UI case 时，如果不涉及 SQL 和数据工厂，推荐把 scenario_tags 默认加上 6=线上巡检，方便后续按巡检集合筛选。",
                    "UI case 的 front_sql、posterior_sql 如在多数据库测试环境中使用，先调用 list_data_factory_datasource_aliases(project_product_id) 查询逻辑数据源 ID，再写入 datasource_alias。",
                    "page_step_detail.type=2 的 sql_execute 目前保持既有格式 [{sql,key_list}]，暂不在 MCP schema 中声明 datasource_alias。",
                    "UI 公共变量 type=1(SQL) 已接入 datasource_alias_id，创建或更新前先查询逻辑数据源并传入 datasource_alias_id。",
                ],
            }
        )

    @mcp.tool()
    def list_ui_public_variables(
        project_product_id: int,
        enabled_only: bool = False,
        type: int | None = None,
        test_env_id: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """查询 UI 公共变量。type: 0=自定义, 1=SQL；SQL 返回逻辑数据源 datasource_alias_id。"""
        queryset = UiPublic.objects.select_related("project_product", "datasource_alias").filter(project_product_id=project_product_id)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        if type is not None:
            if type not in UiPublicTypeEnum.get_key_list():
                return fail("UI 公共变量类型只支持 0=自定义、1=SQL。", "UI_PUBLIC_TYPE_INVALID")
            queryset = queryset.filter(type=type)
        if test_env_id is not None:
            queryset = queryset.filter(test_env=test_env_id)
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
                "type": item.type,
                "type_title": UiPublicTypeEnum.get_value(item.type),
                "name": item.name,
                "key": item.key,
                "value": item.value,
                "datasource_alias_id": item.datasource_alias_id,
                "datasource_alias_name": item.datasource_alias.name if item.datasource_alias_id else None,
                "status": item.status,
            }
            for item in queryset.order_by("test_env", "type", "-id")[offset : offset + page_size]
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def create_ui_public_variable(
        project_product_id: int,
        test_env_id: int,
        type: int,
        name: str,
        key: str,
        value: str,
        datasource_alias_id: int | None = None,
        status: int = 0,
    ) -> dict:
        """创建 UI 公共变量。type=1(SQL) 必须先调用 list_data_factory_datasource_aliases 查询逻辑数据源 datasource_alias_id。"""
        if type not in UiPublicTypeEnum.get_key_list():
            return fail("UI 公共变量类型只支持 0=自定义、1=SQL。", "UI_PUBLIC_TYPE_INVALID")
        if type == UiPublicTypeEnum.SQL.value and not datasource_alias_id:
            return fail("SQL UI 公共变量必须传逻辑数据源 datasource_alias_id。", "UI_PUBLIC_DATASOURCE_ALIAS_REQUIRED")
        data = UiPublicCRUD.inside_post(
            {
                "project_product": project_product_id,
                "test_env": test_env_id,
                "type": type,
                "name": name,
                "key": key,
                "value": value,
                "datasource_alias": datasource_alias_id,
                "status": status,
            }
        )
        return ok({"public_variable_id": data["id"], **data}, "UI 公共变量创建成功")

    @mcp.tool()
    def update_ui_public_variable(
        public_variable_id: int,
        type: int | None = None,
        test_env_id: int | None = None,
        name: str | None = None,
        key: str | None = None,
        value: str | None = None,
        datasource_alias_id: int | None = None,
        status: int | None = None,
    ) -> dict:
        """更新 UI 公共变量。SQL 类型需要传逻辑数据源 datasource_alias_id；自定义类型可不传。"""
        payload = {"id": public_variable_id}
        for field, field_value in {
            "type": type,
            "test_env": test_env_id,
            "name": name,
            "key": key,
            "value": value,
            "datasource_alias": datasource_alias_id,
            "status": status,
        }.items():
            if field_value is not None:
                payload[field] = field_value
        data = UiPublicCRUD.inside_put(public_variable_id, payload)
        return ok({"public_variable_id": data["id"], **data}, "UI 公共变量更新成功")

    @mcp.tool()
    def set_ui_public_variable_status(public_variable_id: int, status: int) -> dict:
        """启用或停用 UI 公共变量。status 通常 1=启用, 0=停用。"""
        data = UiPublicCRUD.inside_put(public_variable_id, {"id": public_variable_id, "status": status})
        return ok({"public_variable_id": data["id"], "status": data["status"]}, "UI 公共变量状态更新成功")

    @mcp.tool()
    def get_ui_operation_methods(page_type: int | None = None) -> dict:
        """查询 UI 操作方法树。page_type 传 DriveTypeEnum。"""
        return ok({"items": _method_tree_for("operation", page_type)})

    @mcp.tool()
    def get_ui_assertion_methods(page_type: int | None = None) -> dict:
        """查询 UI 断言方法树。page_type 传 DriveTypeEnum。"""
        return ok({"items": _method_tree_for("assertion", page_type)})

    @mcp.tool()
    def get_ui_public_assertion_methods() -> dict:
        """查询 UI 公共断言方法树。"""
        return ok({"items": _cache_method_tree(UI_METHOD_CACHE_KEYS["public_assertion"])})

    @mcp.tool()
    def search_ui_pages(project_product_id: int | None = None, module_id: int | None = None, keyword: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        """搜索 UI 页面。"""
        qs = Page.objects.select_related("project_product", "module").all()
        if project_product_id is not None:
            qs = qs.filter(project_product_id=project_product_id)
        if module_id is not None:
            qs = qs.filter(module_id=module_id)
        if keyword:
            qs = qs.filter(Q(name__contains=keyword) | Q(url__contains=keyword))
        return ok(_paged(qs.order_by("-id"), page, page_size, PageCRUD.serializer_class))

    @mcp.tool()
    def get_ui_page_detail(page_id: int) -> dict:
        """查询 UI 页面详情。"""
        return ok(model_to_dict(Page.objects.get(id=page_id)))

    @mcp.tool()
    def create_ui_page(project_product_id: int, module_id: int, name: str, url: str) -> dict:
        """创建 UI 页面。"""
        data = PageCRUD.inside_post({"project_product": project_product_id, "module": module_id, "name": name, "url": url})
        return ok({"page_id": data["id"], **data}, "UI 页面创建成功")

    @mcp.tool()
    def update_ui_page(page_id: int, name: str | None = None, url: str | None = None, module_id: int | None = None) -> dict:
        """更新 UI 页面。"""
        payload = {"id": page_id}
        for key, value in {"name": name, "url": url, "module": module_id}.items():
            if value is not None:
                payload[key] = value
        data = PageCRUD.inside_put(page_id, payload)
        return ok({"page_id": data["id"], **data}, "UI 页面更新成功")

    @mcp.tool()
    def search_ui_elements(page_id: int | None = None, keyword: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        """搜索 UI 元素。"""
        qs = PageElement.objects.select_related("page").all()
        if page_id is not None:
            qs = qs.filter(page_id=page_id)
        if keyword:
            qs = qs.filter(Q(name__contains=keyword) | Q(loc__contains=keyword))
        return ok(_paged(qs.order_by("-id"), page, page_size, PageElementCRUD.serializer_class))

    @mcp.tool()
    def get_ui_element_detail(element_id: int) -> dict:
        """查询 UI 元素详情。"""
        return ok(model_to_dict(PageElement.objects.get(id=element_id)))

    @mcp.tool()
    def create_ui_element(page_id: int, name: str, exp: int, loc: str, exp2: int | None = None, loc2: str | None = None, exp3: int | None = None, loc3: str | None = None, sleep: int | None = None, sub: int | None = None, sub2: int | None = None, sub3: int | None = None, is_iframe: int | None = 0, prompt: str | None = None) -> dict:
        """创建 UI 元素。exp/exp2/exp3 必须属于 ElementExpEnum。"""
        for field, value in {"exp": exp, "exp2": exp2, "exp3": exp3}.items():
            error = _validate_element_exp(value, field)
            if error:
                return error
        data = PageElementCRUD.inside_post({"page": page_id, "name": name, "exp": exp, "loc": loc, "exp2": exp2, "loc2": loc2, "exp3": exp3, "loc3": loc3, "sleep": sleep, "sub": sub, "sub2": sub2, "sub3": sub3, "is_iframe": is_iframe, "prompt": prompt})
        return ok({"element_id": data["id"], **data}, "UI 元素创建成功")

    @mcp.tool()
    def update_ui_element(element_id: int, fields: dict) -> dict:
        """更新 UI 元素。fields 使用 PageElement 字段名，exp/exp2/exp3 会校验枚举。"""
        for field in ["exp", "exp2", "exp3"]:
            if field in fields:
                error = _validate_element_exp(fields.get(field), field)
                if error:
                    return error
        data = PageElementCRUD.inside_put(element_id, {"id": element_id, **fields})
        return ok({"element_id": data["id"], **data}, "UI 元素更新成功")

    @mcp.tool()
    def set_ui_element_iframe(element_id: int, is_iframe: int) -> dict:
        """设置元素是否在 iframe 中。"""
        if is_iframe not in [0, 1]:
            return fail("is_iframe 只能是 0 或 1。", "INVALID_IFRAME_STATUS")
        PageElement.objects.filter(id=element_id).update(is_iframe=is_iframe)
        return ok({"element_id": element_id, "is_iframe": is_iframe}, "iframe 状态更新成功")

    @mcp.tool()
    def test_ui_element(element_payload: dict, test_env_id: int | None = None, is_send: bool = True) -> dict:
        """测试一个 UI 元素定位。element_payload 使用页面 test_element 接口同等结构。"""
        user = current_user()
        env_id = _selected_env(user.id, test_env_id)
        payload = {**element_payload, "test_env": env_id, "is_send": is_send}
        TestCase(user.id, user.username, env_id, is_send=is_send).test_element(payload)
        return ok({"client": ClientNameEnum.DRIVER.value}, "元素测试已发送执行器")

    @mcp.tool()
    def search_ui_page_steps(project_product_id: int | None = None, page_id: int | None = None, module_id: int | None = None, keyword: str | None = None, page: int = 1, page_size: int = 20) -> dict:
        """搜索 UI 页面步骤。"""
        qs = PageSteps.objects.select_related("project_product", "module", "page").all()
        if project_product_id is not None:
            qs = qs.filter(project_product_id=project_product_id)
        if page_id is not None:
            qs = qs.filter(page_id=page_id)
        if module_id is not None:
            qs = qs.filter(module_id=module_id)
        if keyword:
            qs = qs.filter(name__contains=keyword)
        return ok(_paged(qs.order_by("-id"), page, page_size, PageStepsCRUD.serializer_class))

    @mcp.tool()
    def get_ui_page_step_detail_full(page_step_id: int) -> dict:
        """查询 UI 页面步骤及步骤详情。"""
        step = PageSteps.objects.get(id=page_step_id)
        return ok({"page_step": model_to_dict(step), "details": [model_to_dict(item) for item in PageStepsDetailed.objects.filter(page_step_id=page_step_id).order_by("step_sort", "id")]})

    @mcp.tool()
    def create_ui_page_step(project_product_id: int, module_id: int, page_id: int, name: str, flow_data: dict | None = None) -> dict:
        """创建 UI 页面步骤。flow_data 可为空；保存详情后应更新节点 config.id。"""
        error = _validate_flow_data(flow_data)
        if error:
            return error
        data = PageStepsCRUD.inside_post({"project_product": project_product_id, "module": module_id, "page": page_id, "name": name, "flow_data": flow_data or {}, "status": TaskEnum.STAY_BEGIN.value})
        return ok({"page_step_id": data["id"], **data}, "UI 页面步骤创建成功")

    @mcp.tool()
    def update_ui_page_step(page_step_id: int, fields: dict) -> dict:
        """更新 UI 页面步骤。若传 flow_data，会校验 nodes/edges 结构。"""
        if "flow_data" in fields:
            error = _validate_flow_data(fields.get("flow_data"), require_config_ids=bool(fields.get("flow_data", {}).get("nodes")))
            if error:
                return error
        data = PageStepsCRUD.inside_put(page_step_id, {"id": page_step_id, **fields})
        return ok({"page_step_id": data["id"], **data}, "UI 页面步骤更新成功")

    @mcp.tool()
    def copy_ui_page_step(page_step_id: int) -> dict:
        """复制 UI 页面步骤及其步骤详情。"""
        source = PageSteps.objects.get(id=page_step_id)
        payload = model_to_dict(source)
        del payload["id"]
        payload["name"] = f"(副本){source.name}"
        payload["status"] = StatusEnum.FAIL.value
        created = PageStepsCRUD.inside_post(payload)
        for detail in PageStepsDetailed.objects.filter(page_step_id=page_step_id):
            detail_payload = model_to_dict(detail)
            del detail_payload["id"]
            detail_payload["page_step"] = created["id"]
            PageStepsDetailedCRUD.inside_post(detail_payload)
        return ok({"page_step_id": created["id"], **created}, "UI 页面步骤复制成功")

    @mcp.tool()
    def run_ui_page_step(page_step_id: int, test_env_id: int | None = None, is_send: bool = True) -> dict:
        """执行 UI 页面步骤，依赖执行器在线。"""
        user = current_user()
        env_id = _selected_env(user.id, test_env_id)
        result = TestCase(user.id, user.username, env_id, is_send=is_send).test_steps(page_step_id)
        return ok(result.model_dump(), "UI 页面步骤执行完成")

    @mcp.tool()
    def list_ui_page_step_details(page_step_id: int) -> dict:
        """查询页面步骤详情。"""
        return ok({"items": [model_to_dict(item) for item in PageStepsDetailed.objects.filter(page_step_id=page_step_id).order_by("step_sort", "id")]})

    @mcp.tool()
    def create_ui_page_step_detail(page_step_id: int, node_id: str, type: int, flow_data: dict, ope_key: str | None = None, ope_value: list | None = None, ele_name_id: int | None = None, sql_execute: list | None = None, custom: list | None = None, condition_value: dict | None = None, func: str | None = None, step_sort: int = 0, page_type: int | None = None) -> dict:
        """创建页面步骤详情，并把新 id 回写到 flow_data.nodes[].config.id。"""
        error = _validate_flow_data(flow_data)
        if error:
            return error
        payload = {"page_step": page_step_id, "type": type, "ope_key": ope_key, "ope_value": ope_value or [], "ele_name": ele_name_id, "sql_execute": sql_execute, "custom": custom, "condition_value": condition_value, "func": func, "step_sort": step_sort}
        error = _validate_page_step_detail_payload(payload, page_type=page_type)
        if error:
            return error
        data = PageStepsDetailedCRUD.inside_post(payload)
        for node in flow_data.get("nodes") or []:
            if node.get("id") == node_id:
                node.setdefault("config", {})["id"] = data["id"]
        PageStepsCRUD.inside_put(page_step_id, {"id": page_step_id, "flow_data": flow_data})
        PageStepsDetailedCRUD().callback(page_step_id)
        return ok({"page_step_detail_id": data["id"], "flow_data": flow_data, **data}, "页面步骤详情创建成功")

    @mcp.tool()
    def update_ui_page_step_detail(detail_id: int, fields: dict, page_type: int | None = None) -> dict:
        """更新页面步骤详情。fields 使用 PageStepsDetailed 字段名，会校验 type/ope_key/ope_value。"""
        current = model_to_dict(PageStepsDetailed.objects.get(id=detail_id))
        payload = {**current, **fields, "id": detail_id}
        error = _validate_page_step_detail_payload(payload, page_type=page_type)
        if error:
            return error
        data = PageStepsDetailedCRUD.inside_put(detail_id, payload)
        PageStepsDetailedCRUD().callback(data["page_step"])
        return ok({"page_step_detail_id": data["id"], **data}, "页面步骤详情更新成功")

    @mcp.tool()
    def sort_ui_page_step_details(page_step_id: int, details: list[dict]) -> dict:
        """排序页面步骤详情。details 格式为 [{id, step_sort}]。"""
        for item in details:
            PageStepsDetailed.objects.filter(id=item["id"], page_step_id=page_step_id).update(step_sort=item["step_sort"])
        PageStepsDetailedCRUD().callback(page_step_id)
        return ok({"page_step_id": page_step_id, "details": details}, "页面步骤详情排序成功")

    @mcp.tool()
    def search_ui_cases(project_product_id: int | None = None, module_id: int | None = None, keyword: str | None = None, case_people_id: int | None = None, level: int | None = None, scenario_layer: int | None = None, scenario_type: int | None = None, scenario_tags: list[int] | None = None, status: int | None = None, page: int = 1, page_size: int = 20) -> dict:
        """搜索 UI case。"""
        qs = UiCase.objects.select_related("project_product", "module", "case_people").all()
        for field, value in {"project_product_id": project_product_id, "module_id": module_id, "case_people_id": case_people_id, "level": level, "scenario_layer": scenario_layer, "scenario_type": scenario_type, "status": status}.items():
            if value is not None:
                qs = qs.filter(**{field: value})
        if scenario_tags:
            tag_query = Q()
            for tag in scenario_tags:
                tag_query |= Q(scenario_tags__contains=[tag])
            qs = qs.filter(tag_query)
        if keyword:
            qs = qs.filter(name__contains=keyword)
        return ok(_paged(qs.order_by("-id"), page, page_size, UiCaseCRUD.serializer_class))

    @mcp.tool()
    def get_ui_case_detail_full(case_id: int, include_result_data: bool = True) -> dict:
        """查询 UI case 完整详情树。"""
        return ok(_case_tree(case_id, include_result_data=include_result_data))

    @mcp.tool()
    def create_ui_case(project_product_id: int, module_id: int, name: str, case_people_id: int | None = None, level: int = 1, scenario_layer: int = 0, scenario_type: int = 0, scenario_tags: list[int] | None = None, scenario_description: str | None = None, parametrize: list | None = None, front_custom: list | None = None, front_sql: list | None = None, posterior_sql: list | None = None) -> dict:
        """创建 UI case 主体。负责人未传时使用当前 MCP 用户；不涉及 SQL 和数据工厂时可默认给 scenario_tags 增加 6=线上巡检。"""
        if case_people_id is None:
            case_people_id = current_user().id
        data = UiCaseCRUD.inside_post({"project_product": project_product_id, "module": module_id, "name": name, "case_people": case_people_id, "level": level, "scenario_layer": scenario_layer, "scenario_type": scenario_type, "scenario_tags": scenario_tags or [], "scenario_description": scenario_description, "parametrize": parametrize or [], "front_custom": front_custom or [], "front_sql": front_sql or [], "posterior_sql": posterior_sql or []})
        return ok({"case_id": data["id"], **data}, "UI case 创建成功")

    @mcp.tool()
    def update_ui_case(case_id: int, fields: dict) -> dict:
        """更新 UI case 主体。fields 使用 UiCase 字段名。"""
        data = UiCaseCRUD.inside_put(case_id, {"id": case_id, **fields})
        return ok({"case_id": data["id"], **data}, "UI case 更新成功")

    @mcp.tool()
    def copy_ui_case(case_id: int) -> dict:
        """复制 UI case 及其用例步骤。"""
        source = UiCase.objects.get(id=case_id)
        payload = model_to_dict(source)
        del payload["id"]
        payload["name"] = f"(副本){source.name}"
        payload["status"] = StatusEnum.FAIL.value
        created = UiCaseCRUD.inside_post(payload)
        for step in UiCaseStepsDetailed.objects.filter(case_id=case_id):
            step_payload = model_to_dict(step)
            del step_payload["id"]
            step_payload["case"] = created["id"]
            UiCaseStepsDetailedCRUD.inside_post(step_payload)
        return ok({"case_id": created["id"], **created}, "UI case 复制成功")

    @mcp.tool()
    def add_ui_case_step(case_id: int, page_step_id: int, case_sort: int | None = None, switch_step_open_url: int = 0, error_retry: int | None = None, retry_interval: int | None = None) -> dict:
        """给 UI case 添加页面步骤。添加后建议调用 refresh_ui_case_step_cache_data；当前模型未保存 retry_interval。"""
        if case_sort is None:
            case_sort = UiCaseStepsDetailed.objects.filter(case_id=case_id).count()
        data = UiCaseStepsDetailedCRUD.inside_post({"case": case_id, "page_step": page_step_id, "case_sort": case_sort, "switch_step_open_url": switch_step_open_url, "error_retry": error_retry})
        UiCaseStepsDetailedCRUD().callback(case_id)
        warnings = ["当前 UiCaseStepsDetailed 模型没有 retry_interval 字段，已忽略该参数。"] if retry_interval is not None else []
        return ok({"case_step_id": data["id"], **data}, "UI case 步骤添加成功", warnings=warnings)

    @mcp.tool()
    def list_ui_case_steps(case_id: int) -> dict:
        """查询 UI case 步骤。"""
        items = [model_to_dict(item) for item in UiCaseStepsDetailed.objects.filter(case_id=case_id).order_by("case_sort")]
        return ok({"items": items})

    @mcp.tool()
    def sort_ui_case_steps(case_id: int, steps: list[dict]) -> dict:
        """排序 UI case 步骤。steps 格式为 [{id, case_sort}]。"""
        for item in steps:
            UiCaseStepsDetailed.objects.filter(id=item["id"], case_id=case_id).update(case_sort=item["case_sort"])
        UiCaseStepsDetailedCRUD().callback(case_id)
        return ok({"case_id": case_id, "steps": steps}, "UI case 步骤排序成功")

    @mcp.tool()
    def refresh_ui_case_step_cache_data(case_step_id: int | None = None, case_id: int | None = None) -> dict:
        """从页面步骤详情同步生成 UI case step 的 case_data。"""
        targets = UiCaseStepsDetailed.objects.filter(id=case_step_id) if case_step_id else UiCaseStepsDetailed.objects.filter(case_id=case_id)
        if not targets.exists():
            return fail("未找到 UI case step。", "UI_CASE_STEP_NOT_FOUND")
        updated = []
        for step in targets:
            flow_data = step.page_step.flow_data if step.page_step else None
            error = _validate_flow_data(flow_data, require_config_ids=True)
            if error:
                return error
            case_data = []
            for detail in PageStepsDetailed.objects.filter(page_step_id=step.page_step_id).order_by("step_sort", "id"):
                if detail.type in [ElementOperationEnum.OPE.value, ElementOperationEnum.ASS.value, ElementOperationEnum.CONDITION.value]:
                    detail_data = detail.ope_value
                elif detail.type == ElementOperationEnum.SQL.value:
                    detail_data = detail.sql_execute
                elif detail.type == ElementOperationEnum.CUSTOM.value:
                    detail_data = detail.custom
                elif detail.type == ElementOperationEnum.PYTHON_CODE.value:
                    detail_data = [{"func": detail.func}]
                else:
                    detail_data = None
                case_data.append({"type": detail.type, "ope_key": detail.ope_key, "page_step_details_id": detail.id, "page_step_details_name": detail.ele_name.name if detail.ele_name else None, "condition_value": detail.condition_value, "page_step_details_data": detail_data})
            step.case_data = case_data
            step.save()
            updated.append({"case_step_id": step.id, "case_data_count": len(case_data)})
        return ok({"updated": updated}, "UI case step 缓存数据刷新成功")

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
        first = UiCase.objects.get(id=case_ids[0])
        project_id = first.project_product.project_id
        for case_id in case_ids:
            if UiCase.objects.get(id=case_id).project_product.project_id != project_id:
                return fail("批量执行的 UI case 必须属于同一个项目。", "CASE_PROJECT_MISMATCH")
        add_tasks = AddTasks(project_product=first.project_product_id, test_env=env_id, is_notice=StatusEnum.FAIL.value, user_id=user.id)
        for case_id in case_ids:
            add_tasks.add_test_suite_details(case_id, TestCaseTypeEnum.UI)
        return ok({"case_ids": case_ids, "test_env_id": env_id, "client": ClientNameEnum.DRIVER.value}, "UI case 批量执行任务创建成功")

    @mcp.tool()
    def get_ui_case_run_result(case_id: int) -> dict:
        """查询 UI case 最近一次执行结果。"""
        case = UiCase.objects.get(id=case_id)
        return ok({"case_id": case.id, "status": case.status, "result_data": getattr(case, "result_data", None)})

    def _preview_delete(model, item_id: int, action: str, name: str) -> dict:
        item = model.objects.filter(id=item_id).first()
        if not item:
            return fail("数据不存在。", "NOT_FOUND")
        return _delete_preview(action, item_id, f"{action.upper()}:{item_id}", {"id": item_id, "name": getattr(item, "name", None), "model": model.__name__})

    def _delete(model, item_id: int, action: str, token: str | None, text: str | None) -> dict:
        error = validate_dangerous_action_confirmation(action, item_id, token, text)
        if error:
            return error
        model.objects.get(id=item_id).delete()
        return ok({"id": item_id}, "删除成功")

    @mcp.tool()
    def preview_delete_ui_page_impact(page_id: int) -> dict:
        return _preview_delete(Page, page_id, "delete_ui_page", "UI 页面")

    @mcp.tool()
    def delete_ui_page(page_id: int, preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        return _delete(Page, page_id, "delete_ui_page", preview_token, confirm_text)

    @mcp.tool()
    def preview_delete_ui_element_impact(element_id: int) -> dict:
        return _preview_delete(PageElement, element_id, "delete_ui_element", "UI 元素")

    @mcp.tool()
    def delete_ui_element(element_id: int, preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        return _delete(PageElement, element_id, "delete_ui_element", preview_token, confirm_text)

    @mcp.tool()
    def preview_delete_ui_page_step_impact(page_step_id: int) -> dict:
        return _preview_delete(PageSteps, page_step_id, "delete_ui_page_step", "UI 页面步骤")

    @mcp.tool()
    def delete_ui_page_step(page_step_id: int, preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        return _delete(PageSteps, page_step_id, "delete_ui_page_step", preview_token, confirm_text)

    @mcp.tool()
    def preview_delete_ui_page_step_detail_impact(detail_id: int) -> dict:
        return _preview_delete(PageStepsDetailed, detail_id, "delete_ui_page_step_detail", "UI 页面步骤详情")

    @mcp.tool()
    def delete_ui_page_step_detail(detail_id: int, preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        detail = PageStepsDetailed.objects.filter(id=detail_id).first()
        page_step_id = detail.page_step_id if detail else None
        result = _delete(PageStepsDetailed, detail_id, "delete_ui_page_step_detail", preview_token, confirm_text)
        if result.get("success") and page_step_id:
            PageStepsDetailedCRUD().callback(page_step_id)
        return result

    @mcp.tool()
    def preview_delete_ui_case_impact(case_id: int) -> dict:
        return _preview_delete(UiCase, case_id, "delete_ui_case", "UI case")

    @mcp.tool()
    def delete_ui_case(case_id: int, preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        return _delete(UiCase, case_id, "delete_ui_case", preview_token, confirm_text)

    @mcp.tool()
    def preview_delete_ui_case_step_impact(case_step_id: int) -> dict:
        return _preview_delete(UiCaseStepsDetailed, case_step_id, "delete_ui_case_step", "UI case step")

    @mcp.tool()
    def delete_ui_case_step(case_step_id: int, preview_token: str | None = None, confirm_text: str | None = None) -> dict:
        step = UiCaseStepsDetailed.objects.filter(id=case_step_id).first()
        case_id = step.case_id if step else None
        result = _delete(UiCaseStepsDetailed, case_step_id, "delete_ui_case_step", preview_token, confirm_text)
        if result.get("success") and case_id:
            UiCaseStepsDetailedCRUD().callback(case_id)
        return result

from __future__ import annotations

import json as jsonlib
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

from curlparser import parse
from django.db import transaction
from django.forms import model_to_dict
from genson import SchemaBuilder

from src.auto_test.auto_api.models import ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter, ApiHeaders, ApiInfo, ApiPublic
from src.auto_test.auto_system.models import CacheData
from src.auto_test.auto_api.service.test_case.test_api_info import TestApiInfo
from src.auto_test.auto_api.service.test_case.test_case import TestCase
from src.auto_test.auto_api.views.api_case import ApiCaseCRUD, ApiCaseSerializersC
from src.auto_test.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD
from src.auto_test.auto_api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD
from src.auto_test.auto_api.views.api_headers import ApiHeadersCRUD
from src.auto_test.auto_api.views.api_info import ApiInfoCRUD
from src.auto_test.auto_api.views.api_pulic import ApiPublicCRUD
from src.auto_test.auto_user.models import User
from src.enums.api_enum import ApiPublicTypeEnum, MethodEnum
from src.enums.system_enum import CacheDataKey2Enum
from src.enums.tools_enum import StatusEnum, TestCaseTypeEnum
from src.mcp_server.common import current_user, fail, ok


def _json_string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return value
    return jsonlib.dumps(value, ensure_ascii=False, indent=4)


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, tuple, set)):
        return all(_is_empty_value(item) for item in value)
    if isinstance(value, dict):
        return all(_is_empty_value(item) for item in value.values())
    return False


def _clean_list_rows(value: Any) -> list:
    if not isinstance(value, list):
        return []
    return [item for item in value if not _is_empty_value(item)]


def _normalize_scenario_payload(payload: dict) -> dict:
    normalized = dict(payload)
    for key in ("params", "data", "json"):
        if key in normalized:
            normalized[key] = _json_string(normalized[key])
    for key in (
        "headers",
        "front_sql",
        "posterior_response",
        "posterior_response_text",
        "posterior_sql",
    ):
        if key in normalized:
            normalized[key] = _clean_list_rows(normalized[key])
    if "ass_general" in normalized:
        normalized["ass_general"] = _normalize_ass_general(normalized["ass_general"])
    if "ass_jsonpath" in normalized:
        normalized["ass_jsonpath"] = _normalize_ass_jsonpath(normalized["ass_jsonpath"])
    return normalized


def _normalize_ass_general(assertions: list | None) -> list:
    """Keep general assertion parameter values UI-friendly.

    The frontend renders each parameter value in a textarea, while the SQL
    assertion executor already converts JSON strings back to dict/list values.
    Store dict/list parameter values as JSON strings so MCP-created assertions
    match the normal page-editing shape.
    """
    normalized = _clean_list_rows(assertions)
    for assertion in normalized:
        if not isinstance(assertion, dict):
            continue
        value = assertion.get("value")
        if not isinstance(value, dict):
            continue
        parameters = value.get("parameter")
        if not isinstance(parameters, list):
            continue
        for parameter in parameters:
            if not isinstance(parameter, dict):
                continue
            parameter_value = parameter.get("v")
            if isinstance(parameter_value, (dict, list)):
                parameter["v"] = jsonlib.dumps(parameter_value, ensure_ascii=False)
    return normalized


def _normalize_ass_jsonpath(assertions: list | None) -> list:
    """Normalize JSONPath assertion field names to the executor's actual/method/expect shape."""
    if not assertions:
        return []
    normalized = []
    for item in assertions:
        if not isinstance(item, dict):
            continue
        actual = item.get("actual", item.get("path"))
        method = item.get("method", item.get("operator"))
        expect = item.get("expect", item.get("value"))
        if _is_empty_value({"actual": actual, "method": method, "expect": expect}):
            continue
        normalized.append(
            {
                "actual": actual,
                "method": method,
                "expect": "" if expect is None else str(expect),
            }
        )
    return normalized


def _api_assertion_method_groups() -> list[dict]:
    cache_data = CacheData.objects.get(key=CacheDataKey2Enum.ASS_SELECT_VALUE.value)
    return jsonlib.loads(cache_data.value)


def _flatten_assertion_methods(groups: list[dict]) -> list[dict]:
    methods = []

    def walk(items: list[dict], parents: list[str]) -> None:
        for item in items or []:
            children = item.get("children") or []
            label = item.get("label") or item.get("value")
            if children:
                walk(children, [*parents, label])
                continue
            value = item.get("value")
            if not value:
                continue
            methods.append(
                {
                    "value": value,
                    "label": label,
                    "path": " / ".join([*parents, label]),
                    "parameter": item.get("parameter") or [],
                }
            )

    walk(groups, [])
    return methods


def _content_assertion_methods(groups: list[dict]) -> list[dict]:
    for group in groups:
        if group.get("value") == "内容断言":
            return group.get("children") or []
    return []


def _general_assertion_template(method_value: str, actual: Any = "", expect: Any = "") -> dict:
    methods = _flatten_assertion_methods(_api_assertion_method_groups())
    method = next((item for item in methods if item["value"] == method_value), None)
    if method is None:
        raise ValueError(f"断言方法不存在: {method_value}")
    value = {
        "value": method["value"],
        "label": method["label"],
        "parameter": method["parameter"],
    }
    for parameter in value["parameter"]:
        if parameter.get("f") == "actual":
            parameter["v"] = actual
        elif parameter.get("f") == "expect":
            parameter["v"] = expect
    return {"method": method["path"], "value": value}


def _case_owner_required() -> dict:
    return fail(
        "创建 API case 需要指定负责人 case_people_id。请先调用 list_case_owners 查询可选负责人，并询问用户选择绑定给谁。",
        "CASE_OWNER_REQUIRED",
        {
            "required_field": "case_people_id",
            "next_actions": [
                "调用 list_case_owners 查询可选负责人",
                "向用户展示负责人列表并询问 case 要绑定给谁",
                "用户选择后再次调用 create_api_case 或 create_complete_api_case",
            ],
        },
    )


def _case_tree(case_id: int, include_result_data: bool = True) -> dict:
    case = ApiCase.objects.select_related("project_product", "project_product__project", "module", "case_people").get(
        id=case_id
    )
    case_data = ApiCaseSerializersC(instance=case).data
    steps = []
    details = (
        ApiCaseDetailed.objects.select_related("api_info")
        .filter(case_id=case_id)
        .order_by("case_sort", "id")
    )
    for detail in details:
        api_info = detail.api_info
        parameters = []
        for parameter in ApiCaseDetailedParameter.objects.filter(case_detailed_id=detail.id).order_by("id"):
            parameter_data = model_to_dict(parameter)
            if not include_result_data:
                parameter_data.pop("result_data", None)
            parameters.append(parameter_data)
        detail_data = model_to_dict(detail)
        api_info_data = model_to_dict(api_info)
        if not include_result_data:
            api_info_data.pop("result_data", None)
        steps.append(
            {
                "detail": detail_data,
                "api_info": api_info_data,
                "parameters": parameters,
            }
        )
    return {"case": case_data, "steps": steps}


def _create_case_step(case_id: int, api_info_id: int, case_sort: int | None = None) -> dict:
    api_info_obj = ApiInfo.objects.get(id=api_info_id)
    if case_sort is None:
        case_sort = ApiCaseDetailed.objects.filter(case_id=case_id).count()
    detail = ApiCaseDetailedCRUD.inside_post(
        {
            "case": case_id,
            "api_info": api_info_id,
            "case_sort": case_sort,
        }
    )
    parameter = ApiCaseDetailedParameterCRUD.inside_post(
        {
            "case_detailed": detail["id"],
            "name": api_info_obj.name,
            "headers": [],
            "params": api_info_obj.params,
            "data": api_info_obj.data,
            "json": api_info_obj.json,
            "file": api_info_obj.file,
        }
    )
    ApiCaseDetailedCRUD().callback(case_id)
    return {
        "step_id": detail["id"],
        "case_id": case_id,
        "api_info_id": api_info_id,
        "case_sort": case_sort,
        "default_parameter_id": parameter["id"],
    }


def _selected_env(user_id: int | None, test_env_id: int | None) -> int:
    if test_env_id is not None:
        return test_env_id
    user = current_user(user_id)
    if user.selected_environment is None:
        raise ValueError("当前用户未选择测试环境，请先调用 switch_user_test_environment")
    return int(user.selected_environment)


def _find_json_paths(data: Any, prefix: str = "$", limit: int = 20) -> list[tuple[str, Any]]:
    paths: list[tuple[str, Any]] = []
    if len(paths) >= limit:
        return paths
    if isinstance(data, dict):
        for key, value in data.items():
            child_prefix = f"{prefix}.{key}"
            if isinstance(value, (dict, list)):
                paths.extend(_find_json_paths(value, child_prefix, limit - len(paths)))
            else:
                paths.append((child_prefix, value))
            if len(paths) >= limit:
                break
    elif isinstance(data, list) and data:
        paths.extend(_find_json_paths(data[0], f"{prefix}[0]", limit))
    return paths[:limit]


def register_api_automation_tools(mcp):
    @mcp.tool()
    def list_api_headers(project_product_id: int, enabled_only: bool = False) -> dict:
        """查询项目产品公共请求头。"""
        queryset = ApiHeaders.objects.filter(project_product_id=project_product_id)
        if enabled_only:
            queryset = queryset.filter(status=1)
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
                ]
            }
        )

    @mcp.tool()
    def create_api_header(project_product_id: int, key: str, value: str, status: int = 0) -> dict:
        """创建项目产品公共请求头。"""
        data = ApiHeadersCRUD.inside_post(
            {
                "project_product": project_product_id,
                "key": key,
                "value": value,
                "status": status,
            }
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
        data = ApiHeadersCRUD.inside_put(header_id, payload)
        return ok({"header_id": data["id"], **data}, "公共请求头更新成功")

    @mcp.tool()
    def list_api_public_variables(
        project_product_id: int,
        enabled_only: bool = False,
        type: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """查询 API 全局变量。type: 0=自定义, 1=SQL, 2=登录。"""
        queryset = ApiPublic.objects.select_related("project_product").filter(project_product_id=project_product_id)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        if type is not None:
            queryset = queryset.filter(type=type)
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
                "type": item.type,
                "type_title": ApiPublicTypeEnum.get_value(item.type),
                "name": item.name,
                "key": item.key,
                "value": item.value,
                "status": item.status,
            }
            for item in queryset.order_by("type", "-id")[offset : offset + page_size]
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def create_api_public_variable(
        project_product_id: int,
        type: int,
        name: str,
        key: str,
        value: str,
        status: int = 0,
    ) -> dict:
        """创建 API 全局变量。type: 0=自定义, 1=SQL, 2=登录。"""
        data = ApiPublicCRUD.inside_post(
            {
                "project_product": project_product_id,
                "type": type,
                "name": name,
                "key": key,
                "value": value,
                "status": status,
            }
        )
        return ok({"public_variable_id": data["id"], **data}, "API 全局变量创建成功")

    @mcp.tool()
    def update_api_public_variable(
        public_variable_id: int,
        type: int | None = None,
        name: str | None = None,
        key: str | None = None,
        value: str | None = None,
        status: int | None = None,
    ) -> dict:
        """更新 API 全局变量。"""
        payload: dict[str, Any] = {"id": public_variable_id}
        for field, field_value in {
            "type": type,
            "name": name,
            "key": key,
            "value": value,
            "status": status,
        }.items():
            if field_value is not None:
                payload[field] = field_value
        data = ApiPublicCRUD.inside_put(public_variable_id, payload)
        return ok({"public_variable_id": data["id"], **data}, "API 全局变量更新成功")

    @mcp.tool()
    def set_api_public_variable_status(public_variable_id: int, status: int) -> dict:
        """启用或停用 API 全局变量。status 通常 1=启用, 0=停用。"""
        data = ApiPublicCRUD.inside_put(public_variable_id, {"id": public_variable_id, "status": status})
        return ok({"public_variable_id": data["id"], "status": data["status"]}, "API 全局变量状态更新成功")

    @mcp.tool()
    def search_api_infos(
        project_product_id: int | None = None,
        module_id: int | None = None,
        keyword: str | None = None,
        method: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """搜索接口定义。"""
        queryset = ApiInfo.objects.select_related("project_product", "module").all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if method is not None:
            queryset = queryset.filter(method=method)
        if keyword:
            queryset = queryset.filter(name__contains=keyword) | queryset.filter(url__contains=keyword)
        count = queryset.count()
        offset = max(page - 1, 0) * page_size
        items = [
            {
                "id": item.id,
                "name": item.name,
                "url": item.url,
                "method": item.method,
                "method_title": MethodEnum.get_value(item.method),
                "project_product_id": item.project_product_id,
                "module_id": item.module_id,
            }
            for item in queryset.order_by("-id")[offset : offset + page_size]
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_api_info_detail(api_info_id: int) -> dict:
        """查询接口定义详情。"""
        item = ApiInfo.objects.get(id=api_info_id)
        return ok(model_to_dict(item))

    @mcp.tool()
    def create_api_info(
        project_product_id: int,
        module_id: int,
        name: str,
        url: str,
        method: int,
        params: str | dict | list | None = None,
        data: str | dict | list | None = None,
        json_body: str | dict | list | None = None,
        file: dict | list | None = None,
        type: int = 1,
    ) -> dict:
        """创建 API 接口定义。params/data/json_body 请传 JSON 字符串或对象。ApiInfo.headers 默认保持 null。"""
        if method not in MethodEnum.get_key_list():
            return fail("请求方法不存在", "METHOD_NOT_FOUND", {"method": method})
        data_obj = ApiInfoCRUD.inside_post(
            {
                "project_product": project_product_id,
                "module": module_id,
                "name": name,
                "url": url,
                "method": method,
                "headers": None,
                "params": _json_string(params),
                "data": _json_string(data),
                "json": _json_string(json_body),
                "file": file,
                "type": type,
            }
        )
        return ok({"api_info_id": data_obj["id"], **data_obj}, "接口定义创建成功")

    @mcp.tool()
    def create_api_info_from_curl(
        project_product_id: int,
        module_id: int,
        name: str,
        curl_command: str,
        type: int = 1,
    ) -> dict:
        """根据 curl 命令创建 API 接口定义。"""
        if not curl_command.strip().startswith("curl"):
            return fail("curl 命令格式不正确", "INVALID_CURL")
        parsed = parse(curl_command)
        url_components = urlparse(parsed.url)
        path = url_components.path
        payload: dict[str, Any] = {
            "project_product": project_product_id,
            "module": module_id,
            "name": name,
            "url": path,
            "method": MethodEnum.get_key(parsed.method),
            "headers": None,
            "type": type,
        }
        query_params = parse_qs(url_components.query)
        params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
        if params:
            payload["params"] = _json_string(params)
        if parsed.json and parsed.data:
            payload["json"] = _json_string(parsed.json)
        elif parsed.json is None and parsed.data:
            payload["data"] = _json_string(parsed.data)
        elif parsed.json and parsed.data is None:
            payload["json"] = _json_string(parsed.json)
        data_obj = ApiInfoCRUD.inside_post(payload)
        return ok({"api_info_id": data_obj["id"], **data_obj}, "接口定义创建成功")

    @mcp.tool()
    def update_api_info(
        api_info_id: int,
        name: str | None = None,
        url: str | None = None,
        method: int | None = None,
        params: str | dict | list | None = None,
        data: str | dict | list | None = None,
        json_body: str | dict | list | None = None,
        file: dict | list | None = None,
    ) -> dict:
        """更新 API 接口定义。"""
        payload: dict[str, Any] = {"id": api_info_id}
        for key, value in {
            "name": name,
            "url": url,
            "method": method,
            "params": _json_string(params),
            "data": _json_string(data),
            "json": _json_string(json_body),
            "file": file,
        }.items():
            if value is not None:
                payload[key] = value
        data_obj = ApiInfoCRUD.inside_put(api_info_id, payload)
        return ok({"api_info_id": data_obj["id"], **data_obj}, "接口定义更新成功")

    @mcp.tool()
    def run_api_info(api_info_id: int, test_env_id: int | None = None, user_id: int | None = None) -> dict:
        """调试执行单个接口定义并返回请求、响应和错误信息。"""
        try:
            user = current_user(user_id)
            env_id = _selected_env(user.id, test_env_id)
            result = TestApiInfo(user.id, env_id).api_info_run(api_info_id)
        except Exception as exc:
            return fail(str(exc), "API_INFO_RUN_FAILED")
        return ok(result, "接口执行完成")

    @mcp.tool()
    def search_api_cases(
        project_product_id: int | None = None,
        module_id: int | None = None,
        keyword: str | None = None,
        case_people_id: int | None = None,
        level: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """搜索 API case。"""
        queryset = ApiCase.objects.select_related("project_product", "module", "case_people").all()
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if module_id is not None:
            queryset = queryset.filter(module_id=module_id)
        if case_people_id is not None:
            queryset = queryset.filter(case_people_id=case_people_id)
        if level is not None:
            queryset = queryset.filter(level=level)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        count = queryset.count()
        offset = max(page - 1, 0) * page_size
        items = [
            {
                "id": item.id,
                "name": item.name,
                "project_product_id": item.project_product_id,
                "module_id": item.module_id,
                "case_people_id": item.case_people_id,
                "case_flow": item.case_flow,
                "level": item.level,
                "status": item.status,
            }
            for item in queryset.order_by("-id")[offset : offset + page_size]
        ]
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def create_api_case(
        project_product_id: int,
        module_id: int,
        name: str,
        case_people_id: int | None = None,
        level: int = 1,
        front_custom: list | None = None,
        front_sql: list | None = None,
        front_headers: list[int] | None = None,
        posterior_sql: list | None = None,
    ) -> dict:
        """创建 API case 主体。未提供 case_people_id 时应先查询负责人并询问用户选择。"""
        if case_people_id is None:
            return _case_owner_required()
        data_obj = ApiCaseCRUD.inside_post(
            {
                "project_product": project_product_id,
                "module": module_id,
                "name": name,
                "case_people": case_people_id,
                "level": level,
                "front_custom": front_custom or [],
                "front_sql": front_sql or [],
                "front_headers": front_headers or [],
                "posterior_sql": posterior_sql or [],
            }
        )
        return ok({"case_id": data_obj["id"], **data_obj}, "API case 创建成功")

    @mcp.tool()
    def update_api_case(
        case_id: int,
        name: str | None = None,
        level: int | None = None,
        front_custom: list | None = None,
        front_sql: list | None = None,
        front_headers: list[int] | None = None,
        posterior_sql: list | None = None,
    ) -> dict:
        """更新 API case 主体配置。"""
        payload: dict[str, Any] = {"id": case_id}
        for key, value in {
            "name": name,
            "level": level,
            "front_custom": front_custom,
            "front_sql": front_sql,
            "front_headers": front_headers,
            "posterior_sql": posterior_sql,
        }.items():
            if value is not None:
                payload[key] = value
        data_obj = ApiCaseCRUD.inside_put(case_id, payload)
        return ok({"case_id": data_obj["id"], **data_obj}, "API case 更新成功")

    @mcp.tool()
    def add_api_case_step(case_id: int, api_info_id: int, case_sort: int | None = None) -> dict:
        """给 API case 添加接口步骤，并自动创建默认场景参数。"""
        try:
            with transaction.atomic():
                data = _create_case_step(case_id, api_info_id, case_sort)
        except Exception as exc:
            return fail(str(exc), "ADD_API_CASE_STEP_FAILED")
        return ok(data, "API case 步骤添加成功")

    @mcp.tool()
    def list_api_case_steps(case_id: int) -> dict:
        """查询 API case 步骤。"""
        steps = []
        queryset = ApiCaseDetailed.objects.select_related("api_info").filter(case_id=case_id).order_by("case_sort")
        for item in queryset:
            steps.append(
                {
                    "step_id": item.id,
                    "case_id": item.case_id,
                    "api_info_id": item.api_info_id,
                    "api_name": item.api_info.name,
                    "case_sort": item.case_sort,
                    "status": item.status,
                    "error_message": item.error_message,
                }
            )
        return ok({"items": steps})

    @mcp.tool()
    def sort_api_case_steps(case_id: int, steps: list[dict]) -> dict:
        """调整 API case 步骤顺序。steps 格式为 [{step_id, case_sort}]。"""
        for item in steps:
            ApiCaseDetailed.objects.filter(id=item["step_id"], case_id=case_id).update(case_sort=item["case_sort"])
        ApiCaseDetailedCRUD().callback(case_id)
        return ok({"case_id": case_id, "steps": steps}, "API case 步骤排序成功")

    @mcp.tool()
    def refresh_api_case_step_from_api_info(step_id: int) -> dict:
        """从接口定义同步 params/data/json/file 到步骤下所有场景。"""
        detail = ApiCaseDetailed.objects.select_related("api_info").get(id=step_id)
        api_info = detail.api_info
        count = ApiCaseDetailedParameter.objects.filter(case_detailed_id=step_id).update(
            params=api_info.params,
            data=api_info.data,
            json=api_info.json,
            file=api_info.file,
        )
        return ok({"step_id": step_id, "updated_scenarios": count}, "步骤参数同步成功")

    @mcp.tool()
    def list_api_case_scenarios(step_id: int) -> dict:
        """查询 API case 步骤下的场景参数。"""
        items = [model_to_dict(item) for item in ApiCaseDetailedParameter.objects.filter(case_detailed_id=step_id)]
        return ok({"items": items})

    @mcp.tool()
    def create_api_case_scenario(
        step_id: int,
        name: str,
        error_retry: int | None = None,
        retry_interval: int | None = None,
        headers: list[int] | None = None,
        params: str | dict | list | None = None,
        data: str | dict | list | None = None,
        json_body: str | dict | list | None = None,
        file: dict | list | None = None,
        front_sql: list | None = None,
        front_func: str | None = None,
        ass_jsonpath: list | None = None,
        ass_general: list | None = None,
        ass_json_all: dict | list | None = None,
        ass_text_all: str | None = None,
        ass_schema: dict | None = None,
        posterior_response: list | None = None,
        posterior_response_text: list | None = None,
        posterior_sql: list | None = None,
        posterior_sleep: int | None = None,
        posterior_func: str | None = None,
    ) -> dict:
        """给步骤创建一个场景参数。"""
        payload = {
            "case_detailed": step_id,
            "name": name,
            "error_retry": error_retry,
            "retry_interval": retry_interval,
            "headers": headers or [],
            "params": _json_string(params),
            "data": _json_string(data),
            "json": _json_string(json_body),
            "file": file,
            "front_sql": front_sql or [],
            "front_func": front_func,
            "ass_jsonpath": _normalize_ass_jsonpath(ass_jsonpath),
            "ass_general": ass_general or [],
            "ass_json_all": ass_json_all,
            "ass_text_all": ass_text_all,
            "ass_schema": ass_schema,
            "posterior_response": posterior_response or [],
            "posterior_response_text": posterior_response_text or [],
            "posterior_sql": posterior_sql or [],
            "posterior_sleep": posterior_sleep,
            "posterior_func": posterior_func,
        }
        payload = _normalize_scenario_payload(payload)
        data_obj = ApiCaseDetailedParameterCRUD.inside_post(payload)
        return ok({"scenario_id": data_obj["id"], **data_obj}, "场景参数创建成功")

    @mcp.tool()
    def update_api_case_scenario(scenario_id: int, fields: dict) -> dict:
        """更新场景参数。fields 使用 ApiCaseDetailedParameter 字段名。"""
        payload = {"id": scenario_id, **fields}
        payload = _normalize_scenario_payload(payload)
        data_obj = ApiCaseDetailedParameterCRUD.inside_put(scenario_id, payload)
        return ok({"scenario_id": data_obj["id"], **data_obj}, "场景参数更新成功")

    @mcp.tool()
    def copy_api_case_scenario(
        scenario_id: int,
        name: str | None = None,
        error_retry: int | None = None,
        retry_interval: int | None = None,
    ) -> dict:
        """复制场景参数。"""
        source = ApiCaseDetailedParameter.objects.get(id=scenario_id)
        parameter = model_to_dict(source)
        del parameter["id"]
        parameter["name"] = name or f"(副本){source.name}"
        parameter["error_retry"] = error_retry
        parameter["retry_interval"] = retry_interval
        parameter["status"] = 2
        parameter["result_data"] = None
        data_obj = ApiCaseDetailedParameterCRUD.inside_post(parameter)
        return ok({"scenario_id": data_obj["id"], **data_obj}, "场景参数复制成功")

    @mcp.tool()
    def generate_api_case_scenario_assertions(
        response_sample: dict | list | str,
        assertion_style: Literal["status_code", "jsonpath", "schema", "full"] = "jsonpath",
    ) -> dict:
        """根据响应样例生成场景断言草稿，不落库。"""
        sample: Any = response_sample
        if isinstance(response_sample, str):
            try:
                sample = jsonlib.loads(response_sample)
            except jsonlib.JSONDecodeError:
                sample = response_sample
        result: dict[str, Any] = {
            "ass_jsonpath": [],
            "ass_general": [],
            "ass_json_all": None,
            "ass_text_all": None,
            "ass_schema": None,
        }
        if assertion_style in ("jsonpath", "full") and isinstance(sample, (dict, list)):
            for path, value in _find_json_paths(sample):
                if isinstance(value, (str, int, float, bool)) or value is None:
                    result["ass_jsonpath"].append(
                        {
                            "actual": path,
                            "method": "p_is_equal_to",
                            "expect": "" if value is None else str(value),
                        }
                    )
        if assertion_style in ("schema", "full") and isinstance(sample, (dict, list)):
            builder = SchemaBuilder()
            builder.add_object(sample)
            result["ass_schema"] = builder.to_schema()
        if assertion_style == "full":
            if isinstance(sample, (dict, list)):
                result["ass_json_all"] = sample
            else:
                result["ass_text_all"] = str(sample)
        return ok(result)

    @mcp.tool()
    def generate_api_case_scenario_extractors(
        response_sample: dict | list | str,
        target_fields: list[str] | None = None,
    ) -> dict:
        """根据响应样例生成后置提取草稿，不落库。"""
        sample: Any = response_sample
        if isinstance(response_sample, str):
            try:
                sample = jsonlib.loads(response_sample)
            except jsonlib.JSONDecodeError:
                sample = response_sample
        posterior_response = []
        posterior_response_text = []
        targets = set(target_fields or ["token", "access_token", "id", "order_id", "user_id"])
        if isinstance(sample, (dict, list)):
            for path, value in _find_json_paths(sample, limit=50):
                key = path.split(".")[-1].replace("[0]", "")
                if key in targets:
                    posterior_response.append({"key": key, "value": path})
        else:
            for target in targets:
                posterior_response_text.append({"key": target, "value": f"{target}=([^&\\\\s]+)"})
        return ok(
            {
                "posterior_response": posterior_response,
                "posterior_response_text": posterior_response_text if not posterior_response else [],
            }
        )

    @mcp.tool()
    def auto_generate_api_case_scenario_schema(scenario_id: int) -> dict:
        """根据场景最近一次响应 JSON 生成 schema 断言并保存。"""
        parameter = ApiCaseDetailedParameter.objects.get(id=scenario_id)
        response = (parameter.result_data or {}).get("response", {}).get("json")
        if response is None:
            return fail("该场景没有最近一次响应 JSON，无法生成 schema", "RESPONSE_JSON_NOT_FOUND")
        builder = SchemaBuilder()
        builder.add_object(response)
        schema = builder.to_schema()
        parameter.ass_schema = schema
        parameter.save()
        return ok({"scenario_id": scenario_id, "ass_schema": schema}, "schema 断言生成成功")

    @mcp.tool()
    def get_api_case_detail_full(case_id: int, include_result_data: bool = True) -> dict:
        """查询完整 API case 树：case、steps、api_info、parameters。"""
        return ok(_case_tree(case_id, include_result_data))

    @mcp.tool()
    def create_complete_api_case(
        project_product_id: int,
        module_id: int,
        case_name: str,
        api: dict,
        scenarios: list[dict],
        case_people_id: int | None = None,
        headers: list[dict] | None = None,
        case_front_headers: list[int] | None = None,
        run_after_create: bool = False,
        test_env_id: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """一键创建公共请求头、接口定义、API case、步骤、场景，并可选立即执行。未提供 case_people_id 时应先查询负责人并询问用户选择。"""
        if case_people_id is None:
            return _case_owner_required()
        try:
            with transaction.atomic():
                header_ids: list[int] = []
                for header in headers or []:
                    created_header = ApiHeadersCRUD.inside_post(
                        {
                            "project_product": project_product_id,
                            "key": header["key"],
                            "value": header["value"],
                            "status": header.get("status", 0),
                        }
                    )
                    header_ids.append(created_header["id"])

                api_payload = {
                    "project_product": project_product_id,
                    "module": module_id,
                    "name": api["name"],
                    "url": api["url"],
                    "method": api["method"],
                    "headers": None,
                    "params": _json_string(api.get("params")),
                    "data": _json_string(api.get("data")),
                    "json": _json_string(api.get("json") or api.get("json_body")),
                    "file": api.get("file"),
                    "type": api.get("type", 1),
                }
                api_info = ApiInfoCRUD.inside_post(api_payload)
                api_case = ApiCaseCRUD.inside_post(
                    {
                        "project_product": project_product_id,
                        "module": module_id,
                        "name": case_name,
                        "case_people": case_people_id,
                        "level": api.get("level", 1),
                        "front_headers": case_front_headers or header_ids,
                        "front_custom": [],
                        "front_sql": [],
                        "posterior_sql": [],
                    }
                )
                step = _create_case_step(api_case["id"], api_info["id"], 0)
                default_parameter_id = step["default_parameter_id"]
                scenario_ids: list[int] = []
                if scenarios:
                    first = scenarios[0]
                    update_payload = {"name": first.get("name", api["name"])}
                    update_payload.update({k: v for k, v in first.items() if k != "name"})
                    update_payload = _normalize_scenario_payload(update_payload)
                    ApiCaseDetailedParameterCRUD.inside_put(default_parameter_id, update_payload)
                    scenario_ids.append(default_parameter_id)
                    for scenario in scenarios[1:]:
                        scenario_payload = {
                            "case_detailed": step["step_id"],
                            "name": scenario.get("name", api["name"]),
                            **{k: v for k, v in scenario.items() if k != "name"},
                        }
                        scenario_payload = _normalize_scenario_payload(scenario_payload)
                        created_scenario = ApiCaseDetailedParameterCRUD.inside_post(scenario_payload)
                        scenario_ids.append(created_scenario["id"])
                run_result = None
                if run_after_create:
                    user = current_user(user_id)
                    env_id = _selected_env(user.id, test_env_id)
                    run_result = TestCase(user_id=user.id, test_env=env_id, case_id=api_case["id"]).test_case().model_dump()
        except Exception as exc:
            return fail(str(exc), "CREATE_COMPLETE_API_CASE_FAILED")

        return ok(
            {
                "api_info_id": api_info["id"],
                "case_id": api_case["id"],
                "step_id": step["step_id"],
                "header_ids": header_ids,
                "scenario_ids": scenario_ids,
                "run_result": run_result,
            },
            "完整 API case 创建成功",
        )

    @mcp.tool()
    def run_api_case(
        case_id: int,
        test_env_id: int | None = None,
        case_sort: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """执行已保存 API case。不传 test_env_id 时使用当前用户 selected_environment。"""
        try:
            user = current_user(user_id)
            env_id = _selected_env(user.id, test_env_id)
            result = TestCase(user_id=user.id, test_env=env_id, case_id=case_id).test_case(case_sort).model_dump()
        except Exception as exc:
            return fail(str(exc), "API_CASE_RUN_FAILED")
        return ok(result, "API case 执行完成")

    @mcp.tool()
    def run_api_case_batch(
        case_ids: list[int],
        test_env_id: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """批量执行 API case。当前实现复用任务队列创建逻辑，返回任务创建结果。"""
        try:
            from src.auto_test.auto_system.service.tasks.add_tasks import AddTasks

            user = current_user(user_id)
            env_id = _selected_env(user.id, test_env_id)
            case_project_product = None
            case_project = None
            for case_id in case_ids:
                case = ApiCase.objects.select_related("project_product", "project_product__project").get(id=case_id)
                if case_project is None:
                    case_project_product = case.project_product.id
                    case_project = case.project_product.project.id
                elif case_project != case.project_product.project.id:
                    return fail("批量执行的 API case 必须属于同一个项目", "CASE_PROJECT_MISMATCH")
            add_tasks = AddTasks(
                project_product=case_project_product,
                test_env=env_id,
                is_notice=StatusEnum.FAIL.value,
                user_id=user.id,
            )
            for case_id in case_ids:
                add_tasks.add_test_suite_details(case_id, TestCaseTypeEnum.API)
        except Exception as exc:
            return fail(str(exc), "API_CASE_BATCH_RUN_FAILED")
        return ok({"case_ids": case_ids, "test_env_id": env_id}, "API case 批量执行任务创建成功")

    @mcp.tool()
    def get_api_case_run_result(case_id: int) -> dict:
        """查询 API case 最近一次执行结果，包括步骤和场景 result_data。"""
        return ok(_case_tree(case_id, include_result_data=True))

    @mcp.tool()
    def analyze_api_case_failure(case_id: int, step_id: int | None = None, scenario_id: int | None = None) -> dict:
        """基于最近一次执行结果分析 API case 失败原因。"""
        parameters = ApiCaseDetailedParameter.objects.filter(case_detailed__case_id=case_id)
        if step_id is not None:
            parameters = parameters.filter(case_detailed_id=step_id)
        if scenario_id is not None:
            parameters = parameters.filter(id=scenario_id)
        evidence = []
        suggestions = []
        failure_type = "unknown"
        for parameter in parameters:
            result_data = parameter.result_data or {}
            error_message = result_data.get("error_message") or ""
            response = result_data.get("response") or {}
            request = result_data.get("request") or {}
            status = parameter.status
            if status == 1 and not error_message:
                continue
            if error_message:
                evidence.append(f"scenario={parameter.name}, error={error_message}")
            if response.get("code"):
                evidence.append(f"scenario={parameter.name}, response.code={response.get('code')}")
            if response.get("code") in [401, 403]:
                failure_type = "auth_error"
                suggestions.append("检查 Authorization/Cookie 等认证请求头是否已创建并绑定到用例或场景")
            if request and not request.get("headers"):
                suggestions.append("当前请求没有请求头，必要时调用 create_api_header 并绑定 front_headers 或 scenario.headers")
        if not evidence:
            return ok(
                {
                    "summary": "未发现失败场景，最近一次结果可能为成功或尚未执行",
                    "failure_type": "none",
                    "evidence": [],
                    "suggestions": [],
                }
            )
        return ok(
            {
                "summary": evidence[0],
                "failure_type": failure_type,
                "evidence": evidence,
                "suggestions": list(dict.fromkeys(suggestions)),
            }
        )

    @mcp.tool()
    def get_api_method_schema() -> dict:
        """返回 API 请求方法枚举。"""
        return ok(MethodEnum.obj())

    @mcp.tool()
    def get_api_assertion_methods() -> dict:
        """查询 API 断言方法选项，来源同前端 system/cache/data/key/value?key=ass_select_value。"""
        groups = _api_assertion_method_groups()
        content_methods = _content_assertion_methods(groups)
        return ok(
            {
                "source": "cache_data.ass_select_value",
                "groups": groups,
                "jsonpath_methods": content_methods,
                "flat_methods": _flatten_assertion_methods(groups),
                "recommended": {
                    "jsonpath_equal": "p_is_equal_to",
                    "jsonpath_contains": "p_contains",
                    "jsonpath_not_null": "p_is_not_none",
                    "general_equal": "p_is_equal_to",
                },
                "notes": [
                    "jsonpath断言的 method 必须使用 jsonpath_methods 中叶子节点的 value，例如 p_is_equal_to，不能使用 eq。",
                    "通用断言保存的是前端级联选项对象，建议先用 get_api_assertion_schema 查看结构。",
                ],
            }
        )

    @mcp.tool()
    def get_api_assertion_schema() -> dict:
        """返回 API 场景断言字段格式。"""
        try:
            general_equal = _general_assertion_template("p_is_equal_to", "${{实际值}}", "预期值")
        except Exception:
            general_equal = {"method": "内容断言 / 值等于什么 / 等于expect", "value": {}}
        return ok(
            {
                "assertion_types": {
                    "ass_json_all": "JSON一致断言。保存期望 JSON 对象或 JSON 字符串，后端用 p_in_dict 判断响应 JSON 是否匹配期望 JSON。",
                    "ass_jsonpath": "JSONPath断言。actual 是 JSONPath，method 必须是 get_api_assertion_methods.jsonpath_methods 中的 value，expect 是预期值。",
                    "ass_text_all": "文本一致断言。保存完整预期响应文本，后端用 response.text.strip() == expect.strip()。",
                    "ass_general": "通用断言。外层 value 保存前端级联选中的完整对象；parameter[].v 面向 textarea 保存，dict/list 应保存为 JSON 字符串，执行 SQL 断言时会自动反序列化。",
                    "ass_schema": "结构化断言。保存 JSON Schema 对象；也可调用 auto_generate_api_case_scenario_schema 自动生成。",
                },
                "ass_jsonpath": [{"actual": "$.code", "method": "p_is_equal_to", "expect": "0"}],
                "ass_general": [general_equal],
                "ass_json_all": {"code": 0},
                "ass_text_all": "完整响应文本",
                "ass_schema": {"type": "object", "properties": {"code": {"type": "integer"}}},
            }
        )

    @mcp.tool()
    def get_api_extractor_schema() -> dict:
        """返回 API 场景后置提取字段格式。"""
        return ok(
            {
                "posterior_response": [{"key": "token", "value": "$.data.token"}],
                "posterior_response_text": [{"key": "order_id", "value": "orderId=(\\d+)"}],
            }
        )

    @mcp.tool()
    def get_api_case_schema() -> dict:
        """返回 API case、步骤和场景参数的核心字段说明。"""
        return ok(
            {
                "api_info": ["project_product", "module", "name", "url", "method", "params", "data", "json", "file"],
                "api_case": ["project_product", "module", "name", "case_people", "level", "front_headers", "front_custom", "front_sql", "posterior_sql"],
                "api_case_detailed": ["case", "api_info", "case_sort"],
                "api_case_detailed_parameter": [
                    "case_detailed",
                    "name",
                    "headers",
                    "params",
                    "data",
                    "json",
                    "file",
                    "front_sql",
                    "front_func",
                    "ass_jsonpath",
                    "ass_general",
                    "ass_json_all",
                    "ass_text_all",
                    "ass_schema",
                    "posterior_response",
                    "posterior_response_text",
                    "posterior_sql",
                    "posterior_sleep",
                    "posterior_func",
                ],
            }
        )

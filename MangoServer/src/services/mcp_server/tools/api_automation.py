from __future__ import annotations

import json as jsonlib
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

from curlparser import parse
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from genson import SchemaBuilder

from src.apps.auto_api.models import ApiCase, ApiCaseDetailed, ApiCaseDetailedParameter, ApiHeaders, ApiInfo, ApiPublic
from src.apps.auto_system.models import CacheData
from src.apps.auto_api.service.test_case.test_api_info import TestApiInfo
from src.apps.auto_api.service.test_case.test_case import TestCase
from src.apps.auto_api.views.api_case import ApiCaseCRUD, ApiCaseSerializersC
from src.apps.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD
from src.apps.auto_api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD
from src.apps.auto_api.views.api_headers import ApiHeadersCRUD
from src.apps.auto_api.views.api_info import ApiInfoCRUD
from src.apps.auto_api.views.api_pulic import ApiPublicCRUD
from src.apps.auto_user.models import User
from src.common.enums.api_enum import ApiPublicTypeEnum, MethodEnum
from src.common.enums.system_enum import CacheDataKey2Enum
from src.common.enums.tools_enum import (
    ApiCaseScenarioLayerEnum,
    ApiCaseScenarioTagEnum,
    ApiCaseScenarioTypeEnum,
    CaseLevelEnum,
    StatusEnum,
    TestCaseTypeEnum,
)
from src.services.mcp_server.common import (
    create_dangerous_action_preview,
    current_user,
    fail,
    ok,
    validate_dangerous_action_confirmation,
)


FILE_UPLOAD_USAGE = {
    "description": "API 接口定义和 API case 场景参数中的 file 字段用于描述 multipart/form-data 文件参数。",
    "required_format": [{"请求文件字段名": "${{get_file(已上传文件名)}}" }],
    "strict_rule": "只要 api_info.file 或 api_case 场景 file 非空，每个文件字段值都必须使用 ${{get_file(文件名)}} 表达式；不能直接传本地路径、URL、裸文件名或二进制内容。",
    "workflow": [
        "先调用 system_file 分组的 upload_system_file 上传真实文件，记录返回的 file.name 或上传时传入的 name。",
        "在 api_info.file 或 api_case_detailed_parameter.file 中使用 ${{get_file(文件名)}} 引用已上传文件。",
        "get_file 是系统自定义随机/变量方法，执行时会按文件名查找上传文件并转换成实际请求文件。",
    ],
    "example": [{"file": "${{get_file(数据订阅新增模板.xlsx)}}"}],
    "notes": [
        "示例中的 file 是请求参数名；如果接口字段名叫 upload_file，则写成 [{'upload_file': '${{get_file(数据订阅新增模板.xlsx)}}'}]。",
        "括号内必须是实际上传文件名，建议先用 list_system_files 查询确认。",
        "不要把本地文件路径直接写入 file 字段；远程 MCP 服务通常无法读取调用者本机路径。",
    ],
}


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


def _validate_scenario_tags(tags: list[int] | None) -> str | None:
    layer_tags = {7, 8, 9}
    for tag in tags or []:
        try:
            if int(tag) in layer_tags:
                return "API/Integration/E2E 已迁移到 scenario_layer 字段，请不要再把 7/8/9 写入 scenario_tags。"
        except (TypeError, ValueError):
            continue
    return None


def _validate_file_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    return value.startswith("${{get_file(") and value.endswith(")}}") and len(value) > len("${{get_file()}}")


def _validate_file_payload(file_payload: Any) -> str | None:
    if file_payload is None:
        return None
    rows = file_payload if isinstance(file_payload, list) else [file_payload]
    if not rows:
        return None
    for row in rows:
        if not isinstance(row, dict) or not row:
            return "file 必须是对象或对象数组，例如 [{'file': '${{get_file(数据订阅新增模板.xlsx)}}'}]。"
        for field_name, field_value in row.items():
            if not field_name:
                return "file 中的请求文件字段名不能为空。"
            if not _validate_file_value(field_value):
                return "file 字段值必须使用 ${{get_file(已上传文件名)}} 格式，不能直接传本地路径、URL、裸文件名或二进制内容。"
    return None


def _validate_api_info_url_path(url: str | None) -> str | None:
    if url is None:
        return None
    if not isinstance(url, str) or not url.strip():
        return "ApiInfo.url 必须是非空路径字符串，例如 /clm/api/category/update。"
    value = url.strip()
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith("//"):
        return "ApiInfo.url 只允许保存路径，不允许包含协议、域名或端口；请传 /path，例如 /clm/api/category/update。"
    if not value.startswith("/"):
        return "ApiInfo.url 必须以 / 开头，只保存请求路径，例如 /clm/api/category/update。"
    if parsed.query or parsed.fragment:
        return "ApiInfo.url 只保存路径，不保存 query 或 fragment；query 参数请放到 params 字段。"
    return None


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
        if _jsonpath_method_uses_expect(method):
            normalized_expect = "" if expect is None else str(expect)
        else:
            normalized_expect = None
        normalized.append(
            {
                "actual": actual,
                "method": method,
                "expect": normalized_expect,
            }
        )
    return normalized


def _jsonpath_method_uses_expect(method_value: str | None) -> bool:
    if not method_value:
        return True
    method = _find_assertion_method(method_value)
    if method is None:
        return True
    parameters = method.get("parameter") or []
    return any(parameter.get("f") == "expect" for parameter in parameters)


def _find_assertion_method(method_value: str) -> dict | None:
    methods = _flatten_assertion_methods(_api_assertion_method_groups())
    return next((item for item in methods if item["value"] == method_value), None)


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
        "创建 API case 需要指定负责人 case_people_id，或通过 MCP APIKey/JWT 识别当前用户作为默认负责人。",
        "CASE_OWNER_REQUIRED",
        {
            "required_field": "case_people_id",
            "next_actions": [
                "在 MCP 客户端 Authorization 中配置当前用户 APIKey",
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


def _api_case_delete_impact(case_id: int) -> dict:
    from src.apps.auto_data_factory.models import DataFactoryCaseConfig
    from src.apps.auto_system.models import TasksDetails, TestSuiteDetails
    from src.common.enums.data_factory_enum import DataFactoryCaseSourceTypeEnum

    case = ApiCase.objects.select_related("project_product", "module", "case_people").get(id=case_id)
    step_ids = list(ApiCaseDetailed.objects.filter(case_id=case_id).values_list("id", flat=True))
    scenario_ids = list(
        ApiCaseDetailedParameter.objects.filter(case_detailed_id__in=step_ids).values_list("id", flat=True)
    )
    case_factory_count = DataFactoryCaseConfig.objects.filter(
        source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
        source_id=case_id,
    ).count()
    scenario_factory_count = DataFactoryCaseConfig.objects.filter(
        source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
        source_id__in=scenario_ids,
    ).count()
    task_detail_count = TasksDetails.objects.filter(api_case_id=case_id).count()
    report_detail_count = TestSuiteDetails.objects.filter(
        type=TestCaseTypeEnum.API.value,
        case_id=case_id,
    ).count()
    return {
        "case": {
            "id": case.id,
            "name": case.name,
            "project_product_id": case.project_product_id,
            "project_product_name": case.project_product.name if case.project_product else None,
            "module_id": case.module_id,
            "module_name": case.module.name if case.module else None,
            "case_people_id": case.case_people_id,
            "case_people_name": case.case_people.name if case.case_people else None,
            "status": case.status,
        },
        "will_delete": {
            "api_case": 1,
            "api_case_steps": len(step_ids),
            "api_case_scenarios": len(scenario_ids),
            "case_data_factory_configs": case_factory_count,
            "scenario_data_factory_configs": scenario_factory_count,
        },
        "references": {
            "task_detail_count": task_detail_count,
            "historical_report_detail_count": report_detail_count,
        },
        "blocking_risks": [
            "如果 task_detail_count > 0，模型会阻止删除，请先解除定时任务详情绑定。",
            "历史测试报告明细按 case_id 保存，不会随 case 删除自动删除。",
        ],
    }


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


def _find_same_api_header(project_product_id: int, key: str) -> ApiHeaders | None:
    return (
        ApiHeaders.objects.select_related("project_product")
        .filter(project_product_id=project_product_id, key__iexact=key)
        .order_by("-status", "-id")
        .first()
    )


def _api_header_summary(header: ApiHeaders) -> dict:
    project_product = header.project_product
    return {
        "id": header.id,
        "project_product_id": header.project_product_id,
        "project_product_name": project_product.name if project_product else None,
        "api_client_type": getattr(project_product, "api_client_type", None) if project_product else None,
        "key": header.key,
        "value": header.value,
        "status": header.status,
    }


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
    def preview_create_api_header_impact(project_product_id: int, key: str, value: str, status: int = 0) -> dict:
        """预览创建项目产品公共请求头的影响。

        公共请求头会被 API case/front_headers 或场景 headers 复用。只有接口执行必需的认证、租户、
        CSRF、业务网关等请求头才允许创建；accept-language、user-agent、sec-*、traceparent 等
        非必须浏览器噪声请求头不要添加。预览后必须由用户手动确认，才能调用 create_api_header。
        创建前会按同一项目产品和请求头 key 做查重；已存在时应复用已有 header_id，不再新增。
        """
        duplicate = _find_same_api_header(project_product_id, key)
        if duplicate and duplicate.value == value:
            return ok(
                {
                    "action": "reuse_existing_header",
                    "header": _api_header_summary(duplicate),
                    "next_step": "该项目产品下已存在相同请求头，请直接复用这个 header_id，不要重复创建。",
                },
                "公共请求头已存在，无需新增",
            )
        if duplicate:
            return fail(
                "该项目产品下已存在相同 key 的公共请求头，请优先复用已有 header_id；如确需变更，请人工确认后使用 update_api_header。",
                "API_HEADER_ALREADY_EXISTS",
                {
                    "existing_header": _api_header_summary(duplicate),
                    "requested": {
                        "project_product_id": project_product_id,
                        "key": key,
                        "value_preview": value[:80],
                        "status": status,
                    },
                },
            )
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
                    "duplicate_header": None,
                    "manual_check_required": [
                        "请确认该请求头是接口执行必需项。",
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
        非必须请求头不允许创建；不要把浏览器噪声请求头写入公共请求头池。
        """
        error = validate_dangerous_action_confirmation(
            "create_api_header",
            f"{project_product_id}:{key}",
            preview_token,
            confirm_text,
        )
        if error:
            return error
        duplicate = _find_same_api_header(project_product_id, key)
        if duplicate and duplicate.value == value:
            return ok(
                {
                    "header_id": duplicate.id,
                    **_api_header_summary(duplicate),
                    "action": "reuse_existing_header",
                },
                "公共请求头已存在，已返回已有 header_id，未重复创建",
            )
        if duplicate:
            return fail(
                "创建前发现该项目产品下已存在相同 key 的公共请求头，已阻止重复创建。",
                "API_HEADER_ALREADY_EXISTS",
                {
                    "existing_header": _api_header_summary(duplicate),
                    "requested_value_preview": value[:80],
                    "next_step": "请复用 existing_header.id；如确需修改公共请求头，请使用 update_api_header。",
                },
            )
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
        test_env_id: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict:
        """查询 API 全局变量。type: 0=自定义, 1=SQL。"""
        queryset = ApiPublic.objects.select_related("project_product", "datasource_alias").filter(project_product_id=project_product_id)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        if type is not None:
            if type not in ApiPublicTypeEnum.get_key_list():
                return fail("API 全局变量类型只支持 0=自定义、1=SQL。", "API_PUBLIC_TYPE_INVALID")
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
                "type_title": ApiPublicTypeEnum.get_value(item.type),
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
    def create_api_public_variable(
        project_product_id: int,
        test_env_id: int,
        type: int,
        name: str,
        key: str,
        value: str,
        datasource_alias_id: int | None = None,
        status: int = 0,
    ) -> dict:
        """创建 API 全局变量。type: 0=自定义, 1=SQL；SQL 类型必须先调用 list_data_factory_datasource_aliases 查询 datasource_alias_id。"""
        if type not in ApiPublicTypeEnum.get_key_list():
            return fail("API 全局变量类型只支持 0=自定义、1=SQL。", "API_PUBLIC_TYPE_INVALID")
        if type == ApiPublicTypeEnum.SQL.value and not datasource_alias_id:
            return fail("SQL API 全局变量必须传 datasource_alias_id。", "API_PUBLIC_DATASOURCE_ALIAS_REQUIRED")
        data = ApiPublicCRUD.inside_post(
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
        return ok({"public_variable_id": data["id"], **data}, "API 全局变量创建成功")

    @mcp.tool()
    def update_api_public_variable(
        public_variable_id: int,
        type: int | None = None,
        test_env_id: int | None = None,
        name: str | None = None,
        key: str | None = None,
        value: str | None = None,
        datasource_alias_id: int | None = None,
        status: int | None = None,
    ) -> dict:
        """更新 API 全局变量。SQL 类型需要 datasource_alias_id；自定义类型可传空清除。"""
        payload: dict[str, Any] = {"id": public_variable_id}
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
        """创建 API 接口定义。url 只能传路径，不能传域名；params/data/json_body 请传 JSON 字符串或对象。ApiInfo.headers 默认保持 null。

        文件上传接口的 file 字段必须先调用 upload_system_file 上传真实文件，再使用
        [{"file": "${{get_file(数据订阅新增模板.xlsx)}}"}] 这种格式引用。
        其中 file 是请求文件字段名；如果字段名是 upload_file，则写成
        [{"upload_file": "${{get_file(数据订阅新增模板.xlsx)}}"}]。
        不能直接传本地路径、URL、裸文件名或二进制内容；详细格式见 get_api_case_schema.file_upload_usage。
        """
        if method not in MethodEnum.get_key_list():
            return fail("请求方法不存在", "METHOD_NOT_FOUND", {"method": method})
        url_error = _validate_api_info_url_path(url)
        if url_error:
            return fail(url_error, "INVALID_API_INFO_URL", {"url": url})
        file_error = _validate_file_payload(file)
        if file_error:
            return fail(file_error, "INVALID_FILE_FORMAT")
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
        url_error = _validate_api_info_url_path(path)
        if url_error:
            return fail(url_error, "INVALID_API_INFO_URL", {"parsed_url": parsed.url, "path": path})
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
        module_id: int | None = None,
        url: str | None = None,
        method: int | None = None,
        params: str | dict | list | None = None,
        data: str | dict | list | None = None,
        json_body: str | dict | list | None = None,
        file: dict | list | None = None,
    ) -> dict:
        """更新 API 接口定义。module_id 可修改接口所属模块；url 只能传路径，不能传域名。

        文件上传接口的 file 字段必须先调用 upload_system_file 上传真实文件，再使用
        [{"file": "${{get_file(数据订阅新增模板.xlsx)}}"}] 这种格式引用；不能直接传本地路径、URL、裸文件名或二进制内容。
        详细格式见 get_api_case_schema.file_upload_usage。
        """
        url_error = _validate_api_info_url_path(url)
        if url_error:
            return fail(url_error, "INVALID_API_INFO_URL", {"url": url})
        file_error = _validate_file_payload(file)
        if file_error:
            return fail(file_error, "INVALID_FILE_FORMAT")
        payload: dict[str, Any] = {"id": api_info_id}
        for key, value in {
            "name": name,
            "module": module_id,
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
        scenario_layer: int | None = None,
        scenario_type: int | None = None,
        scenario_tags: list[int] | None = None,
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
        if scenario_layer is not None:
            queryset = queryset.filter(scenario_layer=scenario_layer)
        if scenario_type is not None:
            queryset = queryset.filter(scenario_type=scenario_type)
        if scenario_tags:
            tag_query = Q()
            for tag in scenario_tags:
                tag_query |= Q(scenario_tags__contains=[tag])
            queryset = queryset.filter(tag_query)
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
                "scenario_layer": item.scenario_layer,
                "scenario_type": item.scenario_type,
                "scenario_tags": item.scenario_tags,
                "scenario_description": item.scenario_description,
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
        scenario_layer: int = 0,
        scenario_type: int = 0,
        scenario_tags: list[int] | None = None,
        scenario_description: str | None = None,
        front_custom: list | None = None,
        front_sql: list | None = None,
        front_headers: list[int] | None = None,
        posterior_sql: list | None = None,
    ) -> dict:
        """创建 API case 主体。

        复杂字段格式见 get_api_case_schema.api_case_fields。front_headers 只传 ApiHeaders.id 数组，
        表示用例级默认请求头；如果某个场景参数 headers 非空，执行时会完全覆盖 front_headers，不会合并。
        scenario_layer 表示测试分层：0=接口/组件层、1=Integration集成、2=E2E端到端。
        接口/组件层用于单接口、组件能力、契约、边界、异常校验，Integration用于跨模块/跨服务/数据库/消息/第三方协作验证，
        E2E用于核心用户路径和完整业务闭环验证。scenario_tags 只放冒烟、回归、主流程等辅助标签。
        如果用例不涉及 SQL 前后置、SQL 断言或数据工厂造数/清理，可默认把 6=线上巡检 加入 scenario_tags。
        未提供 case_people_id 时默认使用当前 MCP APIKey/JWT 对应用户作为负责人。
        """
        tag_error = _validate_scenario_tags(scenario_tags)
        if tag_error:
            return fail(tag_error, "INVALID_SCENARIO_TAGS")
        if case_people_id is None:
            case_people_id = current_user().id
        data_obj = ApiCaseCRUD.inside_post(
            {
                "project_product": project_product_id,
                "module": module_id,
                "name": name,
                "case_people": case_people_id,
                "level": level,
                "scenario_layer": scenario_layer,
                "scenario_type": scenario_type,
                "scenario_tags": scenario_tags or [],
                "scenario_description": scenario_description,
                "front_custom": front_custom or [],
                "front_sql": front_sql or [],
                "front_headers": front_headers or [],
                "posterior_sql": posterior_sql or [],
            }
        )
        return ok({"case_id": data_obj["id"], "current_user_id": current_user().id, **data_obj}, "API case 创建成功")

    @mcp.tool()
    def update_api_case(
        case_id: int,
        name: str | None = None,
        module_id: int | None = None,
        case_people_id: int | None = None,
        level: int | None = None,
        scenario_layer: int | None = None,
        scenario_type: int | None = None,
        scenario_tags: list[int] | None = None,
        scenario_description: str | None = None,
        front_custom: list | None = None,
        front_sql: list | None = None,
        front_headers: list[int] | None = None,
        posterior_sql: list | None = None,
    ) -> dict:
        """更新 API case 主体配置。module_id 可修改所属模块，case_people_id 可修改负责人；复杂字段格式见 get_api_case_schema.api_case_fields。"""
        tag_error = _validate_scenario_tags(scenario_tags)
        if tag_error:
            return fail(tag_error, "INVALID_SCENARIO_TAGS")
        payload: dict[str, Any] = {"id": case_id}
        for key, value in {
            "name": name,
            "module": module_id,
            "case_people": case_people_id,
            "level": level,
            "scenario_layer": scenario_layer,
            "scenario_type": scenario_type,
            "scenario_tags": scenario_tags,
            "scenario_description": scenario_description,
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
    def preview_delete_api_case_impact(case_id: int) -> dict:
        """预览删除 API case 的影响。删除属于危险操作，必须先预览，再由用户二次确认。"""
        return ok(
            create_dangerous_action_preview(
                "delete_api_case",
                case_id,
                f"DELETE_API_CASE:{case_id}",
                _api_case_delete_impact(case_id),
            ),
            "已生成 API case 删除影响预览",
        )

    @mcp.tool()
    def delete_api_case(
        case_id: int,
        preview_token: str | None = None,
        confirm_text: str | None = None,
    ) -> dict:
        """确认后删除 API case。

        必须先调用 preview_delete_api_case_impact。确认后会删除该 case 下的步骤、场景参数，
        并通过模型 delete 逻辑清理 API case 与场景级数据工厂绑定；如果仍有关联定时任务详情，删除会被阻止。
        """
        error = validate_dangerous_action_confirmation("delete_api_case", case_id, preview_token, confirm_text)
        if error:
            return error
        try:
            with transaction.atomic():
                before = _api_case_delete_impact(case_id)
                for step in ApiCaseDetailed.objects.filter(case_id=case_id).order_by("id"):
                    step.delete()
                ApiCaseCRUD.inside_delete(case_id)
        except Exception as exc:
            return fail(str(exc), "DELETE_API_CASE_FAILED")
        return ok({"case_id": case_id, "deleted": before.get("will_delete", {})}, "API case 删除成功")

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
        """给步骤创建一个场景参数。

        复杂字段格式见 get_api_case_schema.api_case_scenario_fields。
        headers 只传 ApiHeaders.id 数组；只要 headers 非空，就会完全覆盖 API case 的 front_headers，不会合并。
        ass_jsonpath 中 actual 是 JSONPath；method 使用 get_api_assertion_methods 返回的叶子 value。
        如果 method 的参数只有 actual、没有 expect，例如 p_is_none/p_is_true/p_is_false，expect 传 null。
        文件上传参数 file 必须使用 [{"file": "${{get_file(数据订阅新增模板.xlsx)}}"}] 格式引用已上传文件；
        file 是请求文件字段名，不能直接传本地路径、URL、裸文件名或二进制内容。
        """
        file_error = _validate_file_payload(file)
        if file_error:
            return fail(file_error, "INVALID_FILE_FORMAT")
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
        """更新场景参数。fields 使用 ApiCaseDetailedParameter 字段名。

        字段格式见 get_api_case_schema.api_case_scenario_fields。fields.headers 非空时会覆盖 API case 的 front_headers。
        fields.ass_jsonpath 的规则同 create_api_case_scenario：单参数断言方法 expect 传 null。
        fields.file 如需上传文件，必须使用 [{"file": "${{get_file(数据订阅新增模板.xlsx)}}"}] 格式引用已上传文件；
        file 是请求文件字段名，不能直接传本地路径、URL、裸文件名或二进制内容。
        """
        if "file" in fields:
            file_error = _validate_file_payload(fields.get("file"))
            if file_error:
                return fail(file_error, "INVALID_FILE_FORMAT")
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
                    if value is None:
                        method = "p_is_none"
                        expect = None
                    elif value is True:
                        method = "p_is_true"
                        expect = None
                    elif value is False:
                        method = "p_is_false"
                        expect = None
                    else:
                        method = "p_is_equal_to"
                        expect = str(value)
                    result["ass_jsonpath"].append(
                        {
                            "actual": path,
                            "method": method,
                            "expect": expect,
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
        scenario_layer: int = 0,
        scenario_type: int = 0,
        scenario_tags: list[int] | None = None,
        scenario_description: str | None = None,
        headers: list[dict] | None = None,
        case_front_headers: list[int] | None = None,
        run_after_create: bool = False,
        test_env_id: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """一键创建接口定义、API case、步骤、场景，并可选立即执行。

        未提供 case_people_id 时默认使用当前 MCP APIKey/JWT 对应用户作为负责人。
        出于公共请求头安全控制，本工具不再直接创建 ApiHeaders。需要请求头时，请先对每个必需 header
        调用 preview_create_api_header_impact 并由用户手动确认，再调用 create_api_header 创建，最后把返回 id
        通过 case_front_headers 或 scenarios[].headers 传入。
        如果 scenarios[].headers 非空，执行该场景时会覆盖 case_front_headers，不会合并。
        api.file 和 scenarios[].file 如需上传文件，必须先调用 upload_system_file 上传真实文件，再使用
        [{"file": "${{get_file(数据订阅新增模板.xlsx)}}"}] 这种格式引用；不能直接传本地路径、URL、裸文件名或二进制内容。
        详细格式见 get_api_case_schema.file_upload_usage。
        scenario_layer 表示测试分层：0=接口/组件层、1=Integration集成、2=E2E端到端；scenario_tags 只放辅助标签。
        如果完整用例不涉及 SQL 前后置、SQL 断言或数据工厂造数/清理，可默认把 6=线上巡检 加入 scenario_tags。
        """
        tag_error = _validate_scenario_tags(scenario_tags)
        if tag_error:
            return fail(tag_error, "INVALID_SCENARIO_TAGS")
        if headers:
            return fail(
                "create_complete_api_case 不允许直接创建公共请求头。请先逐个调用 preview_create_api_header_impact，"
                "由用户确认是接口执行必需请求头后，再调用 create_api_header 创建，并通过 case_front_headers 或 scenarios[].headers 绑定。",
                "API_HEADER_CONFIRM_REQUIRED",
                {
                    "headers_count": len(headers),
                    "required_flow": [
                        "list_api_headers 查询是否已有可复用请求头",
                        "preview_create_api_header_impact 预览新增请求头影响",
                        "用户确认该请求头为接口执行必需项",
                        "create_api_header 传回 preview_token/confirm_text 创建",
                        "create_complete_api_case 使用 case_front_headers 绑定已创建请求头 ID",
                    ],
                },
            )
        api_url_error = _validate_api_info_url_path(api.get("url"))
        if api_url_error:
            return fail(api_url_error, "INVALID_API_INFO_URL", {"url": api.get("url")})
        file_error = _validate_file_payload(api.get("file"))
        if file_error:
            return fail(f"api.file 格式错误：{file_error}", "INVALID_FILE_FORMAT")
        for index, scenario in enumerate(scenarios or [], start=1):
            if "file" in scenario:
                file_error = _validate_file_payload(scenario.get("file"))
                if file_error:
                    return fail(f"scenarios[{index}].file 格式错误：{file_error}", "INVALID_FILE_FORMAT")
        if case_people_id is None:
            case_people_id = current_user(user_id).id
        try:
            caller_user = current_user(user_id)
            with transaction.atomic():
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
                        "scenario_layer": scenario_layer,
                        "scenario_type": scenario_type,
                        "scenario_tags": scenario_tags or [],
                        "scenario_description": scenario_description,
                        "front_headers": case_front_headers or [],
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
                return ok(
                    {
                        "current_user_id": caller_user.id,
                        "case_people_id": case_people_id,
                        "api_info_id": api_info["id"],
                        "case_id": api_case["id"],
                        "step_id": step["step_id"],
                        "header_ids": case_front_headers or [],
                        "scenario_ids": scenario_ids,
                        "run_result": run_result,
                    },
                    "完整 API case 创建成功",
                )
        except Exception as exc:
            return fail(str(exc), "CREATE_COMPLETE_API_CASE_FAILED")

    @mcp.tool()
    def run_api_case(
        case_id: int,
        test_env_id: int | None = None,
        case_sort: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """异步执行已保存 API case。不传 test_env_id 时使用当前用户 selected_environment。"""
        try:
            from src.apps.auto_system.service.tasks.add_tasks import AddTasks

            if case_sort is not None:
                return fail("异步执行暂不支持 case_sort；请执行完整 API case。", "ASYNC_CASE_SORT_UNSUPPORTED")
            user = current_user(user_id)
            env_id = _selected_env(user.id, test_env_id)
            case = ApiCase.objects.select_related("project_product").get(id=case_id)
            add_tasks = AddTasks(
                project_product=case.project_product_id,
                test_env=env_id,
                is_notice=StatusEnum.FAIL.value,
                user_id=user.id,
            )
            add_tasks.add_test_suite_details(case_id, TestCaseTypeEnum.API)
        except Exception as exc:
            return fail(str(exc), "API_CASE_RUN_FAILED")
        return ok(
            {
                "case_id": case_id,
                "test_env_id": env_id,
                "test_suite_id": add_tasks.test_suite_id,
                "result_query_tool": "get_test_report_detail",
            },
            "API case 异步执行任务创建成功",
        )

    @mcp.tool()
    def run_api_case_batch(
        case_ids: list[int],
        test_env_id: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """批量执行 API case。当前实现复用任务队列创建逻辑，返回任务创建结果。"""
        try:
            from src.apps.auto_system.service.tasks.add_tasks import AddTasks

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
        return ok(
            {
                "case_ids": case_ids,
                "test_env_id": env_id,
                "test_suite_id": add_tasks.test_suite_id,
                "result_query_tool": "get_test_report_detail",
            },
            "API case 批量异步执行任务创建成功",
        )

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
                    "jsonpath_null": "p_is_none",
                    "jsonpath_not_null": "p_is_not_none",
                    "jsonpath_true": "p_is_true",
                    "jsonpath_false": "p_is_false",
                    "general_equal": "p_is_equal_to",
                },
                "notes": [
                    "jsonpath断言的 method 必须使用 jsonpath_methods 中叶子节点的 value，例如 p_is_equal_to，不能使用 eq。",
                    "判断 ass_jsonpath.expect 如何传值必须看所选 method 在 jsonpath_methods/flat_methods 中的 parameter 定义。",
                    "如果 method.parameter 里包含 {f:\"expect\"}，expect 传预期值；如果 parameter 只有 {f:\"actual\"} 或不包含 expect，expect 必须传 null。",
                    "如果响应字段值是 JSON null，不要使用 p_is_equal_to + expect:null，应使用 p_is_none + expect:null。",
                    "如果响应字段值是空字符串，使用 p_is_equal_to + expect:\"\" 或 p_is_empty，不能按 null 处理。",
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
                    "ass_json_all": "JSON一致断言。保存基础、固定的期望 JSON 片段，后端用 p_in_dict 到响应 JSON 中做局部包含匹配，不是全量相等断言；已在这里断言的字段无需再重复写入 ass_jsonpath。",
                    "ass_jsonpath": "JSONPath断言。actual 是 JSONPath，method 必须是 get_api_assertion_methods.jsonpath_methods 中的 value；expect 是否需要传值取决于该 method 的 parameter，包含 f=expect 时传预期值，不包含 f=expect 时传 null。",
                    "ass_text_all": "文本一致断言。保存完整预期响应文本，后端用 response.text.strip() == expect.strip()。",
                    "ass_general": "通用断言。外层 value 保存前端级联选中的完整对象；parameter[].v 面向 textarea 保存，dict/list 应保存为 JSON 字符串，执行 SQL 断言时会自动反序列化。",
                    "ass_schema": "结构化断言。保存 JSON Schema 对象；也可调用 auto_generate_api_case_scenario_schema 自动生成。",
                },
                "ass_jsonpath": [
                    {"actual": "$.code", "method": "p_is_equal_to", "expect": "0"},
                    {"actual": "$.timestamp", "method": "p_is_none", "expect": None},
                    {"actual": "$.success", "method": "p_is_true", "expect": None},
                ],
                "ass_general": [general_equal],
                "ass_json_all": {"code": 0, "data": {"status": 1}},
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
        key_value_schema = {
            "type": "list[object]",
            "format": [{"key": "缓存key或名称", "value": "值、SQL、JSONPath、正则或表达式"}],
            "variable_support": "value 通常支持 ${{变量}}、${{随机方法()}}、${{数据工厂.字段}} 等表达式，执行前由测试数据引擎替换。",
        }
        sql_key_value_schema = {
            "type": "list[object]",
            "format": [{"key": "缓存key或名称", "value": "SQL语句", "datasource_alias": "逻辑数据源ID，可为空"}],
            "datasource_alias": {
                "field": "datasource_alias",
                "type": "int | null",
                "source": "数据工厂逻辑数据源 DataFactoryDatasourceAlias.id",
                "lookup_tool": "list_data_factory_datasource_aliases(project_product_id=当前产品ID)",
                "rule": "多数据库测试环境下，API case/场景的 SQL 前置或后置必须传 datasource_alias；单库老数据可为空并由后端兜底。",
            },
            "variable_support": "value 支持 ${{变量}}、${{随机方法()}}、${{数据工厂.字段}} 等表达式，执行前由测试数据引擎替换。",
        }
        file_example = [{"file": "${{get_file(数据订阅新增模板.xlsx)}}"}]
        return ok(
            {
                "api_info": ["project_product", "module", "name", "url", "method", "params", "data", "json", "file"],
                "api_public": [
                    "project_product",
                    "test_env",
                    "type",
                    "name",
                    "key",
                    "value",
                    "datasource_alias_id",
                    "status",
                ],
                "api_public_sql": {
                    "fields": ["project_product_id", "test_env_id", "type", "name", "key", "value", "datasource_alias_id", "status"],
                    "format": {
                        "type": "0=自定义公共变量，1=SQL 公共变量。",
                        "value": "SQL 类型时填写 SQL 语句，自定义类型时填写普通值。",
                        "datasource_alias_id": "SQL 类型必填，传逻辑数据源 DataFactoryDatasourceAlias.id；自定义类型可不传。",
                    },
                    "lookup_rule": "创建或更新 SQL 公共变量前，先调用 list_data_factory_datasource_aliases(project_product_id=当前产品ID) 查询逻辑数据源 ID，然后把返回的 datasource_alias_id 传给本字段。",
                    "query_rule": "已有 API 公共变量可调用 list_api_public_variables(project_product_id=当前产品ID, type=1) 查询，返回 datasource_alias_id 和 datasource_alias_name。",
                    "example": {
                        "project_product_id": 1,
                        "test_env_id": 0,
                        "type": 1,
                        "name": "查询用户",
                        "key": "user",
                        "value": "SELECT id,name FROM user WHERE id=${{user_id}}",
                        "datasource_alias_id": 2,
                        "status": 1,
                    },
                },
                "api_case": [
                    "project_product",
                    "module",
                    "name",
                    "case_people",
                    "level",
                    "scenario_layer",
                    "scenario_type",
                    "scenario_tags",
                    "scenario_description",
                    "front_headers",
                    "front_custom",
                    "front_sql",
                    "posterior_sql",
                ],
                "api_case_detailed": ["case", "api_info", "case_sort"],
                "api_case_detailed_parameter": [
                    "case_detailed",
                    "name",
                    "error_retry",
                    "retry_interval",
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
                    "posterior_file",
                    "posterior_func",
                ],
                "api_info_fields": {
                    "url": {
                        "type": "str",
                        "model_field": "ApiInfo.url",
                        "description": "只保存接口路径，不允许包含协议、域名、端口、query 或 fragment。",
                        "required_format": "/clm/api/category/update",
                        "forbidden": [
                            "https://test-contract.qtech.cn/clm/api/category/update",
                            "http://127.0.0.1:8000/api/demo",
                            "/api/demo?page=1",
                        ],
                        "query_rule": "query 参数请放到 params 字段，不要拼在 url 中。",
                    },
                    "file": {
                        "type": "list[object] | dict | null",
                        "model_field": "ApiInfo.file",
                        "description": "接口定义层的 multipart/form-data 文件参数。只要 file 非空，就必须使用 ${{get_file(已上传文件名)}} 引用。",
                        "required_format": file_example,
                        "field_name_rule": "对象 key 是请求文件字段名，例如 file/upload_file/test_file；对象 value 必须是 ${{get_file(已上传文件名)}}。",
                        "forbidden": ["本地路径", "URL", "裸文件名", "base64/二进制内容"],
                    },
                },
                "api_case_fields": {
                    "project_product_id": {
                        "type": "int",
                        "required": True,
                        "description": "项目产品 ID，对应 ApiCase.project_product。",
                    },
                    "module_id": {
                        "type": "int",
                        "required": True,
                        "description": "模块 ID，对应 ApiCase.module。",
                    },
                    "name": {
                        "type": "str",
                        "required": True,
                        "description": "API case 名称。",
                    },
                    "case_people_id": {
                        "type": "int | null",
                        "default": "当前 MCP APIKey/JWT 对应用户",
                        "description": "用例负责人。未传时 MCP 使用当前调用用户；显式传值时绑定指定负责人。",
                    },
                    "level": {
                        "type": "int",
                        "default": 1,
                        "enum_source": "CaseLevelEnum",
                        "enum": CaseLevelEnum.obj(),
                        "description": "用例级别。0=高(P0)，1=中(P1)，2=低(P2)，3=极低(P3)。",
                    },
                    "scenario_layer": {
                        "type": "int",
                        "default": 0,
                        "enum_source": "ApiCaseScenarioLayerEnum",
                        "enum": ApiCaseScenarioLayerEnum.obj(),
                        "description": "场景层级/测试分层。创建 API case 时必须明确选择：0=接口/组件层、1=Integration集成、2=E2E端到端。",
                        "coverage_distribution": {
                            "0_api_component": "接口/组件层，建议约 70%。用于单接口、组件能力、契约、参数、边界、异常、权限等底层能力校验，是主要覆盖层。",
                            "1_Integration": "Integration集成，建议约 20%。用于跨模块、跨服务、数据库、消息、第三方协作验证。",
                            "2_E2E": "E2E端到端，建议约 10%。用于核心用户路径和完整业务闭环验证。",
                        },
                    },
                    "scenario_type": {
                        "type": "int",
                        "default": 0,
                        "enum_source": "ApiCaseScenarioTypeEnum",
                        "enum": ApiCaseScenarioTypeEnum.obj(),
                        "description": "场景类型，描述当前 case 的测试意图，例如正常、异常、边界、权限、数据、流程。",
                    },
                    "scenario_tags": {
                        "type": "list[int]",
                        "default": [],
                        "enum_source": "ApiCaseScenarioTagEnum",
                        "enum": ApiCaseScenarioTagEnum.obj(),
                        "description": "场景标签，只表示执行策略或业务重要性，例如冒烟、回归、主流程、核心链路、高频、阻塞、线上巡检；不要把 API/Integration/E2E 放在这里。",
                        "selection_guidance": [
                            "冒烟用于每次发布前必须快速验证的关键路径。",
                            "回归用于版本变更后需要持续覆盖的稳定能力。",
                            "主流程/核心链路用于标记业务重要路径，高频/阻塞/线上巡检用于执行优先级或风险标识。",
                            "如果 case 不涉及 SQL 前后置、SQL 断言或数据工厂造数/清理，可默认增加 6=线上巡检，方便后续做生产/准生产巡检集合。",
                            "API/Integration/E2E 属于 scenario_layer，不属于 scenario_tags。",
                        ],
                    },
                    "scenario_description": {
                        "type": "str | null",
                        "default": None,
                        "description": "场景描述，展示在 API case 列表和详情头部。",
                    },
                    "front_custom": {
                        **key_value_schema,
                        "default": [],
                        "description": "用例执行前写入普通缓存。key 是缓存名；value 执行前会做变量替换。",
                        "example": [{"key": "tenant_id", "value": "896684654038353011"}],
                    },
                    "front_sql": {
                        **sql_key_value_schema,
                        "default": [],
                        "description": "用例执行前执行 SQL。value 是 SQL；查询结果第一行写入 SQL 缓存 key。",
                        "example": [{"key": "user", "value": "SELECT id,name FROM user WHERE id=${{user_id}}", "datasource_alias": 2}],
                    },
                    "front_headers": {
                        "type": "list[int]",
                        "default": [],
                        "description": "用例级默认请求头，只保存 ApiHeaders.id。只勾选当前 case 必须的公共请求头。",
                        "execution": "场景 headers 为空时使用；场景 headers 非空时被场景 headers 完全覆盖，不合并。",
                        "example": [1, 2, 3],
                    },
                    "posterior_sql": {
                        **sql_key_value_schema,
                        "default": [],
                        "description": "整个 API case 执行结束后执行 SQL。value 是 SQL；查询结果第一行写入 SQL 缓存 key。",
                        "example": [{"key": "order", "value": "SELECT id,status FROM orders WHERE id=${{order_id}}", "datasource_alias": 2}],
                    },
                    "parametrize": {
                        "type": "list[object]",
                        "default": [],
                        "description": "用例参数化。每组执行前把 parametrize 数组中的 key/value 写入缓存。",
                        "example": [{"name": "正常数据", "parametrize": [{"key": "name", "value": "AUTO_${{random_str(6)}}"}]}],
                    },
                },
                "api_case_scenario_fields": {
                    "step_id": {
                        "type": "int",
                        "required": True,
                        "description": "API case 步骤 ID，对应 ApiCaseDetailed.id；创建场景时内部保存为 case_detailed。",
                    },
                    "name": {
                        "type": "str",
                        "required": True,
                        "description": "场景参数名称。",
                    },
                    "error_retry": {
                        "type": "int | null",
                        "default": None,
                        "description": "失败重试次数；为空时执行 1 次。注意当前执行代码在捕获请求异常时会立即返回失败。",
                    },
                    "retry_interval": {
                        "type": "int | null",
                        "default": None,
                        "description": "每次失败后等待秒数。",
                    },
                    "headers": {
                        "type": "list[int]",
                        "default": [],
                        "description": "场景级请求头，只保存 ApiHeaders.id。",
                        "execution": "只要 headers 非空，就完全覆盖 api_case.front_headers，不会合并；headers=[] 时使用用例级 front_headers。",
                        "example": [4, 5],
                    },
                    "params": {
                        "type": "str | dict | list | null",
                        "saved_as": "TextField JSON 字符串或原字符串",
                        "description": "URL query 参数。MCP 传对象/数组会序列化为 JSON 字符串；执行前做变量替换。",
                        "example": {"page": 1, "name": "${{name}}"},
                    },
                    "data": {
                        "type": "str | dict | list | null",
                        "saved_as": "TextField JSON 字符串或原字符串",
                        "description": "表单/body data。MCP 传对象/数组会序列化为 JSON 字符串；执行前做变量替换。",
                        "example": {"username": "${{username}}", "password": "${{password}}"},
                    },
                    "json_body": {
                        "type": "str | dict | list | null",
                        "model_field": "json",
                        "saved_as": "TextField JSON 字符串或原字符串",
                        "description": "JSON 请求体。工具入参叫 json_body，后端模型字段叫 json；执行前做变量替换。",
                        "example": {"categoryName": "AUTO_${{random_str(8)}}", "enabled": True},
                    },
                    "file": {
                        "type": "list[object] | dict | null",
                        "description": "multipart/form-data 文件参数。必须先用 upload_system_file 上传，再用 ${{get_file(文件名)}} 引用文件名；不能直接传本地路径、URL、裸文件名或二进制内容。",
                        "required_format": file_example,
                        "field_name_rule": "对象 key 是请求文件字段名，例如 file/upload_file/test_file；对象 value 必须是 ${{get_file(已上传文件名)}}。",
                        "example": file_example,
                    },
                    "front_sql": {
                        **sql_key_value_schema,
                        "default": [],
                        "description": "场景请求前执行 SQL。value 是 SQL；查询结果第一行写入 SQL 缓存 key。",
                    },
                    "front_func": {
                        "type": "str | null",
                        "default": None,
                        "description": "场景请求前 Python 函数字符串，默认函数名 func，入参为 (self, request)，返回 RequestModel。",
                    },
                    "ass_jsonpath": {
                        "type": "list[object]",
                        "default": [],
                        "format": [{"actual": "$.code", "method": "p_is_equal_to", "expect": "0"}],
                        "description": "JSONPath 断言。actual 是响应 JSONPath；method 必须来自 get_api_assertion_methods 的叶子 value，不能写 eq。",
                        "expect_rule": "所选 method 的 parameter 包含 f=expect 时传预期值；不包含 expect 时传 null。",
                    },
                    "ass_general": {
                        "type": "list[object]",
                        "default": [],
                        "description": "通用断言。value 必须保存前端级联选中的完整对象；parameter[].v 是实际输入值。",
                        "format": [{"method": "内容断言 / 值等于什么 / 等于expect", "value": {"label": "等于expect", "value": "p_is_equal_to", "parameter": [{"f": "actual", "v": "${{actual}}"}, {"f": "expect", "v": "0"}]}}],
                    },
                    "ass_json_all": {
                        "type": "dict | list | null",
                        "default": None,
                        "description": "JSON 一致断言，用于断言基础、固定的响应 JSON 片段；使用 p_in_dict 到响应 JSON 中做局部包含匹配，不是全量相等断言。已在 ass_json_all 中断言的字段无需再重复添加到 ass_jsonpath。",
                        "example": {"code": 0, "data": {"status": 1}},
                    },
                    "ass_text_all": {
                        "type": "str | null",
                        "default": None,
                        "description": "文本一致断言，使用 response.text.strip() == expect.strip()。",
                    },
                    "ass_schema": {
                        "type": "dict | null",
                        "default": None,
                        "description": "JSON Schema 结构化断言；场景中填写后会覆盖 ApiInfo 开启的默认 schema。",
                    },
                    "posterior_response": {
                        **key_value_schema,
                        "default": [],
                        "description": "响应 JSON 提取。value 是 JSONPath，提取到的值写入普通缓存 key。",
                        "example": [{"key": "token", "value": "$.data.token"}],
                    },
                    "posterior_response_text": {
                        **key_value_schema,
                        "default": [],
                        "description": "响应文本提取。value 是正则表达式，匹配结果写入普通缓存 key。",
                        "example": [{"key": "order_id", "value": "orderId=(\\d+)"}],
                    },
                    "posterior_sql": {
                        **sql_key_value_schema,
                        "default": [],
                        "description": "响应后执行 SQL。value 是 SQL；查询结果第一行写入 SQL 缓存 key。",
                    },
                    "posterior_sleep": {
                        "type": "int | null",
                        "default": None,
                        "description": "响应后强制等待秒数。",
                    },
                    "posterior_file": {
                        **key_value_schema,
                        "default": {},
                        "description": "文件下载配置。value 是下载 URL，下载后把本地文件路径写入缓存 key；可通过 update_api_case_scenario 的 fields 设置。",
                        "example": [{"key": "download_file", "value": "${{download_url}}"}],
                    },
                    "posterior_func": {
                        "type": "str | null",
                        "default": None,
                        "description": "响应后 Python 函数字符串，默认函数名 func，入参为 (self, response)，返回 ResponseModel。",
                    },
                },
                "execution_rules": {
                    "headers": [
                        "api_case.front_headers 是用例级默认请求头，只保存 ApiHeaders.id 数组。",
                        "api_case_scenario.headers 也是 ApiHeaders.id 数组；只要场景 headers 非空，就会完全覆盖 api_case.front_headers，不会合并。",
                        "如果场景 headers=[]，执行时使用用例级 front_headers。",
                        "如果用例级 front_headers=[]，则 API case 请求头为空。",
                        "ApiInfo.headers 在 MCP 创建/更新接口定义时默认保持 null，不作为 API case 的请求头来源。",
                        "ApiHeaders.status=1 的全局默认请求头主要用于直接执行 ApiInfo 或接口定义初始化 headers；API case 执行主要依赖 case/scene 选择的 headers。",
                    ],
                    "execution_order": [
                        "初始化测试对象和 API 全局变量。",
                        "执行 api_case.front_custom，写入缓存。",
                        "执行 API case 级数据工厂前置。",
                        "执行 api_case.front_sql。",
                        "加载 api_case.front_headers 为用例级 headers。",
                        "按 case_sort 执行每个 ApiCaseDetailed 步骤。",
                        "每个步骤下按 id 执行所有 ApiCaseDetailedParameter 场景。",
                        "每个场景执行数据工厂前置、front_sql、front_func、请求、后置提取/SQL/sleep/function/file、断言。",
                        "API case 全部结束后执行 api_case.posterior_sql，并清理 case 级数据工厂。",
                    ],
                    "request_payload": [
                        "params/data/json_body/file 都以场景参数为准；添加步骤时默认从 ApiInfo 同步一份到默认场景。",
                        "refresh_api_case_step_from_api_info 会把 ApiInfo 的 params/data/json/file 同步到该步骤下所有场景。",
                        "params/data/json_body 传对象或数组时 MCP 会保存为 JSON 字符串；执行时再做变量替换和请求序列化。",
                    ],
                    "assertions": [
                        "ass_jsonpath.method 必须使用 get_api_assertion_methods 返回的叶子 value，例如 p_is_equal_to，不能使用 eq。",
                        "通用断言 ass_general 保存前端级联选项对象；更详细格式请调用 get_api_assertion_schema。",
                    ],
                },
                "examples": {
                    "api_case": {
                        "project_product_id": 7,
                        "module_id": 12,
                        "name": "编辑合同类型",
                        "case_people_id": None,
                        "level": 1,
                        "scenario_layer": 0,
                        "scenario_type": 0,
                        "scenario_tags": [0, 1],
                        "scenario_description": "验证编辑合同类型成功",
                        "front_custom": [{"key": "tenant_id", "value": "896684654038353011"}],
                        "front_sql": [{"key": "category", "value": "SELECT id FROM contract_category WHERE valid=1 LIMIT 1", "datasource_alias": 2}],
                        "front_headers": [10, 11],
                        "posterior_sql": [],
                    },
                    "api_case_scenario": {
                        "step_id": 18,
                        "name": "编辑成功",
                        "headers": [],
                        "params": None,
                        "data": None,
                        "json_body": {"categoryId": "${{category.id}}", "categoryName": "AUTO_${{random_str(8)}}"},
                        "file": file_example,
                        "ass_jsonpath": [{"actual": "$.code", "method": "p_is_equal_to", "expect": "0"}],
                        "posterior_response": [{"key": "category_id", "value": "$.data.id"}],
                    },
                    "headers_override": {
                        "case_front_headers": [1, 2],
                        "scenario_headers_empty": "headers=[] 时执行请求使用 [1,2]",
                        "scenario_headers_non_empty": "headers=[3] 时执行请求只使用 [3]，不会再带 [1,2]",
                    },
                },
                "enums": {
                    "scenario_layer": ApiCaseScenarioLayerEnum.obj(),
                    "scenario_type": ApiCaseScenarioTypeEnum.obj(),
                    "scenario_tags": ApiCaseScenarioTagEnum.obj(),
                },
                "scenario_layer_usage": {
                    "required": "创建 API case 时必须选择 scenario_layer。未传时 MCP 默认 0=接口/组件层。",
                    "coverage_distribution": {
                        "接口/组件层": "约 70%。单接口、组件能力、契约、边界、异常校验，是主要覆盖层。",
                        "Integration集成": "约 20%。跨模块、跨服务、数据库/消息/第三方协作验证。",
                        "E2E端到端": "约 10%。核心用户路径、完整业务闭环验证。",
                    },
                    "recommended_combinations": {
                        "普通接口或组件用例": {"scenario_layer": 0, "scenario_tags": []},
                        "冒烟接口或组件用例": {"scenario_layer": 0, "scenario_tags": [0]},
                        "回归接口或组件用例": {"scenario_layer": 0, "scenario_tags": [1]},
                        "跨服务集成用例": {"scenario_layer": 1, "scenario_tags": [1]},
                        "核心链路闭环用例": {"scenario_layer": 2, "scenario_tags": [3]},
                    },
                },
                "file_upload_usage": FILE_UPLOAD_USAGE,
                "notes": [
                    "创建 API 全局变量时 test_env_id 必填，对应 api_public.test_env。",
                    "API case 的 scenario_layer 默认 0=接口/组件层；scenario_type 默认 0=正常场景；scenario_tags 保存辅助标签整数数组；scenario_description 可为空。",
                    "当 API case 不依赖 SQL 或数据工厂时，推荐把 scenario_tags 默认加上 6=线上巡检；依赖数据准备、数据库断言或清理的数据型用例不要默认加线上巡检。",
                    "API 文件上传参数不要直接传本地路径；先用 upload_system_file 上传，再在 file 字段中通过 ${{get_file(文件名)}} 引用。",
                    "创建或编辑复杂场景前，建议先调用 get_api_assertion_schema 和 get_api_assertion_methods 获取断言格式和可选 method。",
                    "API case/场景的 front_sql、posterior_sql 如在多数据库测试环境中使用，先调用 list_data_factory_datasource_aliases(project_product_id) 查询逻辑数据源 ID，再写入 datasource_alias。",
                ],
            }
        )

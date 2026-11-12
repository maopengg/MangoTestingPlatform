"""API MCP payload normalization and shared helper implementation."""

from __future__ import annotations

import json as jsonlib
from typing import Any

from src.apps.auto_api.enums import MethodEnum
from src.apps.auto_api.models import (
    ApiCaseRelease,
    ApiInfo,
    ApiInfoRelease,
    ApiInfoRevision,
)
from src.apps.auto_api.schemas.case_schema import (
    build_body_from_legacy,
    merge_scenario_protocol_config,
    normalize_body_config_by_type,
)
from src.apps.auto_api.schemas.validation import ApiCaseValidationService
from src.apps.auto_api.selectors.querysets import ApiQuerySelector
from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
from src.apps.auto_api.services.api_info.runtime import ApiInfoRuntimeService
from src.apps.system.enums import CacheDataKey2Enum
from src.apps.system.services.configuration.cache_data_value import CacheDataValue
from src.common.exceptions import MangoServerError
from src.interfaces.mcp.common import (
    fail,
    validate_dangerous_action_confirmation,
)
from src.interfaces.mcp.exceptions import MCP_ASSERTION_METHOD_NOT_FOUND, McpError

API_CASE_RESULT_EXPORT_RELATIVE_DIR = "mcp_export/api_case_result"
API_CASE_RESULT_EXPORT_RETENTION_DAYS = 7

FILE_UPLOAD_USAGE = {
    "description": "API 接口定义和 API case 场景参数中的 multipart.files 用于描述 multipart/form-data 文件参数。",
    "required_format": {"body_type": "multipart", "body_config": {"fields": [], "files": [
        {"key": "请求文件字段名", "file_id": 1, "file_name": "可选发送文件名"}]}},
    "strict_rule": "文件必须来自测试配置-测试文件中的 FileData.id，不能直接传本地路径、URL、裸文件名或二进制内容。",
    "workflow": [
        "先调用 system_file 分组的 upload_system_file 上传真实文件，记录返回的 file.name 或上传时传入的 name。",
        "在 body_config.files 中写入 file_id，并把 key 设置为接口要求的文件字段名。",
        "执行时后端会按 file_id 读取 FileData.test_file 并发送文件。",
    ],
    "example": {"body_type": "multipart", "body_config": {"fields": [{"key": "name", "value": "demo"}],
                                                          "files": [{"key": "file", "file_id": 1}]}},
    "notes": [
        "示例中的 key 是请求参数名；如果接口字段名叫 upload_file，则 key 写 upload_file。",
        "建议先用 list_system_files 查询确认 file_id 和项目产品是否匹配。",
        "远程 MCP 服务通常无法读取调用者本机路径，因此只接受 FileData.id。",
    ],
}


def _json_string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return value
    return jsonlib.dumps(value, ensure_ascii=False, indent=4)


def _is_empty_value(value: Any) -> bool:
    return ApiCaseValidationService.is_empty_value(value)


def _clean_list_rows(value: Any) -> list:
    return ApiCaseValidationService.clean_list_rows(value)


def _validate_scenario_tags(tags: list[str] | None) -> str | None:
    return ApiCaseValidationService.validate_scenario_tags(tags)


def _normalize_body_payload(
        body_type: str | None = None,
        body_config: dict | None = None,
        sse_config: dict | None = None,
        data: Any = None,
        json_body: Any = None,
        file: Any = None,
) -> dict:
    if body_type:
        body_config = normalize_body_config_by_type(body_type, body_config)
        return {
            "body_type": body_type,
            "body_config": body_config,
            "sse_config": sse_config,
        }
    legacy_body_type, legacy_body_config = build_body_from_legacy(data=data, json_body=json_body, file_payload=file)
    legacy_body_config = normalize_body_config_by_type(legacy_body_type, legacy_body_config)
    return {
        "body_type": legacy_body_type,
        "body_config": legacy_body_config,
        "sse_config": sse_config,
    }


def _validate_sql_rows_datasource_alias(rows: Any, field_name: str) -> str | None:
    return ApiCaseValidationService.validate_sql_rows_datasource_alias(rows, field_name)


def _validate_api_case_sql_datasources(front_sql: Any = None, posterior_sql: Any = None,
                                       prefix: str = "") -> str | None:
    return ApiCaseValidationService.validate_sql_datasources(front_sql, posterior_sql, prefix)


def _duplicate_api_info_response(duplicate: ApiInfo) -> dict:
    return fail(
        f"接口定义已存在相同的项目产品、模块、端类型、请求方法、协议类型、请求体类型和URL，重复接口ID：{duplicate.id}",
        "API_INFO_DUPLICATE",
        {"api_info_id": duplicate.id, "name": duplicate.name, "url": duplicate.url},
    )


def _current_api_info_release(api_info_id: int) -> ApiInfoRelease | None:
    return ApiQuerySelector.api_info_release().filter(
        api_info_id=api_info_id,
        is_current=True,
        status=ApiInfoRelease.STATUS_PUBLISHED,
    ).select_related("api_info", "revision").order_by("-version_no").first()


def _current_api_case_release(case_id: int) -> ApiCaseRelease | None:
    return ApiQuerySelector.api_case_release().filter(
        api_case_id=case_id,
        is_current=True,
        status=ApiCaseRelease.STATUS_PUBLISHED,
    ).select_related("api_case", "revision").order_by("-version_no").first()


def _api_info_version_summary(api_info_id: int) -> dict:
    release = _current_api_info_release(api_info_id)
    latest_revision = ApiQuerySelector.api_info_revision().filter(api_info_id=api_info_id).order_by(
        "-revision_no").first()
    return {
        "current_revision_id": latest_revision.id if latest_revision else None,
        "current_revision_no": latest_revision.revision_no if latest_revision else None,
        "published_release_id": release.id if release else None,
        "published_revision_id": release.revision_id if release else None,
        "published_version_label": release.version_label if release else None,
        "publication_status": "published" if release else "unpublished",
    }


def _api_case_version_summary(case_id: int) -> dict:
    # MCP、REST 和页面必须共用同一发布状态口径。仅查询正式 Release 会把已经
    # 提交的预发布误报为 unpublished，也会丢失负责人审批所需的候选修订 ID。
    return ApiCaseRevisionService.get_publication_state(case_id).to_dict()


def _api_info_revision_summary(revision: ApiInfoRevision | None) -> dict:
    if revision is None:
        return {
            "api_info_revision_id": None,
            "api_info_revision_no": None,
            "api_info_revision_summary": None,
            "api_info_release_id": None,
            "api_info_version_label": None,
        }
    release = ApiQuerySelector.api_info_release().filter(
        revision_id=revision.id,
        status=ApiInfoRelease.STATUS_PUBLISHED,
    ).order_by("-is_current", "-version_no").first()
    return {
        "api_info_revision_id": revision.id,
        "api_info_revision_no": revision.revision_no,
        "api_info_revision_summary": revision.summary,
        "api_info_release_id": release.id if release else None,
        "api_info_version_label": release.version_label if release else None,
    }


def _published_api_info_modify_impact(api_info_id: int) -> dict:
    api_info = ApiQuerySelector.api_info().select_related("project_product", "module").get(id=api_info_id)
    release = _current_api_info_release(api_info_id)
    return {
        "target": {
            "type": "api_info",
            "api_info_id": api_info.id,
            "name": api_info.name,
            "project_product_id": api_info.project_product_id,
            "project_product_name": api_info.project_product.name if api_info.project_product else None,
            "module_id": api_info.module_id,
            "module_name": api_info.module.name if api_info.module else None,
        },
        "published": bool(release),
        "current_release": None if not release else {
            "release_id": release.id,
            "version_no": release.version_no,
            "version_label": release.version_label,
            "revision_id": release.revision_id,
            "published_at": release.published_at.strftime("%Y-%m-%d %H:%M:%S") if release.published_at else None,
        },
        "risk": "该接口已有已发布版本。直接修改只会改变接口当前编辑态，不会直接改动已发布版本；但会影响后续调试、生成新修订和再次发布。",
        "recommended_flow": [
            "如需基于已发布版本修改，先调用 checkout_api_info_revision_to_editing 迁出到编辑态。",
            "只在当前编辑态中修改并验证；已发布版本、历史修订均为只读。",
            "配置确认后可调用 create_api_info_revision_from_current 生成修订，再按需调用 publish_api_info_revision 发布正式版本；调试成功不是生成修订的前置条件。",
        ],
    }


def _published_api_case_modify_impact(case_id: int) -> dict:
    api_case = ApiQuerySelector.api_case().select_related("project_product", "module", "case_people").get(id=case_id)
    release = _current_api_case_release(case_id)
    return {
        "target": {
            "type": "api_case",
            "case_id": api_case.id,
            "name": api_case.name,
            "project_product_id": api_case.project_product_id,
            "project_product_name": api_case.project_product.name if api_case.project_product else None,
            "module_id": api_case.module_id,
            "module_name": api_case.module.name if api_case.module else None,
            "case_people_id": api_case.case_people_id,
            "case_people_name": api_case.case_people.name if api_case.case_people else None,
        },
        "published": bool(release),
        "current_release": None if not release else {
            "release_id": release.id,
            "version_no": release.version_no,
            "version_label": release.version_label,
            "revision_id": release.revision_id,
            "published_at": release.published_at.strftime("%Y-%m-%d %H:%M:%S") if release.published_at else None,
        },
        "risk": "该 API Case 已有已发布版本。直接修改只会改变用例当前编辑态，不会直接改动已发布版本；但会影响后续调试、生成新修订和再次发布。",
        "recommended_flow": [
            "如需基于已发布版本修改，先调用 checkout_api_case_revision_to_editing 迁出到编辑态。",
            "只在当前编辑态中修改步骤和场景参数；已发布版本、历史修订均为只读。",
            "断言配置确认后可调用 create_api_case_revision_from_current 生成修订，再调用 update_api_case_publication_status(target_status='prepublished', revision_id=修订ID) 提交预发布；只有项目产品负责人可以通过同一工具传 target_status='published' 生成正式版本。",
        ],
    }


def _require_published_api_info_modify_confirmation(
        api_info_id: int,
        preview_token: str | None,
        confirm_text: str | None,
) -> dict | None:
    if not _current_api_info_release(api_info_id):
        return None
    return validate_dangerous_action_confirmation(
        "modify_published_api_info",
        api_info_id,
        preview_token,
        confirm_text,
    )


def _require_published_api_case_modify_confirmation(
        case_id: int,
        preview_token: str | None,
        confirm_text: str | None,
) -> dict | None:
    if not _current_api_case_release(case_id):
        return None
    return validate_dangerous_action_confirmation(
        "modify_published_api_case",
        case_id,
        preview_token,
        confirm_text,
    )


def _api_info_delete_impact(api_info_id: int) -> dict:
    api_info = ApiInfoRuntimeService.resolve_runtime(api_info_id, allow_draft=True)
    dependency_impact = ApiCaseRevisionService.inspect_api_info_delete_dependencies(api_info_id)
    bound_steps = dependency_impact["editing_steps"]
    bound_cases = {}
    for step in bound_steps:
        bound_cases.setdefault(step.case_id, {
            "case_id": step.case_id,
            "case_name": step.case.name if step.case else None,
            "step_ids": [],
        })
        bound_cases[step.case_id]["step_ids"].append(step.id)
    can_delete = dependency_impact["can_delete"]
    release_count = ApiQuerySelector.api_info_release().filter(api_info_id=api_info_id).count()
    revision_count = ApiQuerySelector.api_info_revision().filter(api_info_id=api_info_id).count()
    return {
        "api_info": {
            "id": api_info.id,
            "name": api_info.name,
            "url": api_info.url,
            "method": api_info.method,
            "method_title": MethodEnum.get_value(api_info.method),
            "protocol_type": api_info.protocol_type,
            "project_product_id": api_info.project_product_id,
            "project_product_name": api_info.project_product.name if api_info.project_product else None,
            "module_id": api_info.module_id,
            "module_name": api_info.module.name if api_info.module else None,
        },
        "can_delete": can_delete,
        "will_delete": {
            "api_info": 1 if can_delete else 0,
            "api_info_releases": release_count if can_delete else 0,
            "api_info_revisions": revision_count if can_delete else 0,
        },
        "references": {
            "bound_api_case_step_count": len(bound_steps),
            "bound_api_case_ids": list(bound_cases.keys()),
            "bound_api_cases": list(bound_cases.values()),
            "self_contained_history_references": dependency_impact["self_contained_history_references"],
            "legacy_history_references": dependency_impact["legacy_history_references"],
        },
        "blockers": dependency_impact["blockers"],
        "risk": (
            "确认后删除 ApiInfo 及其接口修订和发布记录。自包含的 Case 历史快照不受影响；"
            "当前编辑态步骤或旧版非自包含快照仍会阻止删除。"
        ),
    }


def _api_info_revision_delete_impact(api_info_id: int, revision_id: int) -> dict:
    revision = ApiQuerySelector.api_info_revision().select_related("api_info", "parent_revision").get(
        id=revision_id,
        api_info_id=api_info_id,
    )
    release_ids = list(
        ApiQuerySelector.api_info_release().filter(revision_id=revision_id)
        .order_by("id")
        .values_list("id", flat=True)
    )
    child_revisions = list(
        ApiQuerySelector.api_info_revision().filter(parent_revision_id=revision_id)
        .order_by("revision_no")
        .values("id", "revision_no")
    )
    pinned_steps = list(
        ApiQuerySelector.api_case_detailed().select_related("case")
        .filter(pinned_api_info_revision_id=revision_id)
        .order_by("case_id", "case_sort", "id")
    )
    history_references = ApiCaseRevisionService.find_api_info_history_references(
        api_info_id,
        api_info_revision_id=revision_id,
    )
    blockers = []
    if release_ids:
        blockers.append("该接口修订已发布为版本，不能删除。")
    if pinned_steps:
        blockers.append("该接口修订已被 API Case 步骤固定引用，不能删除。")
    if history_references["legacy"]:
        blockers.append("该接口修订仍被未内嵌完整接口配置的旧版 Case 快照引用，不能删除。")
    if child_revisions:
        blockers.append("该接口修订存在后续子修订，不能删除；请从最新的叶子修订开始倒序删除。")
    can_delete = not blockers
    return {
        "revision": {
            "api_info_id": revision.api_info_id,
            "api_info_name": revision.api_info.name,
            "revision_id": revision.id,
            "revision_no": revision.revision_no,
            "summary": revision.summary,
            "parent_revision_id": revision.parent_revision_id,
        },
        "can_delete": can_delete,
        "will_delete": {"api_info_revision": 1 if can_delete else 0},
        "references": {
            "release_ids": release_ids,
            "child_revisions": child_revisions,
            "pinned_api_case_steps": [
                {
                    "step_id": step.id,
                    "case_id": step.case_id,
                    "case_name": step.case.name if step.case else None,
                }
                for step in pinned_steps
            ],
            "self_contained_history_references": history_references["self_contained"],
            "legacy_history_references": history_references["legacy"],
        },
        "blockers": blockers,
        "risk": "确认后仅删除该未发布接口修订，不删除接口定义、当前编辑态、其他修订或发布版本。",
    }


def _api_info_save_failed_response(error: MangoServerError) -> dict:
    return fail(error.msg, "API_INFO_SAVE_FAILED", {"code": error.code})


def _normalize_scenario_payload(payload: dict) -> dict:
    normalized = dict(payload)
    if any(key in normalized for key in ("body_config", "mcp_config", "grpc_config")):
        normalized["body_config"] = merge_scenario_protocol_config(
            normalized.get("body_config"),
            normalized.get("mcp_config"),
            normalized.get("grpc_config"),
        )
    for deprecated_key in ("protocol_type", "body_type", "data", "json", "json_body", "file"):
        normalized.pop(deprecated_key, None)
    for deprecated_key in ("mcp_config", "grpc_config"):
        normalized.pop(deprecated_key, None)
    for key in ("params",):
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
        assertion["group_name"] = str(assertion.get("group_name") or "").strip()
        assertion["group_logic"] = _normalize_assertion_group_logic(assertion.get("group_logic"))
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


def _normalize_assertion_group_logic(group_logic: Any) -> str:
    logic = str(group_logic or "AND").upper()
    return "OR" if logic == "OR" else "AND"


def _normalize_ass_jsonpath(assertions: list | None) -> list:
    """Normalize response extraction assertions to the executor's field shape."""
    if not assertions:
        return []
    normalized = []
    for item in assertions:
        if not isinstance(item, dict):
            continue
        actual = item.get("actual", item.get("path"))
        method = item.get("method", item.get("operator"))
        expect = item.get("expect", item.get("value"))
        assertion_type = str(item.get("assertion_type") or "jsonpath").lower()
        assertion_type = assertion_type if assertion_type in {"jsonpath", "regex", "cache"} else "jsonpath"
        group_name = str(item.get("group_name") or "").strip()
        group_logic = _normalize_assertion_group_logic(item.get("group_logic"))
        if _is_empty_value({"actual": actual, "method": method, "expect": expect}):
            continue
        if _jsonpath_method_uses_expect(method):
            normalized_expect = "" if expect is None else str(expect)
        else:
            normalized_expect = None
        normalized.append(
            {
                "actual": actual,
                "assertion_type": assertion_type,
                "method": method,
                "expect": normalized_expect,
                "group_name": group_name,
                "group_logic": group_logic,
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
    return CacheDataValue.get_cache_value(key=CacheDataKey2Enum.ASS_SELECT_VALUE.value)


def _selectable_assertion_method_groups() -> list[dict]:
    """Hide deprecated regex methods from new API/MCP assertion configurations."""
    deprecated_methods = {"p_matches", "p_does_not_match"}

    def clean(items: list[dict]) -> list[dict]:
        result = []
        for item in items or []:
            if item.get("value") in deprecated_methods:
                continue
            normalized = dict(item)
            if isinstance(item.get("children"), list):
                normalized["children"] = clean(item["children"])
            result.append(normalized)
        return result

    return clean(_api_assertion_method_groups())


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
        raise McpError(MCP_ASSERTION_METHOD_NOT_FOUND, value=(method_value,))
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

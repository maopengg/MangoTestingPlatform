# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API请求体结构迁移
# @Time   : 2026-06-16 00:00
# @Author : Codex
import json
import re
from typing import Any

from src.apps.auto_api.models import ApiCaseDetailedParameter, ApiInfo
from src.apps.system.models import FileData
from src.common.enums.api_enum import ApiBodyTypeEnum, ApiProtocolTypeEnum


GET_FILE_PATTERN = re.compile(r'^\s*\$\{\{get_file\((.+?)\)\}\}\}\s*$')


def _is_empty(value: Any) -> bool:
    if value in (None, '', {}, []):
        return True
    if isinstance(value, str) and value.strip() in ('', '{}', '[]', 'null', 'None'):
        return True
    return False


def _load_json_text(value: Any):
    if not isinstance(value, str):
        return value, None
    try:
        return json.loads(value), None
    except json.JSONDecodeError as error:
        return value, str(error)


def _mapping_to_fields(value: Any) -> list[dict]:
    loaded, _ = _load_json_text(value)
    if isinstance(loaded, dict):
        return [{'key': key, 'value': item} for key, item in loaded.items()]
    if isinstance(loaded, list):
        fields = []
        for item in loaded:
            if isinstance(item, dict) and set(item.keys()).issubset({'key', 'value'}):
                fields.append({'key': item.get('key') or '', 'value': item.get('value')})
            elif isinstance(item, dict):
                fields.extend({'key': key, 'value': item_value} for key, item_value in item.items())
            else:
                fields.append({'key': 'body', 'value': item})
        return fields
    return []


def _raw_body_config(value: Any) -> dict:
    return {
        'body_text': value if isinstance(value, str) else json.dumps(value, ensure_ascii=False),
        'content_type': 'application/json',
    }


def _json_body_config(value: Any, issues: list[dict], issue_context: dict) -> dict:
    if isinstance(value, str):
        parsed, error = _load_json_text(value)
        if error:
            if '${{' not in value:
                issues.append({**issue_context, 'issue_type': 'INVALID_JSON_NO_TEMPLATE', 'message': error})
            return {'source_type': 'template', 'body_text': value}
        if '${{' in value:
            return {'source_type': 'template', 'body_text': value}
        return {'source_type': 'value', 'body': parsed}
    return {'source_type': 'value', 'body': value}


def _extract_file_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = GET_FILE_PATTERN.match(value)
    if not match:
        return None
    return match.group(1).strip()


def _iter_file_payload(file_payload: Any) -> list[dict]:
    loaded, _ = _load_json_text(file_payload)
    if _is_empty(loaded):
        return []
    if isinstance(loaded, dict):
        loaded = [loaded]
    if not isinstance(loaded, list):
        return [{'key': 'file', 'value': loaded}]
    items = []
    for item in loaded:
        if not isinstance(item, dict):
            items.append({'key': 'file', 'value': item})
            continue
        if set(item.keys()).issubset({'key', 'value'}):
            items.append({'key': item.get('key') or '', 'value': item.get('value')})
            continue
        for key, value in item.items():
            items.append({'key': key, 'value': value})
    return items


def _resolve_file(file_name: str, project_product_id: int | None, issues: list[dict], issue_context: dict) -> FileData | None:
    file_data = FileData.objects.filter(name=file_name).first()
    if not file_data:
        issues.append({**issue_context, 'issue_type': 'FILE_NOT_FOUND', 'file_name': file_name})
        return None
    if project_product_id and file_data.project_product_id and file_data.project_product_id != project_product_id:
        issues.append({
            **issue_context,
            'issue_type': 'CROSS_PROJECT_FILE',
            'file_name': file_name,
            'file_project_product_id': file_data.project_product_id,
        })
        return None
    if not file_data.test_file:
        issues.append({**issue_context, 'issue_type': 'FILE_WITHOUT_UPLOAD', 'file_name': file_name})
        return None
    return file_data


def _file_payload_to_files(
        file_payload: Any,
        project_product_id: int | None,
        issues: list[dict],
        issue_context: dict,
) -> list[dict]:
    files = []
    for item in _iter_file_payload(file_payload):
        file_name = _extract_file_name(item.get('value'))
        if not file_name:
            issues.append({
                **issue_context,
                'issue_type': 'NOT_GET_FILE_EXPRESSION',
                'file_key': item.get('key'),
                'file_value': item.get('value'),
            })
            continue
        file_data = _resolve_file(file_name, project_product_id, issues, issue_context)
        if not file_data:
            continue
        files.append({
            'key': item.get('key') or file_data.name,
            'file_id': file_data.id,
            'file_name': file_data.name,
        })
    return files


def _build_body_from_old_fields(
        source_table: str,
        source_id: int,
        project_product_id: int | None,
        data: Any,
        json_body: Any,
        file_payload: Any,
        issues: list[dict],
) -> tuple[str, dict | None]:
    issue_context = {
        'source_table': source_table,
        'source_id': source_id,
        'project_product_id': project_product_id,
    }
    has_data = not _is_empty(data)
    has_json = not _is_empty(json_body)
    has_file = not _is_empty(file_payload)
    body_count = sum([has_data, has_json, has_file])
    if body_count > 1:
        issues.append({**issue_context, 'issue_type': 'MULTI_BODY_CONFLICT'})

    if has_file:
        fields = _mapping_to_fields(data) if has_data else []
        files = _file_payload_to_files(file_payload, project_product_id, issues, issue_context)
        return ApiBodyTypeEnum.MULTIPART.value, {'fields': fields, 'files': files}

    if has_json:
        return ApiBodyTypeEnum.JSON.value, _json_body_config(json_body, issues, issue_context)

    if has_data:
        loaded, error = _load_json_text(data)
        if error:
            return ApiBodyTypeEnum.RAW.value, _raw_body_config(data)
        if isinstance(loaded, (dict, list)):
            return ApiBodyTypeEnum.FORM.value, {'fields': _mapping_to_fields(loaded)}
        return ApiBodyTypeEnum.RAW.value, _raw_body_config(data)

    return ApiBodyTypeEnum.NONE.value, None


def _should_skip(obj) -> bool:
    return bool(obj.body_config) or obj.body_type not in (None, '', ApiBodyTypeEnum.NONE.value)


def _migrate_api_info(issues: list[dict]) -> dict:
    stats = {'total': 0, 'migrated': 0, 'skipped': 0}
    for api_info in ApiInfo.objects.all().only(
            'id',
            'project_product_id',
            'data',
            'json',
            'file',
            'protocol_type',
            'body_type',
            'body_config',
            'sse_config',
    ):
        stats['total'] += 1
        if _should_skip(api_info):
            stats['skipped'] += 1
            continue
        body_type, body_config = _build_body_from_old_fields(
            'api_info',
            api_info.id,
            api_info.project_product_id,
            api_info.data,
            api_info.json,
            api_info.file,
            issues,
        )
        api_info.protocol_type = api_info.protocol_type or ApiProtocolTypeEnum.HTTP.value
        api_info.body_type = body_type
        api_info.body_config = body_config
        api_info.save(update_fields=['protocol_type', 'body_type', 'body_config', 'update_time'])
        stats['migrated'] += 1
    return stats


def _migrate_api_case_parameter(issues: list[dict]) -> dict:
    stats = {'total': 0, 'migrated': 0, 'skipped': 0}
    queryset = ApiCaseDetailedParameter.objects.select_related('case_detailed__api_info').all()
    for parameter in queryset:
        stats['total'] += 1
        if _should_skip(parameter):
            stats['skipped'] += 1
            continue
        project_product_id = parameter.case_detailed.api_info.project_product_id
        body_type, body_config = _build_body_from_old_fields(
            'api_case_detailed_parameter',
            parameter.id,
            project_product_id,
            parameter.data,
            parameter.json,
            parameter.file,
            issues,
        )
        parameter.protocol_type = parameter.protocol_type or ApiProtocolTypeEnum.HTTP.value
        parameter.body_type = body_type
        parameter.body_config = body_config
        parameter.save(update_fields=['protocol_type', 'body_type', 'body_config', 'update_time'])
        stats['migrated'] += 1
    return stats


def main_6_3_1():
    print("开始执行 API 请求体结构迁移 6.3.1...")
    print("-" * 50)
    issues = []
    api_info_stats = _migrate_api_info(issues)
    parameter_stats = _migrate_api_case_parameter(issues)
    print(f"api_info：总数 {api_info_stats['total']}，迁移 {api_info_stats['migrated']}，跳过 {api_info_stats['skipped']}")
    print(
        "api_case_detailed_parameter："
        f"总数 {parameter_stats['total']}，迁移 {parameter_stats['migrated']}，跳过 {parameter_stats['skipped']}"
    )
    print(f"风险项：{len(issues)}")
    for issue in issues[:200]:
        print(json.dumps(issue, ensure_ascii=False))
    if len(issues) > 200:
        print(f"风险项超过 200 条，仅输出前 200 条，剩余 {len(issues) - 200} 条请使用迁移审计 SQL 查询。")
    print("API 请求体结构迁移 6.3.1 执行完成。")

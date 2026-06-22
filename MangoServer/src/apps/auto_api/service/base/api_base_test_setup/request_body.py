# -*- coding: utf-8 -*-
import json
from dataclasses import dataclass, field
from typing import Any, BinaryIO

import filetype

from src.apps.system.models import FileData
from src.common.enums.api_enum import ApiBodyTypeEnum, ApiProtocolTypeEnum
from src.common.exceptions import (
    ApiError,
    ERROR_MSG_0078,
    ERROR_MSG_0079,
    ERROR_MSG_0080,
    ERROR_MSG_0081,
    ERROR_MSG_0090,
)


SUPPORTED_PROTOCOLS = {ApiProtocolTypeEnum.HTTP.value, ApiProtocolTypeEnum.SSE.value}


@dataclass
class PreparedBody:
    kwargs: dict[str, Any] = field(default_factory=dict)
    request_body: Any = None
    request_files: list[dict] | None = None
    content_type: str | None = None
    file_handles: list[BinaryIO] = field(default_factory=list)

    def close(self):
        for handle in self.file_handles:
            try:
                handle.close()
            except Exception:
                pass


def ensure_supported_protocol(protocol_type: str):
    if protocol_type not in SUPPORTED_PROTOCOLS:
        raise ApiError(*ERROR_MSG_0078, value=(protocol_type,))


def normalize_body_config(body_config: dict | None) -> dict:
    if body_config is None:
        return {}
    if not isinstance(body_config, dict):
        raise ApiError(*ERROR_MSG_0079, value=('unknown', 'body_config 必须是对象'))
    return body_config


def parse_json_template(text: str, body_type: str) -> Any:
    try:
        return json.loads(text, strict=False)
    except json.JSONDecodeError as error:
        raise ApiError(*ERROR_MSG_0079, value=(body_type, f'模板变量替换后的内容不是合法JSON：{error}')) from error


def replace_value(test_data, value):
    if test_data is None:
        return value
    return test_data.replace(value)


def prepare_request_body(request_data, test_data, project_product_id: int | None = None) -> PreparedBody:
    ensure_supported_protocol(request_data.protocol_type)
    body_type = request_data.body_type or ApiBodyTypeEnum.NONE.value
    body_config = normalize_body_config(request_data.body_config)

    if body_type == ApiBodyTypeEnum.NONE.value:
        return PreparedBody()
    if body_type == ApiBodyTypeEnum.JSON.value:
        return prepare_json_body(body_config, test_data, body_type)
    if body_type == ApiBodyTypeEnum.FORM.value:
        return prepare_form_body(body_config, test_data, body_type)
    if body_type == ApiBodyTypeEnum.RAW.value:
        return prepare_raw_body(body_config, test_data, body_type)
    if body_type == ApiBodyTypeEnum.MULTIPART.value:
        return prepare_multipart_body(body_config, test_data, project_product_id, body_type)
    raise ApiError(*ERROR_MSG_0079, value=(body_type, '不支持的请求体类型'))


def prepare_json_body(body_config: dict, test_data, body_type: str) -> PreparedBody:
    source_type = body_config.get('source_type') or 'value'
    if source_type == 'template':
        body_text = replace_value(test_data, body_config.get('body_text') or '')
        body = parse_json_template(body_text, body_type)
    else:
        body = replace_value(test_data, body_config.get('body'))
        if isinstance(body, str):
            body = parse_json_template(body, body_type)
    return PreparedBody(kwargs={'json': body}, request_body=body, content_type='application/json')


def prepare_form_body(body_config: dict, test_data, body_type: str) -> PreparedBody:
    fields = body_config.get('fields') or []
    if not isinstance(fields, list):
        raise ApiError(*ERROR_MSG_0079, value=(body_type, 'fields 必须是数组'))
    data = {}
    for item in fields:
        if not isinstance(item, dict) or not item.get('key'):
            raise ApiError(*ERROR_MSG_0079, value=(body_type, '表单字段 key 不能为空'))
        data[str(item.get('key'))] = replace_value(test_data, item.get('value'))
    return PreparedBody(kwargs={'data': data}, request_body=data, content_type='application/x-www-form-urlencoded')


def prepare_raw_body(body_config: dict, test_data, body_type: str) -> PreparedBody:
    body_text = replace_value(test_data, body_config.get('body_text') or '')
    content_type = body_config.get('content_type') or 'application/json'
    return PreparedBody(kwargs={'content': body_text}, request_body=body_text, content_type=content_type)


def prepare_multipart_body(
        body_config: dict,
        test_data,
        project_product_id: int | None,
        body_type: str,
) -> PreparedBody:
    fields = body_config.get('fields') or []
    files = body_config.get('files') or []
    if not isinstance(fields, list) or not isinstance(files, list):
        raise ApiError(*ERROR_MSG_0079, value=(body_type, 'fields 和 files 必须是数组'))
    data = {}
    for item in fields:
        if not isinstance(item, dict) or not item.get('key'):
            raise ApiError(*ERROR_MSG_0079, value=(body_type, '普通字段 key 不能为空'))
        data[str(item.get('key'))] = replace_value(test_data, item.get('value'))

    prepared_files = []
    request_files = []
    file_handles = []
    for item in files:
        if not isinstance(item, dict) or not item.get('key') or not item.get('file_id'):
            raise ApiError(*ERROR_MSG_0079, value=(body_type, '文件字段 key 和 file_id 必填'))
        file_id = item.get('file_id')
        file_data = FileData.objects.filter(id=file_id).first()
        if not file_data or (project_product_id and file_data.project_product_id != project_product_id):
            raise ApiError(*ERROR_MSG_0080, value=(file_id,))
        if not file_data.test_file:
            raise ApiError(*ERROR_MSG_0081, value=(file_data.name,))
        try:
            handle = file_data.test_file.open('rb')
        except OSError as error:
            raise ApiError(*ERROR_MSG_0090, value=(file_data.name,)) from error
        file_handles.append(handle)
        file_name = item.get('file_name') or file_data.name
        try:
            kind = filetype.guess(file_data.test_file.path)
        except Exception:
            kind = None
        file_tuple = (file_name, handle, kind.mime) if kind else (file_name, handle)
        prepared_files.append((str(item.get('key')), file_tuple))
        request_files.append({
            'key': item.get('key'),
            'file_id': file_data.id,
            'file_name': file_name,
            'name': file_data.name,
        })
    kwargs = {'files': prepared_files}
    if data:
        kwargs['data'] = data
    return PreparedBody(
        kwargs=kwargs,
        request_body={'fields': data, 'files': request_files},
        request_files=request_files,
        content_type='multipart/form-data',
        file_handles=file_handles,
    )

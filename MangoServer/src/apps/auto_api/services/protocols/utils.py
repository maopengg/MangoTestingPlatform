# -*- coding: utf-8 -*-
import json
import re
from urllib.parse import quote

from src.apps.auto_api.exceptions import (
    AutoApiError,
    API_POSITIVE_INTEGER_REQUIRED,
)


def headers_with_content_type(headers: dict | None, content_type: str | None) -> dict | None:
    if not content_type:
        return headers
    normalized = dict(headers or {})
    if content_type == 'multipart/form-data':
        for key in list(normalized.keys()):
            if str(key).lower() == 'content-type':
                normalized.pop(key)
        return normalized
    if any(str(key).lower() == 'content-type' for key in normalized.keys()):
        return normalized
    normalized['Content-Type'] = content_type
    return normalized


def positive_int(value, name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as error:
        raise AutoApiError(API_POSITIVE_INTEGER_REQUIRED, value=(name, value)) from error
    if number <= 0:
        raise AutoApiError(API_POSITIVE_INTEGER_REQUIRED, value=(name, value))
    return number


def loads_json_text(text: str | None):
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def resolve_http_path_params(url: str | None, params):
    """Replace Spring-style ``{name}`` path variables and remove them from query params."""
    if not url or not params:
        return url, params
    if isinstance(params, dict):
        query_params = dict(params)
        pairs = query_params
    elif isinstance(params, list):
        try:
            query_params = list(params)
            pairs = dict(params)
        except (TypeError, ValueError):
            return url, params
    else:
        return url, params

    consumed = []
    for name in re.findall(r"\{([^{}]+)}", url):
        if name not in pairs or pairs[name] is None:
            continue
        value = pairs[name]
        if isinstance(value, (dict, list, tuple, set)):
            continue
        url = url.replace("{" + name + "}", quote(str(value), safe=""))
        consumed.append(name)

    if isinstance(query_params, dict):
        for name in consumed:
            query_params.pop(name, None)
    else:
        query_params = [item for item in query_params if not (
                isinstance(item, (list, tuple)) and len(item) == 2 and item[0] in consumed
        )]
    return url, query_params or None

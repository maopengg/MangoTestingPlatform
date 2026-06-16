# -*- coding: utf-8 -*-
import json
import re
from typing import Any

from src.apps.ai.service.core import mask_sensitive


class ApiAutomationResultExtractor:
    @staticmethod
    def first_message(response: dict) -> dict:
        choices = response.get("choices") or []
        if not choices:
            return {}
        return choices[0].get("message") or {}

    @staticmethod
    def message_content(message: dict) -> str:
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(str(item.get("text") or item) for item in content)
        return ""

    @staticmethod
    def tool_call_parts(tool_call: dict) -> tuple[str, str, dict]:
        function = tool_call.get("function") or {}
        name = function.get("name") or tool_call.get("name") or ""
        tool_call_id = tool_call.get("id") or name
        raw_arguments = function.get("arguments") or tool_call.get("arguments") or "{}"
        if isinstance(raw_arguments, dict):
            return tool_call_id, name, raw_arguments
        try:
            return tool_call_id, name, json.loads(raw_arguments or "{}")
        except json.JSONDecodeError:
            return tool_call_id, name, {"raw_arguments": raw_arguments}

    @classmethod
    def extract_api_case_id(cls, value: Any, allow_plain_id: bool = False) -> int | None:
        if isinstance(value, dict):
            keys = ("api_case_id", "case_id", "id") if allow_plain_id else ("api_case_id", "case_id")
            for key in keys:
                raw_value = value.get(key)
                if isinstance(raw_value, int):
                    return raw_value
                if isinstance(raw_value, str) and raw_value.isdigit():
                    return int(raw_value)
            for nested_key in ("api_case", "case", "data", "result", "binding", "output", "structuredContent", "structured_content"):
                found = cls.extract_api_case_id(value.get(nested_key), allow_plain_id=nested_key in ("api_case", "case"))
                if found:
                    return found
            content = value.get("content")
            if isinstance(content, list):
                for item in content:
                    found = cls.extract_api_case_id(item)
                    if found:
                        return found
            if isinstance(content, str):
                return cls.extract_api_case_id(content)
            for text_key in ("text", "value"):
                if isinstance(value.get(text_key), str):
                    found = cls.extract_api_case_id(value.get(text_key))
                    if found:
                        return found
        if isinstance(value, list):
            for item in value:
                found = cls.extract_api_case_id(item)
                if found:
                    return found
        if isinstance(value, str):
            try:
                return cls.extract_api_case_id(json.loads(value))
            except Exception:
                match = re.search(r"(?:api_case_id|case_id)[^\d]{0,20}(\d+)", value)
                return int(match.group(1)) if match else None
        return None

    @staticmethod
    def extract_mcp_text(result: Any) -> str:
        if isinstance(result, dict):
            content = result.get("content")
            if isinstance(content, list):
                return "\n".join(str(item.get("text") or item.get("value") or item) if isinstance(item, dict) else str(item) for item in content)
            if isinstance(content, str):
                return content
        return json.dumps(mask_sensitive(result), ensure_ascii=False)

    @classmethod
    def extract_mcp_error_message(cls, result: Any) -> str:
        if isinstance(result, str):
            try:
                return cls.extract_mcp_error_message(json.loads(result))
            except Exception:
                return result if "error" in result.lower() or "失败" in result else ""
        if isinstance(result, dict):
            text = result.get("text")
            if isinstance(text, str):
                nested = cls.extract_mcp_error_message(text)
                if nested:
                    return nested
            content = result.get("content")
            if isinstance(content, list):
                for item in content:
                    nested = cls.extract_mcp_error_message(item)
                    if nested:
                        return nested
            for nested_key in ("data", "result", "structuredContent", "structured_content"):
                nested = cls.extract_mcp_error_message(result.get(nested_key))
                if nested:
                    return nested
            if result.get("success") is False or result.get("isError") is True:
                message = result.get("message") or result.get("msg") or result.get("error") or "MCP工具执行失败"
                error_code = result.get("error_code") or result.get("code")
                return f"{message}（{error_code}）" if error_code else str(message)
        return ""

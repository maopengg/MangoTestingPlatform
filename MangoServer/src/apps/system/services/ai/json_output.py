import json
import re
from src.apps.system.exceptions import ai_service_error
from src.apps.system.services.ai.client import AiService
from src.common.prompts import get_prompt

def extract_ai_json(response: dict, *, repair_chat=None) -> dict:
    choices = response.get("choices") or []
    if not choices:
        return {}
    message = choices[0].get("message") or {}
    content = message.get("content") or "{}"
    if isinstance(content, dict):
        return content
    return parse_ai_json_content(str(content), repair_chat=repair_chat)


def parse_ai_json_content(content: str, *, allow_ai_repair: bool = True, repair_chat=None) -> dict:
    json_content = extract_json_text(content)
    try:
        return json.loads(json_content)
    except json.JSONDecodeError as exc:
        if not allow_ai_repair:
            raise
        return repair_ai_json_content(json_content, exc, repair_chat=repair_chat)


def extract_json_text(content: str) -> str:
    text = (content or "{}").strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        text = text[start: end + 1]
    return text


def repair_ai_json_content(content: str, error: json.JSONDecodeError, *, repair_chat=None) -> dict:
    prompt = get_prompt("ai.json_repair")
    repair_messages = [
        {"role": "system", "content": prompt.system},
        {
            "role": "user",
            "content": prompt.render(
                "user",
                error_message=error.msg,
                line=error.lineno,
                column=error.colno,
                content=content[:120000],
            ),
        },
    ]
    repaired_response = (repair_chat or AiService.json_chat)(messages=repair_messages, max_tokens=16000)
    choices = repaired_response.get("choices") or []
    if not choices:
        raise ai_service_error(f"AI返回的JSON格式不正确，且自动修复失败：{error.msg}")
    repaired_content = choices[0].get("message", {}).get("content") or "{}"
    if isinstance(repaired_content, dict):
        return repaired_content
    try:
        return parse_ai_json_content(str(repaired_content), allow_ai_repair=False, repair_chat=repair_chat)
    except json.JSONDecodeError as repair_error:
        raise ai_service_error(
            f"AI返回的JSON格式不正确，自动修复后仍无法解析：{repair_error.msg}，line {repair_error.lineno} column {repair_error.colno}"
        ) from repair_error

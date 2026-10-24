import json

from src.common.prompts import get_prompt

_PROMPT = get_prompt("pytest.case_inference")
PYTEST_CASE_INFERENCE_PROMPT_VERSION = f"v{_PROMPT.version}"


def build_pytest_case_inference_messages(payload: dict) -> list[dict]:
    return [
        {'role': 'system', 'content': _PROMPT.system},
        {
            'role': 'user',
            'content': json.dumps(payload, ensure_ascii=False, separators=(',', ':')),
        },
    ]

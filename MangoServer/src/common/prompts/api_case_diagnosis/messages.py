import json

from src.common.prompts import get_prompt

_PROMPT = get_prompt("api.case_diagnosis")
API_CASE_DIAGNOSIS_PROMPT_VERSION = f"v{_PROMPT.version}"


def build_api_case_diagnosis_messages(evidence: dict) -> list[dict]:
    return [
        {'role': 'system', 'content': _PROMPT.system},
        {
            'role': 'user',
            'content': json.dumps(
                {'prompt_version': API_CASE_DIAGNOSIS_PROMPT_VERSION, 'evidence': evidence},
                ensure_ascii=False,
                separators=(',', ':'),
            ),
        },
    ]

import json

from src.common.prompts import get_prompt

_PROMPT = get_prompt("api.assertion_diagnosis")
ASSERTION_DIAGNOSIS_PROMPT_VERSION = f"v{_PROMPT.version}"


def build_assertion_diagnosis_messages(assertions: list[dict]) -> list[dict]:
    return [
        {'role': 'system', 'content': _PROMPT.system},
        {
            'role': 'user',
            'content': json.dumps(
                {'prompt_version': ASSERTION_DIAGNOSIS_PROMPT_VERSION, 'assertions': assertions},
                ensure_ascii=False,
                separators=(',', ':'),
            ),
        },
    ]

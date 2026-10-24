import json
from src.common.prompts import get_prompt


_PROMPT = get_prompt("evaluation.judge")
EVALUATION_JUDGE_PROMPT_VERSION = int(_PROMPT.version)



def build_evaluation_judge_messages(*, dataset_item: dict, actual: dict, rubric: dict, metric_key: str):
    payload = {
        "prompt_version": EVALUATION_JUDGE_PROMPT_VERSION,
        "metric_key": metric_key,
        "dataset_item": dataset_item,
        "actual": actual,
        "rubric": rubric,
        "output_schema": _PROMPT.values["output_schema"],
    }
    return [
        {"role": _PROMPT.values["roles"]["system"], "content": _PROMPT.system},
        {"role": _PROMPT.values["roles"]["user"], "content": json.dumps(payload, ensure_ascii=False, default=str)},
    ]

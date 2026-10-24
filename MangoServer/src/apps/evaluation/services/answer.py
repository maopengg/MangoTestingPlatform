import json
from src.apps.ai.services.core import parse_ai_json_content
from src.apps.evaluation.exceptions import EvaluationError, EVALUATION_ANSWER_MODEL_CHANGED
from src.apps.evaluation.formatters.payload import select_value, mask_sensitive
from src.apps.evaluation.schemas.answer import EvaluationAnswerOutput
from src.apps.evaluation.services.validation import invalid_config
from src.apps.evaluation.services.ai import model_snapshot, json_chat
from src.common.prompts import get_prompt


def answer_model_snapshot(profile_id=None):
    return model_snapshot(profile_id, "evaluation.memory")


def strict_model_output(response):
    choices = response.get("choices") or []
    content = ((choices[0].get("message") or {}).get("content")) if choices else None
    if isinstance(content, dict):
        return content
    if not isinstance(content, str) or not content.strip():
        raise invalid_config("模型未返回有效的结构化内容")
    return parse_ai_json_content(content, allow_ai_repair=False)


def generate_answer(*, settings, frozen_model, dataset_item, retrieved, timeout_seconds=None):
    if frozen_model is None:
        raise EvaluationError(EVALUATION_ANSWER_MODEL_CHANGED)
    question = dataset_item.input_data if isinstance(dataset_item.input_data, str) else select_value(dataset_item.input_data, settings.question_path)
    if not isinstance(question, str) or not question.strip():
        raise invalid_config("问答生成需要非空问题")
    # Gold answers and annotation context must never enter the answer generation request.
    payload = {"question": question, "memories": retrieved}
    response = json_chat(frozen=frozen_model.model_dump(mode="json", exclude_none=True), prompt_id="evaluation.memory", messages=[
        {"role": "system", "content": get_prompt("evaluation.memory").system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ], temperature=0, max_tokens=settings.max_tokens, timeout_seconds=timeout_seconds)
    parsed = EvaluationAnswerOutput.model_validate(strict_model_output(response))
    return {"retrieval": mask_sensitive(retrieved), "answer": parsed.answer,
            "answer_model": frozen_model.model_dump(mode="json")}

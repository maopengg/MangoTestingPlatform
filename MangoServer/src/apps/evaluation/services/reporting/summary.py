import json
from src.apps.evaluation.schemas.answer import EvaluationAiSummary
from src.apps.evaluation.services.model.ai import json_chat
from src.apps.evaluation.services.model.answer import strict_model_output
from src.common.prompts import get_prompt


def generate_summary(execution, config):
    frozen = config.summary_model.model_dump(mode="json", exclude_none=True)
    facts = {"case": config.case, "dataset": config.dataset, "target": {key: value for key, value in config.target.items() if key != "parameters"},
             "summary": execution.summary, "assessment": config.assessment.model_dump(mode="json") if config.assessment else None}
    response = json_chat(frozen=frozen, prompt_id="evaluation.summary", messages=[
        {"role": "system", "content": get_prompt("evaluation.summary").system},
        {"role": "user", "content": json.dumps(facts, ensure_ascii=False)},
    ], temperature=0, max_tokens=4000)
    parsed = EvaluationAiSummary.model_validate(strict_model_output(response))
    return {"status": "completed", "model": frozen, **parsed.model_dump(mode="json")}

from dataclasses import replace
from src.apps.evaluation.formatters.payload import content_hash
from src.apps.evaluation.services.validation import invalid_config
from src.apps.system.services.ai.evaluation_profiles import EvaluationAiProfileService
from src.apps.system.services.ai.client import AiService
from src.common.prompts import get_prompt


def ai_options(case_id, user):
    from src.apps.evaluation.selectors.case import get_case
    get_case(case_id, user)
    return EvaluationAiProfileService.options()


def resolve_model(profile_id, prompt_id):
    if not profile_id:
        raise invalid_config("请在用例中选择 AI：系统默认 AI 或独立配置的效果测评 AI")
    profile, config = EvaluationAiProfileService.resolve(profile_id)
    snapshot = {"profile_id": profile.id, "name": profile.name, "provider": config.provider_type,
        "model": config.model, "endpoint_hash": content_hash(config.base_url),
        "config_hash": content_hash({"provider": config.provider_type, "endpoint": config.base_url,
                                     "model": config.model, "timeout": config.timeout}),
        "prompt_version": int(get_prompt(prompt_id).version)}
    return config, snapshot


def model_snapshot(profile_id, prompt_id):
    return resolve_model(profile_id, prompt_id)[1]


def json_chat(*, frozen, prompt_id, timeout_seconds=None, **kwargs):
    config, current = resolve_model((frozen or {}).get("profile_id"), prompt_id)
    if {key: value for key, value in frozen.items() if key != "name"} != {key: value for key, value in current.items() if key != "name"}:
        raise invalid_config("所选效果测评 AI 配置已变更，请重新执行以记录新配置")
    if timeout_seconds is not None:
        config = replace(config, timeout=max(1, min(config.timeout, int(timeout_seconds))))
    return AiService.json_chat(config=config, **kwargs)

"""Resolve default, item overrides and required grading into immutable bindings."""

from pydantic import ValidationError
from jsonschema import SchemaError, ValidationError as JsonSchemaValidationError
from src.apps.evaluation.schemas.case import EvaluationItemGrading
from src.apps.evaluation.services.grading.graders import EvaluationGraderRegistry
from src.apps.evaluation.services.assets.validation import invalid_config


def validate_bindings(bindings, *, require_weight=True):
    active = [binding for binding in bindings if binding.enabled]
    identities = [(item.grader_key, item.grader_version, item.metric_key) for item in active]
    metric_keys = []
    for item in active:
        suffixes = ("", "_precision", "_recall") if item.grader_key in {"set_match", "field_extraction", "memory_extraction"} else ("", "_mrr", "_recall_at_k") if item.grader_key == "ranking" else ("",)
        metric_keys.extend(item.metric_key + suffix for suffix in suffixes)
        if any(len(item.metric_key + suffix) > 64 for suffix in suffixes):
            raise invalid_config("指标编码及其派生指标不能超过 64 个字符")
    if len(identities) != len(set(identities)) or len(metric_keys) != len(set(metric_keys)):
        raise invalid_config("评分项的指标身份冲突，请为独立评分使用不同的指标编码")
    for binding in active:
        if not EvaluationGraderRegistry.resolve(binding.grader_key, binding.grader_version)[0]:
            raise invalid_config(f"评分器或版本未注册：{binding.grader_key}@{binding.grader_version}")
        try:
            EvaluationGraderRegistry.validate_config(binding.grader_key, binding.grader_version, binding.parameters)
        except (ValidationError, JsonSchemaValidationError, SchemaError) as error:
            raise invalid_config(f"{binding.metric_key} 参数不合法：{error}") from error
        if binding.hard_gate and EvaluationGraderRegistry.is_model(binding.grader_key):
            raise invalid_config("AI 评分不能作为硬门禁")
    if require_weight and (not active or not any(item.weight > 0 and not item.hard_gate for item in active)):
        raise invalid_config("至少配置一个启用且权重大于零的非硬门禁评分项")
    return active


def resolve_graders(grading, item_config):
    try:
        override = EvaluationItemGrading.model_validate(item_config or {})
    except ValidationError as error:
        raise invalid_config(str(error)) from error
    origin = "override" if override.mode == "replace" else "default"
    defaults = override.graders if override.mode == "replace" else grading.default_graders
    entries = [(binding, origin) for binding in defaults if binding.enabled]
    entries += [(binding, "required") for binding in grading.required_graders if binding.enabled]
    validate_bindings([binding for binding, _ in entries])
    return entries

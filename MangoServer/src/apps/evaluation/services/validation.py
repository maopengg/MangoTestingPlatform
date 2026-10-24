"""Business validation shared by HTTP forms and evaluation services."""

from src.apps.evaluation.exceptions import EVALUATION_ASSET_CONFIG_INVALID, EvaluationError


def invalid_config(message):
    if isinstance(message, dict):
        message = "; ".join(f"{key}: {value}" for key, value in message.items())
    return EvaluationError(EVALUATION_ASSET_CONFIG_INVALID, value=(message,))


def validate_relation(attrs, instance=None):
    project_product = attrs.get("project_product", getattr(instance, "project_product", None))
    module = attrs.get("module", getattr(instance, "module", None))
    if module and project_product and module.project_product_id != project_product.id:
        raise invalid_config({"module": "模块不属于当前项目产品"})
    return attrs


def validate_dataset(attrs, instance=None):
    if instance is None or "task_type" in attrs:
        if not attrs.get("task_type", getattr(instance, "task_type", None)):
            raise invalid_config("请至少输入一个任务类型")
    return attrs

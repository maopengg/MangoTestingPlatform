"""Validate and freeze references without storing credentials in datasets."""

from copy import deepcopy
from src.apps.evaluation.enums.workflow import EvaluationWorkflowActionEnum
from src.apps.evaluation.formatters.payload import content_hash, plaintext_secret_paths
from src.apps.evaluation.schemas.dataset import EvaluationDatasetSchema
from src.apps.evaluation.selectors.workflow import resource_configuration
from src.apps.evaluation.services.validation import invalid_config
from src.apps.evaluation.services.python_target import validate_python_target


def freeze_dataset_configuration(value, user, *, product_id=None, target_ref_id=None, publishing=False):
    config = EvaluationDatasetSchema.model_validate(deepcopy(value or {}))
    if plaintext_secret_paths(config.model_dump(mode="json")):
        raise invalid_config("流程中的敏感信息必须使用凭据引用")
    actions = {}
    if publishing or product_id is not None:
        from src.apps.evaluation.enums.workflow import EvaluationPreparationEnum, EvaluationWorkflowStageEnum
        prepare_steps = [step for step in config.workflow.steps if step.stage in {EvaluationWorkflowStageEnum.PREPARE, EvaluationWorkflowStageEnum.READY}]
        if config.workflow.preparation == EvaluationPreparationEnum.NONE and prepare_steps:
            raise invalid_config("已有准备步骤，请选择读取已有数据或自动创建数据")
        if config.workflow.preparation == EvaluationPreparationEnum.CREATE and not any(step.stage == EvaluationWorkflowStageEnum.CLEANUP or step.action == EvaluationWorkflowActionEnum.FACTORY for step in config.workflow.steps):
            raise invalid_config("自动创建数据必须配置清理步骤，或使用能自动清理的数据工厂")
    for step in config.workflow.steps:
        if step.action == EvaluationWorkflowActionEnum.SCRIPT:
            validate_python_target(step.code)
            continue
        if step.resource in actions and actions[step.resource] != step.action:
            raise invalid_config("同一流程资源不能绑定不同执行类型")
        actions[step.resource] = step.action
    frozen = []
    for binding in config.workflow.bindings:
        if product_id is not None and binding.project_product_id != product_id:
            continue
        if product_id is not None and binding.target_ref_id is not None and binding.target_ref_id != target_ref_id:
            continue
        if binding.resource not in actions:
            raise invalid_config("存在未被步骤引用的资源绑定")
        revision, value = resource_configuration(actions[binding.resource], binding, user)
        digest = content_hash(value)
        if binding.content_hash and binding.content_hash != digest:
            raise invalid_config("流程资源已变更，请复制测评集新版本并重新绑定")
        binding.revision_id = revision
        binding.content_hash = digest
        frozen.append(binding)
    if product_id is not None:
        preferred = {}
        for binding in frozen:
            if binding.resource not in preferred or binding.target_ref_id is not None:
                preferred[binding.resource] = binding
        frozen = list(preferred.values())
        if set(actions) - {binding.resource for binding in frozen}:
            raise invalid_config("当前被测项目产品缺少测评集流程资源绑定，请在测评集版本中配置")
        config.workflow.bindings = frozen
    elif publishing and set(actions) - {binding.resource for binding in frozen}:
        raise invalid_config("测评集流程存在未绑定的资源")
    return config

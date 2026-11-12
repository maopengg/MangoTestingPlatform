"""Evaluation asset mutations for non-HTTP clients; reuse domain services."""

from pydantic import ValidationError
from django.db import transaction
from src.apps.evaluation.schemas.assets import EvaluationCaseAssetCreate, EvaluationDatasetAssetCreate
from src.apps.evaluation.models import EvaluationDataset
from src.apps.evaluation.selectors.scope import ensure_product_scope, ensure_dataset_access
from src.apps.test_center.selectors.querysets import TestCenterQuerySelector
from src.apps.evaluation.selectors.case import get_case
from src.apps.evaluation.selectors.dataset_version import get_dataset_version
from src.apps.evaluation.services.assets.case import EvaluationCaseService
from src.apps.evaluation.formatters.case_description import case_description
from src.apps.evaluation.services.execution.execution import EvaluationCaseExecutionService
from src.apps.evaluation.services.assets.validation import invalid_config
from src.apps.evaluation.enums import EvaluationStatusEnum
from src.apps.evaluation.exceptions import EVALUATION_TARGET_ACCESS_DENIED, EvaluationError
from src.apps.user.services.authorization.permission import PermissionMenuService


@transaction.atomic
def ensure_dataset(values, user):
    try:
        data = EvaluationDatasetAssetCreate.model_validate(values)
    except ValidationError as error:
        raise invalid_config(str(error)) from error
    ensure_dataset_access(user)
    dataset = EvaluationDataset.objects.filter(name=data.name).first()
    if dataset is not None:
        if set(dataset.task_type) != set(data.task_type):
            raise invalid_config("同名数据集已有不同任务类型，不能静默复用或新建")
        return dataset, False
    return EvaluationDataset.objects.create(name=data.name, task_type=data.task_type,
        description=data.description, owner=user, update_user=user), True


def create_case(values, user):
    try:
        data = EvaluationCaseAssetCreate.model_validate(values)
    except ValidationError as error:
        raise invalid_config(str(error)) from error
    version = get_dataset_version(data.dataset_version_id, user) if data.dataset_version_id else None
    if data.project_product_id is None:
        raise invalid_config("创建用例时必须指定项目产品")
    ensure_product_scope(user, data.project_product_id)
    product = TestCenterQuerySelector.project_product().filter(pk=data.project_product_id).first()
    if product is None:
        raise invalid_config("项目产品不存在")
    return EvaluationCaseService.save(values={"name": data.name, "dataset_version": version,
        "project_product": product, "module": None,
        "description": data.description, "config": data.config.model_dump(mode="json") if data.config else {}, "owner": user, "update_user": user})


def create_dataset_item(version_id, values, user):
    from src.apps.evaluation.schemas.item import EvaluationDatasetItemPayload
    from src.apps.evaluation.services.dataset.dataset_item import EvaluationDatasetItemService
    version = get_dataset_version(version_id, user)
    try:
        data = EvaluationDatasetItemPayload.model_validate(values)
    except ValidationError as error:
        raise invalid_config(str(error)) from error
    return EvaluationDatasetItemService.save(version=version, values=data.model_dump(mode="json"))


def set_case_status(case_id, status, user):
    if status not in {entry.value for entry in EvaluationStatusEnum}:
        raise invalid_config("未知评测用例状态")
    if not PermissionMenuService.is_effective_super_admin(user) and "evaluation.case:change" not in PermissionMenuService.permission_keys_for_user(user):
        raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)
    case = get_case(case_id, user)
    return EvaluationCaseService.save(instance=case, values={"status": status, "update_user": user})


def update_case(case_id, values, user):
    case = get_case(case_id, user)
    try:
        data = EvaluationCaseAssetCreate.model_validate({
            "name": case.name, "description": case_description(case), "dataset_version_id": case.dataset_version_id,
            "config": case.config or None, **values})
    except ValidationError as error:
        raise invalid_config(str(error)) from error
    version = get_dataset_version(data.dataset_version_id, user) if data.dataset_version_id else None
    return EvaluationCaseService.save(instance=case, values={"name": data.name, "description": data.description,
        "dataset_version": version, "config": data.config.model_dump(mode="json") if data.config else {}, "update_user": user})


def execute_case(case_id, test_env, idempotency_key, user, item_ids=None):
    get_case(case_id, user)
    values = {"case_id": case_id, "test_env": test_env, "idempotency_key": idempotency_key}
    if item_ids is not None:
        values["item_ids"] = item_ids
    record = EvaluationCaseExecutionService.create(values, user)
    EvaluationCaseExecutionService.submit(record.id)
    return record

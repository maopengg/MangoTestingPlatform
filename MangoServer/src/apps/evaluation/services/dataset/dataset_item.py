"""Draft dataset_item persistence and dataset quality invalidation."""

from django.db import transaction
from pydantic import ValidationError
from src.apps.evaluation.services.assets.validation import invalid_config
from src.apps.evaluation.schemas.case import EvaluationItemGrading
from src.apps.evaluation.enums import EvaluationVersionStatusEnum
from src.apps.evaluation.exceptions import EVALUATION_PUBLISHED_VERSION_IMMUTABLE, EvaluationError
from src.apps.evaluation.formatters.payload import content_hash
from src.apps.evaluation.models import EvaluationDatasetVersion, EvaluationDatasetItem
from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService


class EvaluationDatasetItemService:
    @staticmethod
    def ensure_draft(version):
        if version.status != EvaluationVersionStatusEnum.DRAFT.value:
            raise EvaluationError(EVALUATION_PUBLISHED_VERSION_IMMUTABLE)

    @staticmethod
    def reset_quality_ack(version):
        version.quality_report = {}
        version.quality_warning_acknowledged_by = None
        version.quality_warning_acknowledged_at = None
        version.save(update_fields=[
            "quality_report", "quality_warning_acknowledged_by",
            "quality_warning_acknowledged_at", "update_time",
        ])

    @classmethod
    @transaction.atomic
    def save(cls, *, values, version, instance=None):
        version = EvaluationDatasetVersion.objects.select_for_update().get(pk=version.pk)
        cls.ensure_draft(version)
        dataset_item = instance or EvaluationDatasetItem(dataset_version=version)
        for field, value in values.items():
            setattr(dataset_item, field, value)
        try:
            dataset_item.grading_config = EvaluationItemGrading.model_validate(dataset_item.grading_config or {}).model_dump(mode="json")
        except ValidationError as error:
            raise invalid_config(str(error)) from error
        EvaluationVersionService.validate_item(version, EvaluationVersionService.item_payload(dataset_item))
        dataset_item.content_hash = content_hash(EvaluationVersionService.item_payload(dataset_item))
        dataset_item.save()
        cls.reset_quality_ack(version)
        return dataset_item

    @classmethod
    @transaction.atomic
    def delete(cls, dataset_item):
        version = EvaluationDatasetVersion.objects.select_for_update().get(pk=dataset_item.dataset_version_id)
        cls.ensure_draft(version)
        dataset_item.delete()
        cls.reset_quality_ack(version)

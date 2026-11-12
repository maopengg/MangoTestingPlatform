"""Dataset version creation and draft changes."""

from django.db import transaction
from django.utils import timezone
from src.apps.evaluation.exceptions import (
    EVALUATION_DATASET_VERSION_NOT_FOUND,
    EVALUATION_OBJECT_NOT_FOUND,
    EVALUATION_ITEM_SCHEMA_INVALID,
    EvaluationError,
)
from src.apps.evaluation.models import EvaluationDataset, EvaluationDatasetVersion, EvaluationDatasetItem
from src.apps.evaluation.selectors.scope import ensure_dataset_access
from src.apps.evaluation.services.dataset.dataset_item import EvaluationDatasetItemService
from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService


class EvaluationDatasetVersionService:
    @staticmethod
    @transaction.atomic
    def delete(version_id, user):
        from django.db.models.deletion import ProtectedError
        from src.apps.evaluation.services.assets.validation import invalid_config
        ensure_dataset_access(user)
        version = EvaluationDatasetVersion.objects.select_for_update().filter(pk=version_id).first()
        if version is None:
            raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
        EvaluationDatasetItemService.ensure_draft(version)
        try:
            version.delete()
        except ProtectedError as error:
            raise invalid_config("该草稿版本已被引用，不能删除") from error

    @classmethod
    @transaction.atomic
    def create(cls, *, dataset_id, values, user, source_version_id=None):
        dataset = EvaluationDataset.objects.select_for_update().filter(id=dataset_id).first()
        if dataset is None:
            raise EvaluationError(EVALUATION_OBJECT_NOT_FOUND)
        ensure_dataset_access(user)
        values = dict(values)
        source = None
        if source_version_id:
            source = dataset.versions.prefetch_related("items").filter(id=source_version_id).first()
            if source is None:
                raise EvaluationError(EVALUATION_DATASET_VERSION_NOT_FOUND)
            values.setdefault("schema_snapshot", source.schema_snapshot)
            values.setdefault("version_label", f"基于 V{source.version_no}")
        values["schema_snapshot"] = EvaluationVersionService.validate_dataset_schema(values.get("schema_snapshot") or {}).model_dump(mode="json")
        version = EvaluationDatasetVersion.objects.create(
            dataset=dataset, version_no=EvaluationVersionService.next_dataset_version(dataset), **values,
        )
        if source:
            EvaluationDatasetItem.objects.bulk_create([
                EvaluationDatasetItem(
                    dataset_version=version,
                    **{field: getattr(item, field) for field in (
                        "input_data", "expected_output", "context", "metadata",
                        "tags", "priority", "weight", "enabled", "content_hash", "grading_config", "scenario", "data_source",
                    )},
                ) for item in source.items.all()
            ], batch_size=500)
        return version

    @staticmethod
    @transaction.atomic
    def update(version, values):
        version = EvaluationDatasetVersion.objects.select_for_update().get(pk=version.pk)
        EvaluationDatasetItemService.ensure_draft(version)
        for field, value in values.items():
            setattr(version, field, value)
        version.schema_snapshot = EvaluationVersionService.validate_dataset_schema(version.schema_snapshot).model_dump(mode="json")
        version.save()
        EvaluationDatasetItemService.reset_quality_ack(version)
        return version

    @staticmethod
    @transaction.atomic
    def acknowledge_quality(version, user):
        version = EvaluationDatasetVersion.objects.select_for_update().get(pk=version.pk)
        EvaluationDatasetItemService.ensure_draft(version)
        report = EvaluationVersionService.dataset_quality(version)
        if report["errors"]:
            raise EvaluationError(EVALUATION_ITEM_SCHEMA_INVALID, value=(report["errors"][0]["message"],))
        version.quality_report = report
        version.quality_warning_acknowledged_by = user
        version.quality_warning_acknowledged_at = timezone.now()
        version.save(update_fields=[
            "quality_report", "quality_warning_acknowledged_by", "quality_warning_acknowledged_at", "update_time",
        ])
        return report

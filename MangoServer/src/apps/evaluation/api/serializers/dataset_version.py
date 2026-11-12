from rest_framework import serializers
from src.apps.evaluation.api.serializers.base import EvaluationModelSerializer
from src.apps.evaluation.models import EvaluationDatasetVersion
from src.apps.evaluation.selectors.version import item_count
from src.apps.evaluation.services.dataset.versioning import EvaluationVersionService


class DatasetVersionSerializer(EvaluationModelSerializer):
    item_count = serializers.SerializerMethodField()

    @staticmethod
    def get_item_count(obj):
        return item_count(obj)

    class Meta:
        model = EvaluationDatasetVersion
        fields = "__all__"
        read_only_fields = (
            "dataset", "version_no", "status", "item_count", "content_hash",
            "quality_report", "quality_warning_acknowledged_by", "quality_warning_acknowledged_at",
            "published_by", "published_at", "create_time", "update_time",
        )

    def validate_schema_snapshot(self, value):
        EvaluationVersionService.validate_dataset_schema(value)
        return value

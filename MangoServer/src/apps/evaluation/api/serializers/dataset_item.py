from src.apps.evaluation.api.serializers.base import EvaluationModelSerializer
from src.apps.evaluation.models import EvaluationDatasetItem


class DatasetItemSerializer(EvaluationModelSerializer):
    class Meta:
        model = EvaluationDatasetItem
        fields = "__all__"
        read_only_fields = ("dataset_version", "content_hash", "create_time", "update_time")

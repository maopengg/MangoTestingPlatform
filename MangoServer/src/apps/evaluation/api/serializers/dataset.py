from django.db.models import Count
from pydantic import ValidationError
from rest_framework import serializers
from src.apps.evaluation.api.serializers.base import EvaluationModelSerializer
from src.apps.evaluation.models import EvaluationDataset
from src.apps.evaluation.schemas.assets import EvaluationDatasetTaskTypes
from src.apps.evaluation.services.assets.validation import invalid_config
from src.apps.evaluation.selectors.version import current_version, with_current_version
from src.apps.evaluation.services.assets.validation import validate_dataset


class DatasetSerializer(EvaluationModelSerializer):
    task_type = serializers.JSONField(required=True)
    current_version = serializers.SerializerMethodField()
    version_count = serializers.IntegerField(read_only=True)
    item_count = serializers.IntegerField(read_only=True)

    @staticmethod
    def get_current_version(obj):
        return current_version(obj)

    class Meta:
        model = EvaluationDataset
        fields = "__all__"
        read_only_fields = ("current_version", "create_time", "update_time", "update_user")

    @staticmethod
    def setup_eager_loading(queryset):
        return with_current_version(queryset).select_related("owner").annotate(
            version_count=Count("versions", distinct=True),
            item_count=Count("versions__items", distinct=True),
        )

    def validate(self, attrs):
        return validate_dataset(attrs, self.instance)

    def validate_task_type(self, value):
        try:
            return EvaluationDatasetTaskTypes.model_validate({"task_type": value}).task_type
        except ValidationError as error:
            raise invalid_config(str(error)) from error

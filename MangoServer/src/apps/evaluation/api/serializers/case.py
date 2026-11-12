from rest_framework import serializers
from src.apps.evaluation.api.serializers.base import EVALUATION_DATETIME_FORMAT
from src.apps.evaluation.api.serializers.relation import ProjectRelationSerializer
from src.apps.evaluation.models import EvaluationCase
from src.apps.evaluation.services.assets.case import EvaluationCaseService
from src.apps.evaluation.formatters.case_description import case_description


class CaseSerializer(ProjectRelationSerializer):
    dataset_name = serializers.CharField(source="dataset_version.dataset.name", read_only=True, allow_null=True, default=None)
    dataset_id = serializers.IntegerField(source="dataset_version.dataset_id", read_only=True, allow_null=True, default=None)
    dataset_version_no = serializers.IntegerField(source="dataset_version.version_no", read_only=True, allow_null=True, default=None)
    dataset_input_variables = serializers.SerializerMethodField()
    dataset_workflow_summary = serializers.SerializerMethodField()

    @staticmethod
    def get_dataset_workflow_summary(obj):
        from src.apps.evaluation.schemas.dataset import EvaluationDatasetSchema
        if obj.dataset_version_id is None:
            return None
        workflow = EvaluationDatasetSchema.model_validate(obj.dataset_version.schema_snapshot).workflow
        return {"preparation": workflow.preparation.value, "sequence": workflow.sequence.value,
                "steps": [{"name": step.name, "stage": step.stage.value, "scope": step.scope.value} for step in workflow.steps]}

    @staticmethod
    def get_dataset_input_variables(obj):
        from src.apps.evaluation.schemas.dataset import EvaluationDatasetSchema
        if obj.dataset_version_id is None:
            return []
        return [item.model_dump() for item in EvaluationDatasetSchema.model_validate(obj.dataset_version.schema_snapshot).input_variables]

    class Meta:
        model = EvaluationCase
        fields = "__all__"
        read_only_fields = ("create_time", "update_time", "update_user")

    @staticmethod
    def setup_eager_loading(queryset):
        from src.apps.test_center.services.project.product_module import ProductModuleService
        return ProductModuleService.with_full_paths(queryset, "module").select_related("project_product", "module", "owner", "dataset_version__dataset")

    def validate(self, attrs):
        return EvaluationCaseService.normalize(attrs, self.instance)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["description"] = case_description(instance)
        return data

    def create(self, values):
        return EvaluationCaseService.save(values=values)

    def update(self, instance, values):
        return EvaluationCaseService.save(values=values, instance=instance)


class CaseListSerializer(CaseSerializer):
    target_type = serializers.CharField(source="config.target.type", read_only=True)
    latest_result = serializers.SerializerMethodField()

    class Meta(CaseSerializer.Meta):
        fields = ("id", "name", "description", "dataset_version", "dataset_name", "dataset_id", "dataset_version_no",
                  "project_product", "module", "project_product_data", "module_data", "owner_name", "status",
                  "target_type", "latest_result", "update_time")

    @staticmethod
    def get_latest_result(obj):
        if not getattr(obj, "latest_execution_id", None):
            return None
        summary = obj.latest_summary or {}
        finished_at = obj.latest_finished_at
        return {"id": obj.latest_execution_id, "status": obj.latest_status,
                "finished_at": serializers.DateTimeField(format=EVALUATION_DATETIME_FORMAT).to_representation(finished_at) if finished_at is not None else None,
                **{key: summary.get(key) for key in ("valid_rate", "average_score", "effect_pass_rate")}}

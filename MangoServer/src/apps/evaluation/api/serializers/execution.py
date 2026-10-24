from rest_framework import serializers
from src.apps.evaluation.api.serializers.base import EvaluationModelSerializer
from src.apps.evaluation.models import EvaluationCaseExecution


class CaseExecutionSerializer(EvaluationModelSerializer):
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = EvaluationCaseExecution
        fields = "__all__"



class CaseExecutionListSerializer(CaseExecutionSerializer):
    summary = serializers.SerializerMethodField()
    case_name = serializers.CharField(source="snapshot.case.name", read_only=True)

    class Meta:
        model = EvaluationCaseExecution
        fields = ("id", "execution_no", "case", "case_name", "dataset_version", "test_env", "status", "verdict",
                  "progress", "summary", "create_time", "started_at", "finished_at", "retry_of", "created_by_name")

    @staticmethod
    def get_summary(obj):
        summary = obj.summary or {}
        return {key: summary[key] for key in ("total", "item_count", "valid", "invalid", "passed", "failed", "warning", "valid_rate", "effect_pass_rate", "average_score") if key in summary}

from rest_framework import serializers
from src.apps.evaluation.api.serializers.base import EvaluationModelSerializer
from src.apps.evaluation.api.serializers.grade_result import GradeResultSerializer
from src.apps.evaluation.models import EvaluationItemResult


class ItemResultSerializer(EvaluationModelSerializer):
    dataset_item_id = serializers.IntegerField(read_only=True)
    grades = GradeResultSerializer(source="grade_results", many=True, read_only=True)

    class Meta:
        model = EvaluationItemResult
        fields = "__all__"


class ItemResultListSerializer(EvaluationModelSerializer):
    dataset_item_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = EvaluationItemResult
        fields = ("id", "execution", "dataset_item_id", "repeat_index", "execution_status", "grade_status", "verdict", "score", "details", "error_category")

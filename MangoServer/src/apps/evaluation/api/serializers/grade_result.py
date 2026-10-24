from src.apps.evaluation.api.serializers.base import EvaluationModelSerializer
from src.apps.evaluation.models import EvaluationGradeResult


class GradeResultSerializer(EvaluationModelSerializer):
    class Meta:
        model = EvaluationGradeResult
        fields = "__all__"

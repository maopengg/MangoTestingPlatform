from rest_framework.viewsets import ViewSet
from src.apps.evaluation.api.serializers.item_result import ItemResultSerializer, ItemResultListSerializer
from src.apps.evaluation.selectors.execution import get_execution
from src.apps.evaluation.api.views.support import paginate, request_user
from src.apps.evaluation.exceptions import EVALUATION_OBJECT_NOT_FOUND, EvaluationError
from src.apps.evaluation.models import EvaluationItemResult
from src.common.decorators.error_response import error_response
from src.common.responses import RESPONSE_MSG_0001, ResponseData


class ItemResultViews(ViewSet):
    model = EvaluationItemResult
    serializer_class = ItemResultSerializer

    @error_response("system")
    def list(self, request, case_id=None, execution_id=None):
        """获取评测数据项结果列表"""
        execution = get_execution(case_id, execution_id, request_user(request))
        queryset = execution.item_results.all()
        for field in ("verdict", "grade_status", "execution_status", "error_category"):
            if request.query_params.get(field + "__in"):
                queryset = queryset.filter(**{field + "__in": request.query_params[field + "__in"].split(",")})
        return ResponseData.success(RESPONSE_MSG_0001, paginate(request, queryset, ItemResultListSerializer))

    @error_response("system")
    def retrieve(self, request, case_id=None, execution_id=None, item_result_id=None):
        """获取评测数据项结果详情"""
        execution = get_execution(case_id, execution_id, request_user(request))
        record = execution.item_results.prefetch_related("grade_results").filter(pk=item_result_id).first()
        if record is None:
            raise EvaluationError(EVALUATION_OBJECT_NOT_FOUND)
        return ResponseData.success(RESPONSE_MSG_0001, ItemResultSerializer(record).data)

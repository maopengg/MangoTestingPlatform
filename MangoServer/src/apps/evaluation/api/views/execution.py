from rest_framework.viewsets import ViewSet
from src.apps.evaluation.api.serializers.execution import CaseExecutionSerializer, CaseExecutionListSerializer
from src.apps.evaluation.api.views.support import paginate, request_user
from src.apps.evaluation.models import EvaluationCaseExecution
from src.apps.evaluation.selectors.case import get_case
from src.apps.evaluation.selectors.execution import case_executions, get_execution
from src.apps.evaluation.services.execution import EvaluationCaseExecutionService
from src.common.decorators.error_response import error_response
from src.common.responses import RESPONSE_MSG_0001, RESPONSE_MSG_0005, RESPONSE_MSG_0082, ResponseData


class CaseExecutionViews(ViewSet):
    model = EvaluationCaseExecution
    serializer_class = CaseExecutionSerializer

    @error_response("system")
    def list(self, request, case_id=None):
        queryset = case_executions(case_id, request_user(request))
        for field in ("test_env", "status"):
            if request.query_params.get(field):
                queryset = queryset.filter(**{field: request.query_params[field]})
            if request.query_params.get(field + "__in"):
                queryset = queryset.filter(**{field + "__in": request.query_params[field + "__in"].split(",")})
        for field, lookup in (("started_after", "create_time__gte"), ("started_before", "create_time__lte")):
            if request.query_params.get(field):
                queryset = queryset.filter(**{lookup: request.query_params[field]})
        return ResponseData.success(RESPONSE_MSG_0001, paginate(request, queryset.order_by("-id"), CaseExecutionListSerializer))

    @error_response("system")
    def latest(self, request, case_id=None):
        queryset = case_executions(case_id, request_user(request))
        if request.query_params.get("test_env"):
            queryset = queryset.filter(test_env=request.query_params["test_env"])
        record = queryset.order_by("-id").first()
        return ResponseData.success(RESPONSE_MSG_0001, CaseExecutionSerializer(record).data if record else None)

    @error_response("system")
    def retrieve(self, request, case_id=None, execution_id=None):
        return ResponseData.success(RESPONSE_MSG_0001, CaseExecutionSerializer(get_execution(case_id, execution_id, request_user(request))).data)

    @error_response("system")
    def create(self, request, case_id=None):
        get_case(case_id, request_user(request))
        values = dict(request.data)
        values["case_id"] = case_id
        if request.headers.get("Idempotency-Key"):
            values["idempotency_key"] = request.headers["Idempotency-Key"]
        record = EvaluationCaseExecutionService.create(values, request_user(request))
        EvaluationCaseExecutionService.submit(record.id)
        return ResponseData.success(RESPONSE_MSG_0005, {"id": record.id, "execution_no": record.execution_no, "status": record.status})

    @error_response("system")
    def stop(self, request, case_id=None, execution_id=None):
        record = get_execution(case_id, execution_id, request_user(request))
        EvaluationCaseExecutionService.stop(record.id)
        return ResponseData.success(RESPONSE_MSG_0082)

    @error_response("system")
    def retry(self, request, case_id=None, execution_id=None):
        record = get_execution(case_id, execution_id, request_user(request))
        new_record = EvaluationCaseExecutionService.retry_failed(record.id, request_user(request), request.headers.get("Idempotency-Key"))
        EvaluationCaseExecutionService.submit(new_record.id)
        return ResponseData.success(RESPONSE_MSG_0005, {"id": new_record.id, "execution_no": new_record.execution_no, "status": new_record.status})

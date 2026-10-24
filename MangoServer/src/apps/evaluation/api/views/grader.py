from rest_framework.viewsets import ViewSet
from src.apps.evaluation.api.serializers.grader import GraderCatalogSerializer
from src.apps.evaluation.exceptions import EVALUATION_GRADER_UNAVAILABLE, EVALUATION_TARGET_ACCESS_DENIED, EvaluationError
from src.apps.evaluation.api.views.support import request_user
from src.apps.evaluation.services.graders import EvaluationGraderRegistry
from src.common.decorators.error_response import error_response
from src.common.responses import RESPONSE_MSG_0001, ResponseData


class GraderViews(ViewSet):
    serializer_class = GraderCatalogSerializer
    action_permission_map = {"list": "evaluation.grader", "retrieve": "evaluation.grader:detail", "dataset_catalog": "evaluation.dataset"}

    @error_response("system")
    def list(self, request):
        if request_user(request) is None:
            raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)
        rows = EvaluationGraderRegistry.catalog()
        if request.query_params.get("search"):
            text = request.query_params["search"].casefold()
            rows = [row for row in rows if text in row["name"].casefold() or text in row["grader_key"]]
        if request.query_params.get("category__in"):
            categories = set(request.query_params["category__in"].split(","))
            rows = [row for row in rows if row["category"] in categories]
        return ResponseData.success(RESPONSE_MSG_0001, {"items": rows, "count": len(rows)})

    @error_response("system")
    def retrieve(self, request, grader_key=None, version=None):
        if request_user(request) is None:
            raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)
        row = next((row for row in EvaluationGraderRegistry.catalog() if row["grader_key"] == grader_key and row["grader_version"] == version), None)
        if row is None:
            raise EvaluationError(EVALUATION_GRADER_UNAVAILABLE, value=(grader_key, version))
        return ResponseData.success(RESPONSE_MSG_0001, row)

    @error_response("system")
    def dataset_catalog(self, request):
        if request_user(request) is None:
            raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)
        return ResponseData.success(RESPONSE_MSG_0001, EvaluationGraderRegistry.catalog())

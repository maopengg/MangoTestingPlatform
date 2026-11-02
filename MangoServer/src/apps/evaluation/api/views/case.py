from rest_framework.viewsets import ViewSet
from src.apps.evaluation.api.serializers.case import CaseSerializer, CaseListSerializer
from src.apps.evaluation.api.views.support import request_user, paginate
from src.apps.evaluation.exceptions import EVALUATION_TARGET_ACCESS_DENIED, EvaluationError
from src.apps.evaluation.models import EvaluationCase
from src.apps.evaluation.selectors.case import get_case
from src.apps.evaluation.selectors.querysets import EvaluationQuerySelector
from src.apps.evaluation.selectors.scope import ensure_product_scope
from src.apps.evaluation.services.case import EvaluationCaseService
from src.apps.evaluation.services.graders import EvaluationGraderRegistry
from src.apps.user.services.permission import PermissionMenuService
from src.common.decorators.error_response import error_response
from src.common.responses import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0005, RESPONSE_MSG_0082, ResponseData


class CaseViews(ViewSet):
    model = EvaluationCase
    serializer_class = CaseSerializer
    page_permission_key = "evaluation.case"


    @error_response("system")
    def ai_profiles(self, request, pk=None):
        from src.apps.evaluation.services.ai import ai_options
        return ResponseData.success(RESPONSE_MSG_0001, ai_options(pk, request_user(request)))

    @error_response("system")
    def interfaces(self, request, pk=None):
        from pydantic import ValidationError
        from src.apps.evaluation.schemas.target_selection import EvaluationInterfaceSelection
        from src.apps.evaluation.selectors.target import interface_choices
        from src.apps.evaluation.services.validation import invalid_config
        try:
            query = EvaluationInterfaceSelection.model_validate(request.query_params.dict())
        except ValidationError as error:
            raise invalid_config("接口筛选参数格式错误") from error
        return ResponseData.success(RESPONSE_MSG_0001, interface_choices(
            pk, request_user(request), module_id=query.module_id, selected_id=query.selected_id,
            search=query.search, page=query.page, page_size=query.pageSize,
        ))

    @error_response("system")
    def list(self, request):
        queryset = EvaluationQuerySelector.cases(request_user(request), request.query_params.get("test_env"))
        for key in ("status", "project_product", "module"):
            raw = request.query_params.get(key + "__in")
            if raw:
                queryset = queryset.filter(**{key + "__in": raw.split(",")})
            elif request.query_params.get(key):
                queryset = queryset.filter(**{key: request.query_params[key]})
        if request.query_params.get("name"):
            queryset = queryset.filter(name__icontains=request.query_params["name"])
        if request.query_params.get("target_type__in"):
            queryset = queryset.filter(config__target__type__in=request.query_params["target_type__in"].split(","))
        return ResponseData.success(RESPONSE_MSG_0001, paginate(request, queryset, CaseListSerializer))

    @error_response("system")
    def retrieve(self, request, pk=None):
        return ResponseData.success(RESPONSE_MSG_0001, CaseSerializer(get_case(pk, request_user(request))).data)

    @error_response("system")
    def create(self, request):
        serializer = CaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data["project_product"]
        ensure_product_scope(request_user(request), product.id)
        case = serializer.save(update_user=request_user(request))
        return ResponseData.success(RESPONSE_MSG_0005, CaseSerializer(case).data)

    @error_response("system")
    def update(self, request):
        case = get_case(request.data.get("id"), request_user(request))
        serializer = CaseSerializer(case, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        case = serializer.save(update_user=request_user(request))
        return ResponseData.success(RESPONSE_MSG_0082, {"id": case.id, "status": case.status})

    @error_response("system")
    def delete(self, request):
        get_case(request.data.get("id"), request_user(request)).delete()
        return ResponseData.success(RESPONSE_MSG_0002)

    @error_response("system")
    def validate(self, request, pk=None):
        get_case(pk, request_user(request))
        return ResponseData.success(RESPONSE_MSG_0001, EvaluationCaseService.validate(pk, request_user(request)))

    @error_response("system")
    def grading_preview(self, request, pk=None):
        user = request_user(request)
        if not PermissionMenuService.is_effective_super_admin(user) and "evaluation.dataset:read" not in PermissionMenuService.permission_keys_for_user(user):
            raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)
        return ResponseData.success(RESPONSE_MSG_0001, EvaluationCaseService.grading_preview(get_case(pk, user), user))

    @error_response("system")
    def graders(self, request):
        if request_user(request) is None:
            raise EvaluationError(EVALUATION_TARGET_ACCESS_DENIED)
        return ResponseData.success(RESPONSE_MSG_0001, EvaluationGraderRegistry.catalog())

    @error_response("system")
    def copy(self, request, pk=None):
        case = EvaluationCaseService.copy(get_case(pk, request_user(request)), request_user(request))
        return ResponseData.success(RESPONSE_MSG_0005, CaseSerializer(case).data)

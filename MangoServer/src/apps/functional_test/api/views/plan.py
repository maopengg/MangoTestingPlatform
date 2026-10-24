# -*- coding: utf-8 -*-
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.functional_test.api.serializers.plan import (
    FunctionalTestPlanCaseSerializer,
    FunctionalTestPlanListSerializer,
    FunctionalTestPlanSerializer,
)
from src.apps.functional_test.enums import (
    FunctionalTestPlanStatusEnum,
)
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_PLAN_DELETE_NOT_ALLOWED,
    FUNCTIONAL_TEST_PLAN_DEFECT_DELETE_NOT_ALLOWED,
    FunctionalTestError,
)
from src.apps.functional_test.models import (
    FunctionalTestPlan,
    FunctionalTestPlanCase,
    ManualTestSuite,
)
from src.apps.functional_test.selectors.access_scope import filter_plan_by_data_scope
from src.apps.functional_test.services.execution import FunctionalTestExecutionService
from src.apps.test_center.services.product_module import ProductModuleService
from src.apps.user.services.permission import PermissionMenuService, ProjectProductScopeService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0002, RESPONSE_MSG_0005, RESPONSE_MSG_0082


class FunctionalTestPlanCRUD(ModelCRUD):
    model = FunctionalTestPlan
    queryset = FunctionalTestPlan.objects.all()
    serializer = FunctionalTestPlanSerializer
    serializer_class = FunctionalTestPlanListSerializer
    page_permission_key = "functional.plan"
    not_matching_str = ModelCRUD.not_matching_str + ["scope_type", "owner", "requirement_version", "iteration"]

    @error_response("system")
    def delete(self, request: Request):
        plan = filter_plan_by_data_scope(request, self.model.objects.all()).filter(
            id=request.query_params.get("id")
        ).first()
        if not plan:
            return ResponseData.success(RESPONSE_MSG_0005)
        if plan.status in (
                FunctionalTestPlanStatusEnum.COMPLETED.value,
                FunctionalTestPlanStatusEnum.CLOSED.value,
        ):
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_DELETE_NOT_ALLOWED)
        if FunctionalTestPlanCase.objects.filter(plan=plan, defect_relations__isnull=False).exists():
            raise FunctionalTestError(FUNCTIONAL_TEST_PLAN_DEFECT_DELETE_NOT_ALLOWED)
        plan.delete()
        return ResponseData.success(RESPONSE_MSG_0005)


class FunctionalTestPlanViews(ViewSet):
    action_permission_map = {
        "retrieve": "functional.plan:detail", "cases": "functional.plan:detail",
        "add_cases": "functional.plan:edit", "remove_cases": "functional.plan:edit",
        "update_case": "functional.plan:edit", "copy_cases": "functional.plan:copy",
        "requirement_options": "functional.plan:create", "start": "functional.plan:execute",
        "finish": "functional.plan:execute", "batch_result": "functional.plan:execute",
        "related": "functional.plan:detail",
    }

    @staticmethod
    def _user_id(request: Request):
        return ModelCRUD.get_operator_id(request)

    @staticmethod
    def _case_queryset(plan):
        return ProductModuleService.with_full_paths(plan.plan_cases.all(), "case__module").select_related(
            "case", "case__project_product", "case__project_product__project", "case__owner", "executor"
        ).prefetch_related("defect_relations__defect")

    @action(methods=["get"], detail=False)
    @error_response("system")
    def requirement_options(self, request: Request):
        queryset = ManualTestSuite.objects.select_related("requirement")
        user = getattr(getattr(request, "user", None), "user_obj", None)
        if user and not PermissionMenuService.is_effective_super_admin(
                user) and not ProjectProductScopeService.can_view_all_project_data(user):
            ids = ProjectProductScopeService.project_product_ids_for_user(user)
            queryset = queryset.filter(project_product_id__in=ids) if ids else queryset.none()
        if request.query_params.get("project_product"):
            queryset = queryset.filter(project_product_id=request.query_params["project_product"])
        data = [
            {
                "id": item.id,
                "requirement_id": item.requirement_id,
                "name": item.requirement_name or (item.requirement.name if item.requirement_id else "未命名需求"),
                "version_no": item.version_no,
                "project_product_id": item.project_product_id,
            }
            for item in queryset.order_by("requirement_name", "-version_no", "id")[:500]
        ]
        return ResponseData.success(RESPONSE_MSG_0001, data, len(data))

    @action(methods=["get"], detail=False)
    @error_response("system")
    def retrieve(self, request: Request):
        queryset = FunctionalTestPlanListSerializer.setup_eager_loading(
            filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all())
        )
        plan = queryset.get(id=request.query_params.get("id"))
        data = FunctionalTestPlanListSerializer(plan).data
        data["cases"] = FunctionalTestPlanCaseSerializer(self._case_queryset(plan), many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def related(self, request: Request):
        queryset = filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all())
        iteration_id = request.query_params.get("iteration_id")
        requirement_version_id = request.query_params.get("requirement_version_id")
        if iteration_id:
            queryset = queryset.filter(
                Q(iteration_id=iteration_id) | Q(requirement_version__iteration_ref_id=iteration_id)
            )
        elif requirement_version_id:
            queryset = queryset.filter(requirement_version_id=requirement_version_id)
        else:
            queryset = queryset.none()
        queryset = FunctionalTestPlanListSerializer.setup_eager_loading(queryset.distinct())
        data = FunctionalTestPlanListSerializer(queryset, many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data, len(data))

    @action(methods=["get"], detail=False)
    @error_response("system")
    def cases(self, request: Request):
        plan = filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all()).get(
            id=request.query_params.get("plan_id"))
        queryset = self._case_queryset(plan)
        return ResponseData.success(RESPONSE_MSG_0001, FunctionalTestPlanCaseSerializer(queryset, many=True).data,
                                    queryset.count())

    @action(methods=["post"], detail=False)
    @error_response("system")
    def add_cases(self, request: Request):
        filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all()).get(id=request.data.get("plan_id"))
        data = FunctionalTestExecutionService.add_plan_cases(int(request.data["plan_id"]),
                                                             request.data.get("case_ids") or [])
        return ResponseData.success(RESPONSE_MSG_0002, data)

    @action(methods=["delete"], detail=False)
    @error_response("system")
    def remove_cases(self, request: Request):
        filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all()).get(id=request.data.get("plan_id"))
        count = FunctionalTestExecutionService.remove_plan_cases(int(request.data["plan_id"]),
                                                                 request.data.get("plan_case_ids") or [])
        return ResponseData.success(RESPONSE_MSG_0005, {"count": count})

    @action(methods=["put"], detail=False)
    @error_response("system")
    def update_case(self, request: Request):
        scoped = FunctionalTestPlanCase.objects.filter(
            plan__in=filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all()))
        scoped.get(id=request.data.get("id"))
        item = FunctionalTestExecutionService.update_plan_case(int(request.data["id"]), request.data,
                                                               self._user_id(request))
        return ResponseData.success(RESPONSE_MSG_0082, FunctionalTestPlanCaseSerializer(item).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def copy_cases(self, request: Request):
        plans = filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all())
        plans.get(id=request.data.get("plan_id"))
        plans.get(id=request.data.get("source_plan_id"))
        data = FunctionalTestExecutionService.copy_plan_cases(int(request.data["plan_id"]),
                                                              int(request.data["source_plan_id"]))
        return ResponseData.success(RESPONSE_MSG_0002, data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def start(self, request: Request):
        filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all()).get(id=request.data.get("plan_id"))
        plan = FunctionalTestExecutionService.start_plan(
            int(request.data["plan_id"]),
            self._user_id(request),
            update_requirement_status=bool(request.data.get("update_requirement_status")),
        )
        return ResponseData.success(RESPONSE_MSG_0082, FunctionalTestPlanSerializer(plan).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def finish(self, request: Request):
        filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all()).get(id=request.data.get("plan_id"))
        plan = FunctionalTestExecutionService.finish_plan(int(request.data["plan_id"]), self._user_id(request))
        return ResponseData.success(RESPONSE_MSG_0082, FunctionalTestPlanSerializer(plan).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def batch_result(self, request: Request):
        filter_plan_by_data_scope(request, FunctionalTestPlan.objects.all()).get(id=request.data.get("plan_id"))
        items = FunctionalTestExecutionService.batch_result(
            int(request.data["plan_id"]), request.data.get("plan_case_ids") or [], request.data.get("result"),
            self._user_id(request)
        )
        return ResponseData.success(RESPONSE_MSG_0082, FunctionalTestPlanCaseSerializer(items, many=True).data)

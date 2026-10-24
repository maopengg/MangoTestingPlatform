# -*- coding: utf-8 -*-
from django.db.models import Count, Q
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.functional_test.api.serializers.defect import FunctionalTestDefectSerializer, \
    FunctionalTestDefectListSerializer
from src.apps.functional_test.enums import FunctionalTestDefectStatusEnum
from src.apps.functional_test.exceptions import (
    FUNCTIONAL_TEST_DEFECT_STATUS_EXECUTION_NOT_ALLOWED,
    FunctionalTestError,
)
from src.apps.functional_test.models import FunctionalTestDefect
from src.apps.functional_test.services.defect import FunctionalTestDefectService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0004,
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0158,
    RESPONSE_MSG_0210,
)


class FunctionalTestDefectCRUD(ModelCRUD):
    model = FunctionalTestDefect
    queryset = FunctionalTestDefect.objects.all()
    serializer = FunctionalTestDefectSerializer
    serializer_class = FunctionalTestDefectListSerializer
    page_permission_key = "functional.defect"
    not_matching_str = ModelCRUD.not_matching_str + [
        "module", "source_type", "defect_type", "severity", "priority", "status", "reporter", "assignee",
    ]

    @error_response("system")
    def get(self, request: Request):
        queryset = self.model.objects.all()
        keyword = (request.query_params.get("keyword") or request.query_params.get("title") or "").strip()
        if keyword:
            queryset = queryset.filter(Q(defect_no__icontains=keyword) | Q(title__icontains=keyword))
        exact_fields = (
            "project_product", "source_type", "defect_type", "severity", "priority",
            "status", "reporter", "assignee", "requirement_version",
        )
        for field in exact_fields:
            value = request.query_params.get(field)
            if value not in (None, ""):
                queryset = queryset.filter(**{
                    f"{field}_id"
                    if field in {"project_product", "reporter", "assignee", "requirement_version"}
                    else field: value,
                })
        module = request.query_params.get("module")
        if module:
            from src.apps.functional_test.services.suite import ManualTestSuiteService

            try:
                queryset = queryset.filter(module_id__in=ManualTestSuiteService.module_scope_ids(int(module)))
            except (TypeError, ValueError):
                queryset = queryset.none()
        source_plan = request.query_params.get("source_plan")
        if source_plan:
            queryset = queryset.filter(case_relations__plan_case__plan_id=source_plan)
        for query_key, lookup in (
                ("create_time_start", "create_time__date__gte"),
                ("create_time_end", "create_time__date__lte"),
                ("update_time_start", "update_time__date__gte"),
                ("update_time_end", "update_time__date__lte"),
        ):
            value = request.query_params.get(query_key)
            if value:
                queryset = queryset.filter(**{lookup: value})
        queryset = self.filter_queryset_by_data_scope(request, queryset.distinct())
        if request.query_params.get("pageSize") and request.query_params.get("page"):
            data, count = self.paging_list(
                request.query_params["pageSize"], request.query_params["page"],
                queryset, self.get_serializer_class(),
            )
            return ResponseData.success(RESPONSE_MSG_0001, data, count)
        serializer = self.get_serializer_class()
        queryset = serializer.setup_eager_loading(queryset)
        return ResponseData.success(RESPONSE_MSG_0001, serializer(queryset, many=True).data, queryset.count())

    @error_response("system")
    def post(self, request: Request):
        payload = dict(request.data)
        if not self.has_data_scope_permission(request, payload):
            return ResponseData.fail(RESPONSE_MSG_0210)
        serializer = self.serializer(data=payload)
        if not serializer.is_valid():
            return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)
        defect = FunctionalTestDefectService.create(serializer, payload, self.get_request_user_id(request))
        return ResponseData.success(RESPONSE_MSG_0002, self.serializer_class(defect).data)

    @error_response("system")
    def put(self, request: Request):
        defect = self.model.objects.filter(id=request.data.get("id")).first()
        if not defect:
            return ResponseData.fail(RESPONSE_MSG_0158)
        if not self.has_instance_data_scope_permission(request, defect):
            return ResponseData.fail(RESPONSE_MSG_0210)
        payload = dict(request.data)
        serializer = self.serializer(instance=defect, data=payload, partial=True)
        if not serializer.is_valid():
            return ResponseData.fail(RESPONSE_MSG_0004, serializer.errors)
        defect = FunctionalTestDefectService.update(serializer, payload, self.get_request_user_id(request))
        return ResponseData.success(RESPONSE_MSG_0082, self.serializer_class(defect).data)


class FunctionalTestDefectViews(ViewSet):
    action_permission_map = {
        "retrieve": "functional.defect:detail",
        "transition": "functional.defect:status",
        "stats": "functional.defect:detail",
        "related": "functional.defect:detail",
        "options": "functional.defect:detail",
        "bind_cases": "functional.defect:edit",
        "unbind_cases": "functional.defect:edit",
        "create_retest_plan": "functional.plan:create",
    }

    @staticmethod
    def _scoped(request: Request):
        return FunctionalTestDefectCRUD().filter_queryset_by_data_scope(
            request, FunctionalTestDefect.objects.all(),
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def retrieve(self, request: Request):
        queryset = FunctionalTestDefectListSerializer.setup_eager_loading(self._scoped(request))
        item = queryset.get(id=request.query_params.get("id"))
        return ResponseData.success(RESPONSE_MSG_0001, FunctionalTestDefectListSerializer(item).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def transition(self, request: Request):
        defect = self._scoped(request).get(id=request.data.get("id"))
        try:
            target_status = int(request.data.get("status"))
        except (TypeError, ValueError):

            raise FunctionalTestError(FUNCTIONAL_TEST_DEFECT_STATUS_EXECUTION_NOT_ALLOWED)
        item = FunctionalTestDefectService.transition(
            defect, target_status, request.data, ModelCRUD.get_operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0082, FunctionalTestDefectListSerializer(item).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def stats(self, request: Request):
        queryset = self._scoped(request)
        project_product = request.query_params.get("project_product")
        module = request.query_params.get("module")
        if project_product:
            queryset = queryset.filter(project_product_id=project_product)
        if module:
            from src.apps.functional_test.services.suite import ManualTestSuiteService

            try:
                queryset = queryset.filter(
                    module_id__in=ManualTestSuiteService.module_scope_ids(int(module)),
                )
            except (TypeError, ValueError):
                queryset = queryset.none()
        user_id = ModelCRUD.get_operator_id(request)
        open_filter = ~Q(status=FunctionalTestDefectStatusEnum.CLOSED.value)
        data = queryset.aggregate(
            open_count=Count("id", filter=open_filter),
            my_pending_count=Count("id", filter=open_filter & Q(assignee_id=user_id)),
            serious_count=Count("id", filter=open_filter & Q(severity__in=[0, 1])),
            resolved_pending_count=Count(
                "id", filter=Q(status=FunctionalTestDefectStatusEnum.RESOLVED.value),
            ),
        )
        return ResponseData.success(RESPONSE_MSG_0001, data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def related(self, request: Request):
        queryset = self._scoped(request)
        plan_id = request.query_params.get("plan_id")
        iteration_id = request.query_params.get("iteration_id")
        requirement_version_id = request.query_params.get("requirement_version_id")
        if plan_id:
            queryset = queryset.filter(case_relations__plan_case__plan_id=plan_id)
        elif iteration_id:
            queryset = queryset.filter(
                Q(case_relations__plan_case__plan__iteration_id=iteration_id)
                | Q(case_relations__plan_case__plan__requirement_version__iteration_ref_id=iteration_id)
                | Q(requirement_version__iteration_ref_id=iteration_id)
                | Q(case_relations__case__suite__iteration_ref_id=iteration_id)
            )
        elif requirement_version_id:
            queryset = queryset.filter(
                Q(case_relations__plan_case__plan__requirement_version_id=requirement_version_id)
                | Q(requirement_version_id=requirement_version_id)
                | Q(case_relations__case__suite_id=requirement_version_id),
            )
        else:
            queryset = queryset.none()
        queryset = FunctionalTestDefectListSerializer.setup_eager_loading(queryset.distinct())
        data = FunctionalTestDefectListSerializer(queryset, many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data, len(data))

    @action(methods=["get"], detail=False)
    @error_response("system")
    def options(self, request: Request):
        queryset = self._scoped(request).exclude(status=FunctionalTestDefectStatusEnum.CLOSED.value)
        if request.query_params.get("project_product"):
            queryset = queryset.filter(project_product_id=request.query_params["project_product"])
        keyword = (request.query_params.get("keyword") or "").strip()
        if keyword:
            queryset = queryset.filter(Q(defect_no__icontains=keyword) | Q(title__icontains=keyword))
        data = list(queryset.order_by("-id").values("id", "defect_no", "title", "status")[:100])
        return ResponseData.success(RESPONSE_MSG_0001, data, len(data))

    @action(methods=["post"], detail=False)
    @error_response("system")
    def bind_cases(self, request: Request):
        defect = self._scoped(request).get(id=request.data.get("id"))
        count = FunctionalTestDefectService.bind_relations(
            defect, request.data.get("case_ids"), request.data.get("plan_case_ids"),
        )
        return ResponseData.success(RESPONSE_MSG_0002, {"created_count": count})

    @action(methods=["delete"], detail=False)
    @error_response("system")
    def unbind_cases(self, request: Request):
        defect = self._scoped(request).get(id=request.data.get("id"))
        count = FunctionalTestDefectService.unbind_relations(
            defect,
            relation_ids=request.data.get("relation_ids"),
            case_ids=request.data.get("case_ids"),
            plan_case_ids=request.data.get("plan_case_ids"),
        )
        return ResponseData.success(RESPONSE_MSG_0005, {"deleted_count": count})

    @action(methods=["post"], detail=False)
    @error_response("system")
    def create_retest_plan(self, request: Request):
        defect = self._scoped(request).get(id=request.data.get("id"))
        plan = FunctionalTestDefectService.create_retest_plan(
            defect, request.data, ModelCRUD.get_operator_id(request),
        )
        from src.apps.functional_test.api.serializers.plan import FunctionalTestPlanListSerializer

        plan = FunctionalTestPlanListSerializer.setup_eager_loading(
            type(plan).objects.filter(id=plan.id)
        ).get()
        return ResponseData.success(RESPONSE_MSG_0002, FunctionalTestPlanListSerializer(plan).data)

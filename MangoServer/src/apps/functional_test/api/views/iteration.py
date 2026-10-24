# -*- coding: utf-8 -*-
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.functional_test.api.serializers.iteration import FunctionalTestIterationSerializer, \
    FunctionalTestIterationListSerializer
from src.apps.functional_test.enums import ManualTestSuiteStatusEnum
from src.apps.functional_test.models import (
    FunctionalTestIteration,
    FunctionalTestPlanCase,
    ManualTestCase,
    ManualTestSuite,
)
from src.apps.functional_test.services.iteration import FunctionalTestIterationService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0005, RESPONSE_MSG_0210


class FunctionalTestIterationCRUD(ModelCRUD):
    model = FunctionalTestIteration
    queryset = FunctionalTestIteration.objects.all()
    serializer = FunctionalTestIterationSerializer
    serializer_class = FunctionalTestIterationListSerializer
    page_permission_key = "functional.iteration"
    not_matching_str = ModelCRUD.not_matching_str + ["owner", "status"]

    @error_response("system")
    def delete(self, request: Request):
        instance = self.model.objects.filter(id=request.query_params.get("id")).first()
        if not instance:
            return ResponseData.success(RESPONSE_MSG_0005)
        if not self.has_instance_data_scope_permission(request, instance):
            return ResponseData.fail(RESPONSE_MSG_0210)
        FunctionalTestIterationService.delete_iteration(instance)
        return ResponseData.success(RESPONSE_MSG_0005)


class FunctionalTestIterationViews(ViewSet):
    action_permission_map = {
        "retrieve": "functional.iteration:detail",
        "gantt": "functional.iteration:detail",
        "board": "functional.iteration:detail",
        "cases": "functional.iteration:detail",
    }

    @staticmethod
    def _scoped(request: Request):
        return FunctionalTestIterationCRUD().filter_queryset_by_data_scope(
            request, FunctionalTestIteration.objects.all(),
        )

    @action(methods=["get"], detail=False)
    @error_response("system")
    def retrieve(self, request: Request):
        queryset = FunctionalTestIterationListSerializer.setup_eager_loading(self._scoped(request))
        item = queryset.get(id=request.query_params.get("id"))
        return ResponseData.success(RESPONSE_MSG_0001, FunctionalTestIterationListSerializer(item).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def gantt(self, request: Request):
        iteration = self._scoped(request).get(id=request.query_params.get("iteration_id"))
        suites = FunctionalTestIterationCRUD().filter_queryset_by_data_scope(
            request, ManualTestSuite.objects.all(),
        )
        owner_id = request.query_params.get("development_owner")
        if owner_id:
            suites = suites.filter(development_owner_id=owner_id)
        return ResponseData.success(RESPONSE_MSG_0001, FunctionalTestIterationService.gantt(iteration, suites))

    @action(methods=["get"], detail=False)
    @error_response("system")
    def board(self, request: Request):
        from src.apps.functional_test.api.serializers.suite import ManualTestSuiteSerializerC

        iteration = self._scoped(request).get(id=request.query_params.get("iteration_id"))
        suites = FunctionalTestIterationCRUD().filter_queryset_by_data_scope(
            request, ManualTestSuite.objects.filter(iteration_ref=iteration),
        )
        suites = ManualTestSuiteSerializerC.setup_eager_loading(suites).order_by(
            "priority", "planned_submit_date", "id",
        )
        serialized = ManualTestSuiteSerializerC(suites, many=True).data
        statuses = (
            ManualTestSuiteStatusEnum.UNSCHEDULED.value,
            ManualTestSuiteStatusEnum.SCHEDULED.value,
            ManualTestSuiteStatusEnum.PENDING_DEVELOPMENT.value,
            ManualTestSuiteStatusEnum.DEVELOPING.value,
            ManualTestSuiteStatusEnum.PENDING_TEST.value,
            ManualTestSuiteStatusEnum.TESTING.value,
            ManualTestSuiteStatusEnum.TEST_COMPLETED.value,
            ManualTestSuiteStatusEnum.PENDING_RELEASE.value,
            ManualTestSuiteStatusEnum.RELEASED.value,
        )
        return ResponseData.success(RESPONSE_MSG_0001, {
            "iteration_id": iteration.id,
            "columns": [
                {
                    "status": status,
                    "title": ManualTestSuiteStatusEnum.obj()[status],
                    "items": [item for item in serialized if item["status"] == status],
                }
                for status in statuses
            ],
            "cancelled_count": sum(
                item["status"] == ManualTestSuiteStatusEnum.CANCELLED.value for item in serialized
            ),
        })

    @action(methods=["get"], detail=False)
    @error_response("system")
    def cases(self, request: Request):
        from src.apps.functional_test.api.serializers.case import ManualTestCaseListSerializer
        from src.apps.functional_test.selectors.access_scope import filter_manual_case_by_data_scope

        iteration = self._scoped(request).get(id=request.query_params.get("iteration_id"))
        latest_result = (
            FunctionalTestPlanCase.objects.filter(case_id=OuterRef("pk"))
            .filter(Q(plan__iteration=iteration) | Q(plan__requirement_version__iteration_ref=iteration))
            .order_by("-execute_time", "-id")
            .values("result")[:1]
        )
        queryset = filter_manual_case_by_data_scope(
            request,
            ManualTestCase.objects.filter(
                Q(suite__iteration_ref=iteration)
                | Q(requirement_bindings__requirement_version__iteration_ref=iteration)
                | Q(plan_bindings__plan__iteration=iteration)
                | Q(plan_bindings__plan__requirement_version__iteration_ref=iteration)
            ).distinct(),
        ).annotate(
            iteration_plan_count=Count(
                "plan_bindings",
                filter=(Q(plan_bindings__plan__iteration=iteration) | Q(
                    plan_bindings__plan__requirement_version__iteration_ref=iteration)),
                distinct=True,
            ),
            iteration_open_defect_count=Count(
                "defect_relations__defect",
                filter=~Q(defect_relations__defect__status=4),
                distinct=True,
            ) + Count(
                "plan_bindings__defect_relations__defect",
                filter=(
                        (Q(plan_bindings__plan__iteration=iteration)
                         | Q(plan_bindings__plan__requirement_version__iteration_ref=iteration))
                        & ~Q(plan_bindings__defect_relations__defect__status=4)
                ),
                distinct=True,
            ),
            iteration_recent_result=Coalesce(Subquery(latest_result, output_field=IntegerField()), Value(0)),
        ).order_by("project_product_id", "module_id", "id")
        count = queryset.count()
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(500, max(1, int(request.query_params.get("pageSize", 50))))
        except (TypeError, ValueError):
            page, page_size = 1, 50
        cases = list(queryset[(page - 1) * page_size:page * page_size])
        hydrated = ManualTestCaseListSerializer.setup_eager_loading(
            ManualTestCase.objects.filter(id__in=[item.id for item in cases])
        )
        hydrated_map = {item.id: item for item in hydrated}
        data = ManualTestCaseListSerializer(
            [hydrated_map[item.id] for item in cases if item.id in hydrated_map], many=True,
        ).data
        annotation_map = {
            item.id: (item.iteration_plan_count, item.iteration_open_defect_count, item.iteration_recent_result)
            for item in cases
        }
        for row in data:
            row["iteration_plan_count"], row["iteration_open_defect_count"], row["iteration_recent_result"] = \
                annotation_map[row["id"]]
        return ResponseData.success(RESPONSE_MSG_0001, data, count)

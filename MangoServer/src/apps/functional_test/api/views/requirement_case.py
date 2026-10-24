# -*- coding: utf-8 -*-
from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.functional_test.api.serializers.case import ManualTestCaseListSerializer
from src.apps.functional_test.api.views.suite import ManualTestSuiteCRUD
from src.apps.functional_test.models import ManualTestCase, ManualTestSuite
from src.apps.functional_test.selectors.access_scope import filter_manual_case_by_data_scope
from src.apps.functional_test.services.requirement import FunctionalRequirementService
from src.common.decorators.error_response import error_response
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import RESPONSE_MSG_0001, RESPONSE_MSG_0082


class FunctionalRequirementCaseViews(ViewSet):
    action_permission_map = {
        "list": "functional.suite:detail",
        "bind": "functional.suite:edit",
        "unbind": "functional.suite:edit",
    }

    @staticmethod
    def _suite(request: Request, source: dict):
        return ManualTestSuiteCRUD().filter_queryset_by_data_scope(
            request, ManualTestSuite.objects.all(),
        ).get(id=source.get("requirement_version") or source.get("suite_id"))

    @action(methods=["get"], detail=False)
    @error_response("system")
    def list(self, request: Request):
        suite = self._suite(request, request.query_params)
        queryset = filter_manual_case_by_data_scope(
            request,
            ManualTestCase.objects.filter(
                Q(requirement_bindings__requirement_version=suite) | Q(suite=suite),
            ).distinct(),
        ).annotate(
            requirement_sort_order=Case(
                When(requirement_bindings__requirement_version=suite, then="requirement_bindings__sort_order"),
                default=Value(0),
                output_field=IntegerField(),
            ),
        ).order_by("requirement_sort_order", "id")
        queryset = ManualTestCaseListSerializer.setup_eager_loading(queryset)
        return ResponseData.success(RESPONSE_MSG_0001, ManualTestCaseListSerializer(queryset, many=True).data)

    @action(methods=["post"], detail=False)
    @error_response("system")
    def bind(self, request: Request):
        suite = self._suite(request, request.data)
        count = FunctionalRequirementService.bind_cases(
            suite, request.data.get("case_ids") or [], ModelCRUD.get_operator_id(request),
        )
        return ResponseData.success(RESPONSE_MSG_0082, {"bound_count": count})

    @action(methods=["delete"], detail=False)
    @error_response("system")
    def unbind(self, request: Request):
        suite = self._suite(request, request.data)
        count = FunctionalRequirementService.unbind_cases(suite, request.data.get("case_ids") or [])
        return ResponseData.success(RESPONSE_MSG_0082, {"unbound_count": count})

# -*- coding: utf-8 -*-
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.functional_test.api.serializers.automation_binding import (
    ManualTestAutomationBindingSerializer,
)
from src.apps.functional_test.enums import ManualTestRelationTypeEnum
from src.apps.functional_test.models import ManualTestAutomationBinding, ManualTestCase
from src.apps.functional_test.selectors.access_scope import filter_manual_case_by_data_scope
from src.apps.functional_test.services.automation import ManualAutomationService
from src.common.decorators.error_response import error_response
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0175,
)


class ManualTestAutomationViews(ViewSet):
    model = ManualTestAutomationBinding
    serializer_class = ManualTestAutomationBindingSerializer

    @action(methods=["post"], detail=False)
    @error_response("system")
    def bind(self, request: Request):
        case = filter_manual_case_by_data_scope(request, ManualTestCase.objects.all()).get(
            id=request.data.get("case_id"))
        binding = ManualAutomationService.bind(
            case,
            request.data.get("automation_type"),
            int(request.data.get("automation_case_id")),
            request.data.get("relation_type") or ManualTestRelationTypeEnum.BOUND.value,
            request.user.get("id") if isinstance(request.user, dict) else None,
        )
        return ResponseData.success(RESPONSE_MSG_0175, ManualTestAutomationBindingSerializer(instance=binding).data)

    @action(methods=["get"], detail=False)
    @error_response("system")
    def binding(self, request: Request):
        queryset = ManualTestAutomationBinding.objects.all()
        case_id = request.query_params.get("case_id")
        if case_id:
            case_queryset = filter_manual_case_by_data_scope(request, ManualTestCase.objects.filter(id=case_id))
            queryset = queryset.filter(manual_case_id__in=case_queryset.values_list('id', flat=True))
        else:
            case_queryset = filter_manual_case_by_data_scope(request, ManualTestCase.objects.all())
            queryset = queryset.filter(manual_case_id__in=case_queryset.values_list('id', flat=True))
        return ResponseData.success(RESPONSE_MSG_0001,
                                    ManualTestAutomationBindingSerializer(instance=queryset, many=True).data,
                                    queryset.count())

# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.views.api_case import ApiCaseSerializersC
from src.apps.auto_ui.views.ui_case import UiCaseSerializersC
from src.apps.functional_test.models import ManualTestAutomationBinding, ManualTestCase
from src.apps.functional_test.service.automation import ManualAutomationService
from src.common.enums.manual_test_enum import ManualTestRelationTypeEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class ManualTestAutomationBindingSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    api_case = ApiCaseSerializersC(read_only=True)
    ui_case = UiCaseSerializersC(read_only=True)

    class Meta:
        model = ManualTestAutomationBinding
        fields = "__all__"


class ManualTestAutomationBindingLiteSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)
    update_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", read_only=True)

    class Meta:
        model = ManualTestAutomationBinding
        fields = "__all__"


class ManualTestAutomationViews(ViewSet):
    model = ManualTestAutomationBinding
    serializer_class = ManualTestAutomationBindingSerializer

    @action(methods=["post"], detail=False)
    @error_response("system")
    def bind(self, request: Request):
        case = ManualTestCase.objects.get(id=request.data.get("case_id"))
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
            queryset = queryset.filter(manual_case_id=case_id)
        return ResponseData.success(RESPONSE_MSG_0001, ManualTestAutomationBindingSerializer(instance=queryset, many=True).data, queryset.count())

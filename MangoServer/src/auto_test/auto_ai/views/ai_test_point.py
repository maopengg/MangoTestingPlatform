# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 测试点视图
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_ai.models import AiTestPoint
from src.auto_test.auto_ai.views.ai_requirement import AiRequirementSerializers
from src.auto_test.auto_ai.views.ai_requirement_split import AiRequirementSplitSerializers
from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.enums.ai_enum import AiConfirmStatusEnum, AiRequirementStatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class AiTestPointSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = AiTestPoint
        fields = '__all__'


class AiTestPointSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    requirement = AiRequirementSerializers(read_only=True)
    requirement_split = AiRequirementSplitSerializers(read_only=True)

    class Meta:
        model = AiTestPoint
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
            'requirement',
            'requirement_split',
        )
        return queryset


class AiTestPointCRUD(ModelCRUD):
    model = AiTestPoint
    queryset = AiTestPoint.objects.all()
    serializer_class = AiTestPointSerializersC
    serializer = AiTestPointSerializers


class AiTestPointViews(ViewSet):
    model = AiTestPoint
    serializer_class = AiTestPointSerializers

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_confirm(self, request: Request):
        """批量确认/忽略测试点"""
        items = request.data.get('items', [])  # [{id, is_confirmed}, ...]
        for item in items:
            AiTestPoint.objects.filter(id=item['id']).update(
                is_confirmed=item['is_confirmed']
            )
        requirement_id = request.data.get('requirement_id')
        if requirement_id:
            confirmed_count = AiTestPoint.objects.filter(
                requirement_id=requirement_id,
                is_confirmed=AiConfirmStatusEnum.CONFIRMED.value
            ).count()
            if confirmed_count > 0:
                from src.auto_test.auto_ai.models import AiRequirement
                AiRequirement.objects.filter(id=requirement_id).update(
                    status=AiRequirementStatusEnum.WAIT_CONFIRM_POINTS.value
                )
        return ResponseData.success(RESPONSE_MSG_0163)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def by_requirement(self, request: Request):
        """按需求ID获取测试点列表"""
        requirement_id = request.query_params.get('requirement_id')
        qs = AiTestPoint.objects.filter(requirement_id=requirement_id)
        try:
            qs = AiTestPointSerializersC.setup_eager_loading(qs)
        except Exception:
            pass
        data = AiTestPointSerializersC(instance=qs, many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data=data, value=(qs.count(),))

    @action(methods=['get'], detail=False)
    @error_response('system')
    def by_split(self, request: Request):
        """按拆分ID获取测试点列表"""
        split_id = request.query_params.get('requirement_split_id')
        qs = AiTestPoint.objects.filter(requirement_split_id=split_id)
        try:
            qs = AiTestPointSerializersC.setup_eager_loading(qs)
        except Exception:
            pass
        data = AiTestPointSerializersC(instance=qs, many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data=data, value=(qs.count(),))

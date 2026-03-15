# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 需求拆分视图
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_ai.models import AiRequirementSplit
from src.auto_test.auto_ai.views.ai_requirement import AiRequirementSerializers
from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.enums.ai_enum import AiConfirmStatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class AiRequirementSplitSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = AiRequirementSplit
        fields = '__all__'


class AiRequirementSplitSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    requirement = AiRequirementSerializers(read_only=True)

    class Meta:
        model = AiRequirementSplit
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
            'requirement',
        )
        return queryset


class AiRequirementSplitCRUD(ModelCRUD):
    model = AiRequirementSplit
    queryset = AiRequirementSplit.objects.all()
    serializer_class = AiRequirementSplitSerializersC
    serializer = AiRequirementSplitSerializers


class AiRequirementSplitViews(ViewSet):
    model = AiRequirementSplit
    serializer_class = AiRequirementSplitSerializers

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_confirm(self, request: Request):
        """批量确认/忽略需求拆分项，确认后自动触发测试点生成"""
        items = request.data.get('items', [])  # [{id, is_confirmed}, ...]
        for item in items:
            AiRequirementSplit.objects.filter(id=item['id']).update(
                is_confirmed=item['is_confirmed']
            )
        # 检查是否有任意一条已确认，如果有则触发下一步
        requirement_id = request.data.get('requirement_id')
        if requirement_id:
            confirmed_count = AiRequirementSplit.objects.filter(
                requirement_id=requirement_id,
                is_confirmed=AiConfirmStatusEnum.CONFIRMED.value
            ).count()
            if confirmed_count > 0:
                from src.auto_test.auto_ai.models import AiRequirement
                from src.enums.ai_enum import AiRequirementStatusEnum
                AiRequirement.objects.filter(id=requirement_id).update(
                    status=AiRequirementStatusEnum.WAIT_CONFIRM_SPLIT.value
                )
        return ResponseData.success(RESPONSE_MSG_0162)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def by_requirement(self, request: Request):
        """按需求ID获取拆分列表"""
        requirement_id = request.query_params.get('requirement_id')
        qs = AiRequirementSplit.objects.filter(requirement_id=requirement_id)
        try:
            qs = AiRequirementSplitSerializersC.setup_eager_loading(qs)
        except Exception:
            pass
        data = AiRequirementSplitSerializersC(instance=qs, many=True).data
        return ResponseData.success(RESPONSE_MSG_0001, data=data, value=(qs.count(),))

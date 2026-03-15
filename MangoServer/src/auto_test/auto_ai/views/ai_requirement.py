# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: AI需求管理视图
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_ai.models import AiRequirement
from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_user.views.user import UserSerializers
from src.enums.ai_enum import AiRequirementStatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class AiRequirementSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = AiRequirement
        fields = '__all__'


class AiRequirementSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    create_user = UserSerializers(read_only=True)

    class Meta:
        model = AiRequirement
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
            'create_user',
        )
        return queryset


class AiRequirementCRUD(ModelCRUD):
    model = AiRequirement
    queryset = AiRequirement.objects.all()
    serializer_class = AiRequirementSerializersC
    serializer = AiRequirementSerializers


class AiRequirementViews(ViewSet):
    model = AiRequirement
    serializer_class = AiRequirementSerializers

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_name(self, request: Request):
        """获取需求名称列表（用于下拉选择）"""
        project_product_id = request.query_params.get('project_product')
        qs = AiRequirement.objects.filter(
            status=AiRequirementStatusEnum.COMPLETED.value
        )
        if project_product_id:
            qs = qs.filter(project_product_id=project_product_id)
        data = [{'key': i.id, 'title': i.name} for i in qs]
        return ResponseData.success(RESPONSE_MSG_0158, data=data)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def analyze(self, request: Request):
        """触发AI分析：拆分需求"""
        from src.auto_test.auto_ai.service.ai_service import AiService
        requirement_id = request.data.get('requirement_id')
        AiService.start_analyze(requirement_id, request.user.get('id'))
        return ResponseData.success(RESPONSE_MSG_0159)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def generate_points(self, request: Request):
        """触发AI生成测试点（需求拆分已确认后调用）"""
        from src.auto_test.auto_ai.service.ai_service import AiService
        requirement_id = request.data.get('requirement_id')
        AiService.start_generate_points(requirement_id)
        return ResponseData.success(RESPONSE_MSG_0160)

    @action(methods=['post'], detail=False)
    @error_response('system')
    def generate_cases(self, request: Request):
        """触发AI生成用例（测试点已确认后调用）"""
        from src.auto_test.auto_ai.service.ai_service import AiService
        requirement_id = request.data.get('requirement_id')
        AiService.start_generate_cases(requirement_id)
        return ResponseData.success(RESPONSE_MSG_0161)

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-10-25 17:40
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPageStepsResult
from PyAutoTest.auto_test.auto_user.views.product_module import ProductModuleSerializers
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.model_crud import ModelCRUD


class UiPageStepsResultSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiPageStepsResult
        fields = '__all__'


class UiPageStepsResultSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)

    class Meta:
        model = UiPageStepsResult
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project',
            'module',
            'case_people')
        return queryset


class UiPageStepsResultCRUD(ModelCRUD):
    model = UiPageStepsResult
    queryset = UiPageStepsResult.objects.all()
    serializer_class = UiPageStepsResultSerializersC
    serializer = UiPageStepsResultSerializers


class UiPageStepsResultViews(ViewSet):
    model = UiPageStepsResult
    serializer_class = UiPageStepsResultSerializers

    @action(methods=['get'], detail=False)

    @error_response('ui')
    def test(self, request: Request):
        pass

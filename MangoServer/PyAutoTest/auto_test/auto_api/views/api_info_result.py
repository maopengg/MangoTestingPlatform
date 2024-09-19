# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiInfoResult
from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseSerializers
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoSerializers
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import RESPONSE_MSG_0113

from PyAutoTest.tools.decorator.error_response import error_response


class ApiInfoResultSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiInfoResult
        fields = '__all__'


class ApiInfoResultSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case = ApiCaseSerializers(read_only=True)
    api_info = ApiInfoSerializers(read_only=True)

    class Meta:
        model = ApiInfoResult
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'case',
            'api_info')
        return queryset


class ApiInfoResultCRUD(ModelCRUD):
    model = ApiInfoResult
    queryset = ApiInfoResult.objects.all()
    serializer_class = ApiInfoResultSerializersC
    serializer = ApiInfoResultSerializers


class ApiInfoResultViews(ViewSet):
    model = ApiInfoResult
    serializer_class = ApiInfoResultSerializersC
    serializer = ApiInfoResultSerializers

    @action(methods=['get'], detail=False)
    @error_response('api')
    def get_case_result(self, request: Request):
        case_detailed_id = request.query_params.get('case_detailed_id')
        latest_result = ApiInfoResult.objects.filter(case_detailed_id=case_detailed_id).order_by('-id').first()
        return ResponseData.success(RESPONSE_MSG_0113, self.serializer(instance=latest_result, many=False).data)

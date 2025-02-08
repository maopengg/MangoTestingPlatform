# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
import json

from django.core.exceptions import FieldError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_api.models import ApiCaseSuiteDetailed, ApiInfo, ApiCase
from src.auto_test.auto_api.views.api_case import ApiCaseSerializers
from src.auto_test.auto_api.views.api_case_suite import ApiCaseSuiteSerializers
from src.auto_test.auto_api.views.api_info import ApiInfoSerializers
from src.tools.decorator.error_response import error_response
from src.tools.log_collector import log
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class ApiCaseSuiteDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCaseSuiteDetailed
        fields = '__all__'


class ApiCaseSuiteDetailedSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case_suite = ApiCaseSuiteSerializers(read_only=True)
    case = ApiCaseSerializers(read_only=True)

    class Meta:
        model = ApiCaseSuiteDetailed
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'case',
            'case_suite')
        return queryset


class ApiCaseSuiteDetailedCRUD(ModelCRUD):
    model = ApiCaseSuiteDetailed
    queryset = ApiCaseSuiteDetailed.objects.all()
    serializer_class = ApiCaseSuiteDetailedSerializersC
    serializer = ApiCaseSuiteDetailedSerializers

    # @error_response('api')
    # def get(self, request: Request):
    #     case_suite_id = request.query_params.get('case_suite_id')
    #     api_case_detailed = ApiCaseSuiteDetailed.objects.filter(case_suite_id=case_suite_id).order_by('case_sort')
    #     try:
    #         api_case_detailed = self.serializer_class.setup_eager_loading(api_case_detailed)
    #     except FieldError:
    #         pass
    #     data = self.serializer_class(instance=api_case_detailed, many=True).data
    #     return ResponseData.success(RESPONSE_MSG_0010, data)

    def callback(self, _id):
        """
        排序
        @param _id: 用例ID
        @return:
        """
        data = {'id': _id, 'case_flow': ''}
        run = self.model.objects.filter(case=_id).order_by('case_sort')
        for i in run:
            data['case_flow'] += '->'
            if i.api_info:
                data['case_flow'] += i.api_info.name
        from src.auto_test.auto_api.views.api_case_suite import ApiCaseSuiteCRUD
        ApiCaseSuiteCRUD.inside_put(ApiCase.objects.get(id=_id).id, data)


class ApiCaseSuiteDetailedViews(ViewSet):
    model = ApiCaseSuiteDetailed
    serializer_class = ApiCaseSuiteDetailedSerializers

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_case_sort(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        case_suite_id = None
        for i in request.data.get('case_sort_list'):
            obj = self.model.objects.get(id=i['id'])
            obj.case_sort = i['case_sort']
            case_suite_id = obj.case_suite.id
            obj.save()
        ApiCaseSuiteDetailedCRUD().callback(case_suite_id)
        return ResponseData.success(RESPONSE_MSG_0013, )

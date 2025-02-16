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
from src.auto_test.auto_api.models import ApiCaseDetailedParameter

from src.auto_test.auto_api.models import ApiCaseDetailed, ApiInfo, ApiCase, ApiCaseDetailedParameter
from src.auto_test.auto_api.views.api_case import ApiCaseSerializers
from src.auto_test.auto_api.views.api_info import ApiInfoSerializers
from src.exceptions import ToolsError
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *

class ApiCaseDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCaseDetailed
        fields = '__all__'


class ApiCaseDetailedSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case = ApiCaseSerializers(read_only=True)
    api_info = ApiInfoSerializers(read_only=True)

    class Meta:
        model = ApiCaseDetailed
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'case',
            'api_info')
        return queryset


class ApiCaseDetailedCRUD(ModelCRUD):
    model = ApiCaseDetailed
    queryset = ApiCaseDetailed.objects.all()
    serializer_class = ApiCaseDetailedSerializersC
    serializer = ApiCaseDetailedSerializers

    @error_response('api')
    def get(self, request: Request):
        case_id = request.query_params.get('case_id')
        api_info_id = request.query_params.get('api_info_id')
        if api_info_id:
            api_case_detailed = ApiCaseDetailed\
                .objects\
                .filter(case=case_id, api_info=api_info_id)\
                .order_by('case_sort')
        else:
            api_case_detailed = ApiCaseDetailed\
                .objects\
                .filter(case=case_id)\
                .order_by('case_sort')

        try:
            api_case_detailed = self.serializer_class.setup_eager_loading(api_case_detailed)
        except FieldError:
            pass
        data = self.serializer_class(instance=api_case_detailed, many=True).data
        # from src.auto_test.auto_api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD
        # for i in data:
        #     api_case_detailed_parameter = ApiCaseDetailedParameter.objects.filter(case_detailed_id=i.get('id'))
        #     parameter_dict = ApiCaseDetailedParameterCRUD.serializer(api_case_detailed_parameter, many=True).data
        #     i['parameter'] = parameter_dict
        return ResponseData.success(RESPONSE_MSG_0010, data)

    @error_response('api')
    def post(self, request: Request):
        data = request.data
        if data['module']:
            del data['module']
        api_info_obj = ApiInfo.objects.get(id=request.data.get('api_info'))
        data['url'] = api_info_obj.url
        data['params'] = api_info_obj.params
        data['data'] = api_info_obj.data
        data['json'] = api_info_obj.json
        data['file'] = api_info_obj.file
        from src.auto_test.auto_api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD
        return_data = self.inside_post(data)
        data['case_detailed'] = return_data['id']
        data['name'] = api_info_obj.name
        try:
            ApiCaseDetailedParameterCRUD.inside_post(data)
        except ToolsError as error:
            self.model.objects.get(id=return_data['id']).delete()
            return ResponseData.fail((error.code, error.msg))

        self.asynchronous_callback(request.data.get('parent_id'))
        return ResponseData.success(RESPONSE_MSG_0011, return_data)

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
        if data['case_flow'] == '':
            data['case_flow'] = None
        from src.auto_test.auto_api.views.api_case import ApiCaseCRUD
        ApiCaseCRUD.inside_put(ApiCase.objects.get(id=_id).id, data)


class ApiCaseDetailedViews(ViewSet):
    model = ApiCaseDetailed
    serializer_class = ApiCaseDetailedSerializers

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_case_sort(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        case_id = None
        for i in request.data.get('case_sort_list'):
            obj = self.model.objects.get(id=i['id'])
            obj.case_sort = i['case_sort']
            case_id = obj.case.id
            obj.save()
        ApiCaseDetailedCRUD().callback(case_id)
        return ResponseData.success(RESPONSE_MSG_0013, )

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_refresh_api_info(self, request: Request):
        model = self.model.objects.get(id=request.data.get('id'))
        api_info_obj = ApiInfo.objects.get(id=model.api_info.id)

        for i in ApiCaseDetailedParameter.objects.filter(case_detailed_id=model.id):
            i.params = api_info_obj.params
            i.data = api_info_obj.data
            i.json = api_info_obj.json
            i.file = api_info_obj.file
            # i.header = []
            i.save()

        return ResponseData.success(RESPONSE_MSG_0014)
        # return ResponseData.fail(RESPONSE_MSG_0015, serializer.errors)

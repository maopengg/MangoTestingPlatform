# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
import json

from django.core.exceptions import FieldError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCaseDetailed, ApiInfo, ApiCase
from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseSerializers
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoSerializers
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.log_collector import log
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


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
            api_case_detailed = ApiCaseDetailed.objects.filter(case=case_id, api_info=api_info_id).order_by(
                'case_sort')
        else:
            api_case_detailed = ApiCaseDetailed.objects.filter(case=case_id).order_by('case_sort')

        try:
            api_case_detailed = self.serializer_class.setup_eager_loading(api_case_detailed)
        except FieldError:
            pass
        data = self.serializer_class(instance=api_case_detailed, many=True).data
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
        data['header'] = json.dumps(api_info_obj.header) if api_info_obj.header else None

        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            self.asynchronous_callback(request)
            return ResponseData.success(RESPONSE_MSG_0011, serializer.data)
        else:
            log.api.error(f'执行保存时报错，请检查！数据：{request.data}, 报错信息：{json.dumps(serializer.errors)}')
            return ResponseData.fail(RESPONSE_MSG_0012, serializer.errors)

    def callback(self, _id):
        """
        排序
        @param _id: 用例ID
        @return:
        """
        data = {'id': _id, 'case_flow': '', 'name': ''}
        run = self.model.objects.filter(case=_id).order_by('case_sort')
        for i in run:
            data['case_flow'] += '->'
            if i.api_info:
                data['case_flow'] += i.api_info.name
        data['name'] = run[0].case.name
        from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseCRUD
        api_case = ApiCaseCRUD()
        res = api_case.serializer(instance=ApiCase.objects.get(id=_id), data=data)
        if res.is_valid():
            res.save()
        else:
            log.api.error(f'保存用例执行顺序报错！，报错结果：{str(res.errors)}')


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
        print(case_id)
        ApiCaseDetailedCRUD().callback(case_id)
        return ResponseData.success(RESPONSE_MSG_0013, )

    @action(methods=['put'], detail=False)
    @error_response('api')
    def put_refresh_api_info(self, request: Request):
        api_info_detailed_obj = self.model.objects.get(id=request.data.get('id'))
        api_info_obj = ApiInfo.objects.get(id=api_info_detailed_obj.api_info.id)
        data = {
            'url': api_info_obj.url,
            'params': api_info_obj.params,
            'data': api_info_obj.data,
            'json': api_info_obj.json,
            'file': api_info_obj.file,
            'header': json.dumps(api_info_obj.header) if api_info_obj.header else None
        }
        serializer = self.serializer_class(
            instance=api_info_detailed_obj,
            data=data
        )
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(RESPONSE_MSG_0014, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0015, serializer.errors)

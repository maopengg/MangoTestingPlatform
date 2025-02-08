# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_api.models import ApiCaseSuite
from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_user.views.user import UserSerializers
from src.tools.decorator.error_response import error_response
from src.tools.view import ResponseData, RESPONSE_MSG_0111
from src.tools.view.model_crud import ModelCRUD


class ApiCaseSuiteSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCaseSuite
        fields = '__all__'


class ApiCaseSuiteSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    case_people = UserSerializers(read_only=True)
    module = ProductModuleSerializers(read_only=True)

    class Meta:
        model = ApiCaseSuite
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'case_people',
            'module')
        return queryset


class ApiCaseSuiteCRUD(ModelCRUD):
    model = ApiCaseSuite
    queryset = ApiCaseSuite.objects.all()
    serializer_class = ApiCaseSuiteSerializersC
    serializer = ApiCaseSuiteSerializers


class ApiCaseSuiteViews(ViewSet):
    model = ApiCaseSuite
    serializer_class = ApiCaseSuiteSerializers

    @action(methods=['get'], detail=False)
    @error_response('api')
    def api_test_case_suite(self, request: Request):
        case_suite_id = request.query_params.get('case_suite_id')
        test_env = request.query_params.get('test_env')
        print(case_suite_id, test_env)
        return ResponseData.success(RESPONSE_MSG_0111)

    @action(methods=['post'], detail=False)
    @error_response('api')
    def api_test_case_suite_batch(self, request: Request):
        case_suite_id_list = request.query_params.get('case_suite_id_list')
        test_env = request.query_params.get('test_env')
        print(case_suite_id_list, test_env)
        return ResponseData.success(RESPONSE_MSG_0111)

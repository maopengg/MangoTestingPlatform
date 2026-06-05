# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
from django.db import transaction
from django.forms import model_to_dict
from django.db.models import Q
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_api.models import ApiCase
from src.apps.auto_system.models import ProjectProduct
from src.apps.auto_api.schemas.case_schema import (
    ApiKeyValueItem,
    ApiParametrizeSuite,
    validate_int_list,
    validate_model_list,
)
from src.apps.auto_api.service.test_case.test_case import TestCase
from src.apps.auto_system.service.tasks.add_tasks import AddTasks
from src.apps.auto_system.views.product_module import ProductModuleSerializers
from src.apps.auto_system.views.project_product import ProjectProductSerializersC
from src.apps.auto_user.views.user import UserSerializers
from src.common.enums.tools_enum import StatusEnum, TestCaseTypeEnum
from src.common.models.api_model import ApiCaseResultModel
from src.common.tools.decorator.error_response import error_response
from src.common.tools.log_collector import log
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class ApiCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCase
        fields = '__all__'

    def validate_parametrize(self, value):
        return validate_model_list(value, ApiParametrizeSuite, '参数化')

    def validate_front_custom(self, value):
        return validate_model_list(value, ApiKeyValueItem, '前置方法')

    def validate_front_sql(self, value):
        return validate_model_list(value, ApiKeyValueItem, '前置sql')

    def validate_front_headers(self, value):
        return validate_int_list(value, '前置请求头')

    def validate_posterior_sql(self, value):
        return validate_model_list(value, ApiKeyValueItem, '后置sql')


class ApiCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    case_people = UserSerializers(read_only=True)
    module = ProductModuleSerializers(read_only=True)

    class Meta:
        model = ApiCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'case_people',
            'module')
        return queryset


class ApiCaseCRUD(ModelCRUD):
    model = ApiCase
    queryset = ApiCase.objects.all()
    serializer_class = ApiCaseSerializersC
    serializer = ApiCaseSerializers

    @error_response('api')
    def get(self, request: Request):
        query_dict = {}
        scenario_tags = request.query_params.getlist('scenario_tags[]')
        scenario_tags.extend(request.query_params.getlist('scenario_tags'))
        scenario_tags = [
            int(item)
            for item in scenario_tags
            if str(item).strip() not in ['', 'null', 'undefined']
        ]

        for key, value_list in dict(request.query_params.lists()).items():
            if key in ['scenario_tags', 'scenario_tags[]', 'page', 'pageSize']:
                continue
            value = value_list[0]
            if value in [None, '', 'null', 'undefined']:
                continue
            if key in self.not_matching_str or key in ['level', 'scenario_layer', 'scenario_type']:
                query_dict[key] = value
            elif 'id' not in key:
                query_dict[f'{key}__contains'] = value
            else:
                query_dict[key] = value

        project_id = request.headers.get('Project', None)
        if query_dict.get('project_product') is None and project_id:
            query_dict['project_product_id__in'] = ProjectProduct.objects.filter(
                project_id=project_id
            ).values_list('id', flat=True)

        queryset = ApiCase.objects.filter(**query_dict)
        if scenario_tags:
            tag_query = Q()
            for tag in scenario_tags:
                tag_query |= Q(scenario_tags__contains=[tag])
            queryset = queryset.filter(tag_query)

        paging = request.query_params.get("pageSize") and request.query_params.get("page")
        if paging:
            data_list, count = self.paging_list(
                request.query_params.get("pageSize"),
                request.query_params.get("page"),
                queryset,
                self.get_serializer_class()
            )
            return ResponseData.success(RESPONSE_MSG_0001, data_list, count)

        serializer = self.get_serializer_class()
        queryset = serializer.setup_eager_loading(queryset)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            serializer(instance=queryset, many=True).data,
            queryset.count()
        )


class ApiCaseViews(ViewSet):
    model = ApiCase
    serializer_class = ApiCaseSerializers

    @action(methods=['get'], detail=False)
    @error_response('api')
    def api_test_case(self, request: Request):
        api_case_run = TestCase(
            user_id=request.user.get('id'),
            test_env=request.query_params.get('test_env'),
            case_id=request.query_params.get('case_id'),
        )
        test_result: ApiCaseResultModel = api_case_run.test_case(
            request.query_params.get('case_sort')
        )
        if StatusEnum.SUCCESS.value != test_result.status:
            return ResponseData.fail((300, test_result.error_message), test_result.model_dump())
        return ResponseData.success(RESPONSE_MSG_0112, test_result.model_dump())

    @action(methods=['post'], detail=False)
    @error_response('api')
    def api_test_case_batch(self, request: Request):
        case_id_list = request.data.get('case_id_list')
        case_project_product = None
        case_project = None
        for i in case_id_list:
            if case_project is None:
                case_project_product = ApiCase.objects.get(id=i).project_product.id
                case_project = ApiCase.objects.get(id=i).project_product.project.id
            else:
                if case_project != ApiCase.objects.get(id=i).project_product.project.id:
                    return ResponseData.fail(RESPONSE_MSG_0128, )
        add_tasks = AddTasks(
            project_product=case_project_product,
            test_env=request.data.get('test_env'),
            is_notice=StatusEnum.FAIL.value,
            user_id=request.user['id'],
        )
        for case_id in case_id_list:
            add_tasks.add_test_suite_details(case_id, TestCaseTypeEnum.API)
        return ResponseData.success(RESPONSE_MSG_0111)


    @action(methods=['POST'], detail=False)
    @error_response('api')
    @transaction.atomic
    def copy_case(self, request: Request):
        from src.apps.auto_api.models import ApiCaseDetailed, ApiCaseDetailedParameter
        from src.apps.auto_data_factory.models import DataFactoryCaseConfig
        from src.common.enums.data_factory_enum import DataFactoryCaseSourceTypeEnum
        from src.apps.auto_api.views.api_case_data_factory import ApiCaseDataFactoryCRUD
        from src.apps.auto_data_factory.views.case_config import DataFactoryCaseConfigCRUD
        from src.apps.auto_api.views.api_case_detailed import ApiCaseDetailedCRUD
        from src.apps.auto_api.views.api_case_detailed_parameter import ApiCaseDetailedParameterCRUD
        case_id = request.data.get('case_id')
        case_obj = ApiCase.objects.get(id=case_id)
        case_obj = model_to_dict(case_obj)
        case_id = case_obj['id']
        case_obj['status'] = StatusEnum.FAIL.value
        case_obj['name'] = '(副本)' + case_obj.get('name')
        del case_obj['id']
        serializer = self.serializer_class(data=case_obj)
        if serializer.is_valid():
            serializer.save()
            api_case_detailed_obj = ApiCaseDetailed.objects.filter(case=case_id)
            for i in api_case_detailed_obj:
                api_case_detailed = model_to_dict(i)
                del api_case_detailed['id']
                api_case_detailed['case'] = serializer.data['id']
                res_case_de = ApiCaseDetailedCRUD.inside_post(api_case_detailed)
                for p in ApiCaseDetailedParameter.objects.filter(case_detailed_id=i.id):
                    parameter = model_to_dict(p)
                    source_parameter_id = parameter['id']
                    del parameter['id']
                    parameter['case_detailed'] = res_case_de.get('id')
                    res_parameter = ApiCaseDetailedParameterCRUD.inside_post(parameter)
                    for factory_config in DataFactoryCaseConfig.objects.filter(
                            source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
                            source_id=source_parameter_id,
                    ):
                        data_factory = model_to_dict(factory_config)
                        del data_factory['id']
                        data_factory['source_id'] = res_parameter.get('id')
                        data_factory['source_type'] = DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value
                        DataFactoryCaseConfigCRUD.inside_post(data_factory)
            for factory_config in DataFactoryCaseConfig.objects.filter(
                    source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
                    source_id=case_id,
            ):
                data_factory = model_to_dict(factory_config)
                del data_factory['id']
                data_factory['case'] = serializer.data['id']
                data_factory.pop('source_id', None)
                data_factory.pop('source_type', None)
                ApiCaseDataFactoryCRUD.inside_post(data_factory)
            return ResponseData.success(RESPONSE_MSG_0009, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0008, serializer.errors)

    @action(methods=['GET'], detail=False)
    @error_response('api')
    def case_name(self, request: Request):
        res = self.model.objects \
            .filter(module_id=request.query_params.get('module_id')) \
            .values_list('id', 'name')
        return ResponseData.fail(RESPONSE_MSG_0023, [{'key': _id, 'title': name} for _id, name in res])

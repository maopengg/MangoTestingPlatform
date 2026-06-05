# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from django.db.models import Q
from django.forms import model_to_dict
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.auto_system.service.tasks.add_tasks import AddTasks
from src.apps.auto_system.models import ProjectProduct
from src.apps.auto_system.views.product_module import ProductModuleSerializers
from src.apps.auto_system.views.project_product import ProjectProductSerializersC
from src.apps.auto_api.schemas.case_schema import validate_int_list
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.service.test_case.test_case import TestCase
from src.apps.auto_user.views.user import UserSerializers
from src.common.enums.system_enum import ClientNameEnum
from src.common.enums.tools_enum import StatusEnum, TestCaseTypeEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class UiCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiCase
        fields = '__all__'

    def validate_scenario_tags(self, value):
        return validate_int_list(value, '场景标签')


class UiCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)

    class Meta:
        model = UiCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
            'case_people')
        return queryset


class UiCaseCRUD(ModelCRUD):
    model = UiCase
    queryset = UiCase.objects.all()
    serializer_class = UiCaseSerializersC
    serializer = UiCaseSerializers

    @error_response('ui')
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

        queryset = UiCase.objects.filter(**query_dict)
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


class UiCaseViews(ViewSet):
    model = UiCase
    serializer_class = UiCaseSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def ui_test_case(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """

        case_model = TestCase(
            request.user['id'],
            request.user['username'],
            request.query_params.get("test_env"),
            is_send=True
        ).test_case(int(request.query_params.get("case_id")))
        return ResponseData.success(RESPONSE_MSG_0064, data=case_model.model_dump(),
                                    value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['post'], detail=False)
    @error_response('ui')
    def ui_test_case_batch(self, request: Request):
        """
        批量执行多个用例组
        @param request:
        @return:
        """
        case_id_list = request.data.get('case_id_list')
        case_project_product = None
        case_project = None
        for i in case_id_list:
            if case_project is None:
                case_project_product = UiCase.objects.get(id=i).project_product.id
                case_project = UiCase.objects.get(id=i).project_product.project.id
            else:
                if case_project != UiCase.objects.get(id=i).project_product.project.id:
                    return ResponseData.fail(RESPONSE_MSG_0128, )
        add_tasks = AddTasks(
            project_product=case_project_product,
            test_env=request.data.get("test_env"),
            is_notice=StatusEnum.FAIL.value,
            user_id=request.user['id'],
        )
        for case_id in case_id_list:
            add_tasks.add_test_suite_details(case_id, TestCaseTypeEnum.UI)
        return ResponseData.success(RESPONSE_MSG_0074, value=(ClientNameEnum.DRIVER.value,))

    @action(methods=['POST'], detail=False)
    @error_response('ui')
    def cody_case(self, request: Request):
        from src.apps.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailedSerializers
        from src.apps.auto_ui.views.ui_case_steps_detailed import UiCaseStepsDetailed
        case_id = request.data.get('case_id')
        case_obj = UiCase.objects.get(id=case_id)
        case_obj = model_to_dict(case_obj)
        case_id = case_obj['id']
        case_obj['name'] = '(副本)' + case_obj['name']
        case_obj['status'] = StatusEnum.FAIL.value
        del case_obj['id']
        serializer = self.serializer_class(data=case_obj)
        if serializer.is_valid():
            serializer.save()
            ui_case_steps_detailed_obj = UiCaseStepsDetailed.objects.filter(case=case_id)
            for i in ui_case_steps_detailed_obj:
                case_steps_detailed = model_to_dict(i)
                del case_steps_detailed['id']
                case_steps_detailed['case'] = serializer.data['id']
                ui_case_steps_serializer = UiCaseStepsDetailedSerializers(data=case_steps_detailed)
                if ui_case_steps_serializer.is_valid():
                    ui_case_steps_serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0075, ui_case_steps_serializer.errors)
            return ResponseData.success(RESPONSE_MSG_0073, serializer.data)
        else:
            return ResponseData.fail(RESPONSE_MSG_0075, serializer.errors)

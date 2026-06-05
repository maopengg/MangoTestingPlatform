# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-03-25 13:25
# @Author : 毛鹏

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from django.db.models import Q

from src.apps.auto_api.models import ApiCase
from src.apps.auto_api.views.api_case import ApiCaseSerializersC
from src.apps.auto_pytest.models import PytestCase
from src.apps.auto_pytest.views.pytest_case import PytestCaseSerializersC
from src.apps.auto_system.models import TasksDetails
from src.apps.auto_system.views.tasks import TasksSerializers
from src.apps.auto_ui.models import UiCase
from src.apps.auto_ui.views.ui_case import UiCaseSerializersC
from src.common.enums.tools_enum import TestCaseTypeEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class TasksDetailsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TasksDetails
        fields = '__all__'


class TasksDetailsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    task = TasksSerializers(read_only=True)
    ui_case = UiCaseSerializersC(read_only=True)
    api_case = ApiCaseSerializersC(read_only=True)
    pytest_case = PytestCaseSerializersC(read_only=True)

    class Meta:
        model = TasksDetails
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'task',
            'ui_case',
            'api_case',
            'pytest_case'
        )
        return queryset


class TasksDetailsCRUD(ModelCRUD):
    model = TasksDetails
    queryset = TasksDetails.objects.all()
    serializer_class = TasksDetailsSerializersC
    serializer = TasksDetailsSerializers

    @error_response('system')
    def get(self, request: Request):
        queryset = TasksDetails.objects.all()
        task_id = request.query_params.get('task_id')
        _type = request.query_params.get('type')
        project_product_id = request.query_params.get('project_product_id')
        module_id = request.query_params.get('module_id')
        case_people_id = request.query_params.get('case_people_id')
        case_name = request.query_params.get('case_name')

        if task_id:
            queryset = queryset.filter(task_id=task_id)
        if _type not in (None, ''):
            queryset = queryset.filter(type=_type)
        if project_product_id:
            queryset = queryset.filter(
                Q(ui_case__project_product_id=project_product_id)
                | Q(api_case__project_product_id=project_product_id)
                | Q(pytest_case__project_product__project_product_id=project_product_id)
            )
        if module_id:
            queryset = queryset.filter(
                Q(ui_case__module_id=module_id)
                | Q(api_case__module_id=module_id)
                | Q(pytest_case__module_id=module_id)
            )
        if case_people_id:
            queryset = queryset.filter(
                Q(ui_case__case_people_id=case_people_id)
                | Q(api_case__case_people_id=case_people_id)
                | Q(pytest_case__case_people_id=case_people_id)
            )
        if case_name:
            queryset = queryset.filter(
                Q(ui_case__name__contains=case_name)
                | Q(api_case__name__contains=case_name)
                | Q(pytest_case__name__contains=case_name)
            )

        queryset = queryset.select_related(
            'task',
            'ui_case',
            'ui_case__project_product',
            'ui_case__module',
            'ui_case__case_people',
            'api_case',
            'api_case__project_product',
            'api_case__module',
            'api_case__case_people',
            'pytest_case',
            'pytest_case__project_product',
            'pytest_case__project_product__project_product',
            'pytest_case__module',
            'pytest_case__case_people',
        ).order_by('id')

        if request.query_params.get('pageSize') and request.query_params.get('page'):
            data_list, count = self.paging_list(
                request.query_params.get('pageSize'),
                request.query_params.get('page'),
                queryset,
                self.get_serializer_class(),
            )
            return ResponseData.success(RESPONSE_MSG_0001, data_list, count)
        return ResponseData.success(
            RESPONSE_MSG_0001,
            self.get_serializer_class()(instance=queryset, many=True).data,
            queryset.count(),
        )

    @error_response('system')
    def post(self, request: Request):
        _type = int(request.data.get('type'))
        task_id = int(request.data.get('task'))

        if _type == TestCaseTypeEnum.UI.value:
            ui_case_ids = request.data.get('ui_case')
            for ui_case_id in ui_case_ids:
                TasksDetails.objects.get_or_create(
                    task_id=task_id,
                    ui_case_id=ui_case_id,
                    defaults={'type': _type}
                )
        elif _type == TestCaseTypeEnum.API.value:
            api_case_ids = request.data.get('api_case')
            for api_case_id in api_case_ids:
                TasksDetails.objects.get_or_create(
                    task_id=task_id,
                    api_case_id=api_case_id,
                    defaults={'type': _type}
                )
        else:
            pytest_case_ids = request.data.get('pytest_case')
            pytest_cases = PytestCase.objects.filter(id__in=pytest_case_ids)
            if pytest_cases.count() != len(pytest_case_ids):
                return ResponseData.fail(RESPONSE_MSG_0120)
            for model in pytest_cases:
                if not model.project_product or not model.project_product.project_product:
                    return ResponseData.fail(RESPONSE_MSG_0120)
            for pytest_case_id in pytest_case_ids:
                TasksDetails.objects.get_or_create(
                    task_id=task_id,
                    pytest_case_id=pytest_case_id,
                    defaults={'type': _type}
                )

        return ResponseData.success(RESPONSE_MSG_0002)


class TasksDetailsViews(ViewSet):
    model = TasksDetails
    serializer_class = TasksDetailsSerializers

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_type_case_name(self, request: Request):
        _type = int(request.query_params.get('type'))
        module_id = request.query_params.get('module_id')
        module_ids = [
            item for item in request.query_params.get('module_ids', '').split(',')
            if item
        ]
        project_product_id = request.query_params.get('project_product_id')
        if _type == TestCaseTypeEnum.UI.value:
            queryset = UiCase.objects.all()
            if module_ids:
                queryset = queryset.filter(module_id__in=module_ids)
            elif module_id:
                queryset = queryset.filter(module=module_id)
            elif project_product_id:
                queryset = queryset.filter(project_product=project_product_id)
            else:
                queryset = queryset.none()
            res = queryset.values_list('id', 'name')
        elif _type == TestCaseTypeEnum.API.value:
            queryset = ApiCase.objects.all()
            if module_ids:
                queryset = queryset.filter(module_id__in=module_ids)
            elif module_id:
                queryset = queryset.filter(module=module_id)
            elif project_product_id:
                queryset = queryset.filter(project_product=project_product_id)
            else:
                queryset = queryset.none()
            res = queryset.values_list('id', 'name')
        else:
            queryset = PytestCase.objects.all()
            if module_ids:
                queryset = queryset.filter(module_id__in=module_ids)
            elif module_id:
                queryset = queryset.filter(module=module_id)
            elif project_product_id:
                queryset = queryset.filter(project_product__project_product=project_product_id)
            else:
                queryset = queryset.none()
            res = queryset.values_list('id', 'name')
        return ResponseData.success(RESPONSE_MSG_0065, [{'key': _id, 'title': name} for _id, name in res])

    @action(methods=['post'], detail=False)
    @error_response('system')
    def batch_set_cases(self, request: Request):
        case_id_list = request.data.get('case_id_list')
        _type = request.data.get('type')
        scheduled_tasks_id = request.data.get('scheduled_tasks_id')
        if _type == TestCaseTypeEnum.UI.value:
            case_name = 'ui_case'
        elif _type == TestCaseTypeEnum.API.value:
            case_name = 'api_case'
        else:
            obj = PytestCase.objects.filter(id__in=case_id_list)
            for case in obj:
                if case.project_product is None or case.project_product.project_product is None:
                    return ResponseData.fail(RESPONSE_MSG_0091)
            case_name = 'pytest_case'
        tasks_run_case_list = self.model.objects.filter(task=scheduled_tasks_id).values_list(case_name, flat=True)
        for case_id in case_id_list:
            if case_id not in list(tasks_run_case_list):
                serializer = self.serializer_class(data={'task': scheduled_tasks_id, 'type': _type, case_name: case_id})
                if serializer.is_valid():
                    serializer.save()
                else:
                    return ResponseData.fail(RESPONSE_MSG_0066)
        return ResponseData.success(RESPONSE_MSG_0067)

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_pytest.models import PytestCase
from src.auto_test.auto_pytest.service.base.update_file import UpdateFile
from src.auto_test.auto_pytest.service.base.version_control import GitRepo
from src.auto_test.auto_pytest.service.test_case.test_case import TestCase
from src.auto_test.auto_pytest.views.pytest_product import PytestProductSerializersC
from src.auto_test.auto_system.views.product_module import ProductModuleSerializers
from src.auto_test.auto_user.views.user import UserSerializers
from src.enums.pytest_enum import PytestFileTypeEnum, FileStatusEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PytestCaseSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    file_update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestCase
        fields = '__all__'


class PytestCaseSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    file_update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = PytestProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)

    class Meta:
        model = PytestCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
            'case_people',
        )
        return queryset


class PytestCaseCRUD(ModelCRUD):
    model = PytestCase
    queryset = PytestCase.objects.all()
    serializer_class = PytestCaseSerializersC
    serializer = PytestCaseSerializers


class PytestCaseViews(ViewSet):
    model = PytestCase
    serializer_class = PytestCaseSerializers

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_update(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """
        file_path_list = list(self.model.objects.all().values_list('file_path', flat=True))
        _file_path_list = []
        for project in UpdateFile(PytestFileTypeEnum.TEST_CASE, GitRepo().local_warehouse_path).find_test_files():
            for file in project.auto_test:
                _file_path_list.append(file.path)
                pytest_act, created = self.model.objects.get_or_create(
                    file_path=file.path,
                    defaults={
                        'name': file.name,
                        'file_name': file.name,
                        'file_status': FileStatusEnum.UNBOUND.value,
                        'file_update_time': file.time.replace(tzinfo=None),

                    }
                )
                if not created:
                    pytest_act.file_update_time = file.time.replace(tzinfo=None)
                    pytest_act.save()
        deleted_files = set(file_path_list) - set(_file_path_list)
        if deleted_files:
            self.model.objects.filter(file_path__in=deleted_files).update(
                file_status=FileStatusEnum.DELETED.value,
            )
        return ResponseData.success(RESPONSE_MSG_0078)

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_read(self, request: Request):
        file_path = self.model.objects.get(id=request.query_params.get('id')).file_path
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
        return ResponseData.success(RESPONSE_MSG_0084, data=file_content)

    @action(methods=['POST'], detail=False)
    @error_response('pytest')
    def pytest_write(self, request: Request):
        file_path = self.model.objects.get(id=request.data.get('id')).file_path
        file_content = request.data.get('file_content')
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(file_content)
        return ResponseData.success(RESPONSE_MSG_0085)

    @action(methods=['GET'], detail=False)
    @error_response('pytest')
    def pytest_test_case(self, request: Request):
        report_data = TestCase().test_case_main(request.query_params.get('id'))
        return ResponseData.success(RESPONSE_MSG_0086, data=report_data)

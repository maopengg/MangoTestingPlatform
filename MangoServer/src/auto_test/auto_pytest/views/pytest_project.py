# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_pytest.models import PytestProject, PytestProjectModule
from src.auto_test.auto_pytest.service.base.update_file import UpdateFile
from src.auto_test.auto_pytest.service.base.version_control import GitRepo
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.enums.pytest_enum import PytestFileTypeEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PytestProjectSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PytestProject
        fields = '__all__'


class PytestProjectSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)

    class Meta:
        model = PytestProject
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product'
        )
        return queryset


class PytestProjectCRUD(ModelCRUD):
    model = PytestProject
    queryset = PytestProject.objects.all()
    serializer_class = PytestProjectSerializersC
    serializer = PytestProjectSerializers


class PytestProjectViews(ViewSet):
    model = PytestProject
    serializer_class = PytestProjectSerializers

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_update(self, request: Request):
        repo = GitRepo()
        repo.pull_repo()
        update_file = UpdateFile(PytestFileTypeEnum.TEST_CASE, repo.local_warehouse_path).find_test_files(True)
        from src.auto_test.auto_pytest.models import PytestProjectModule

        for project in update_file:
            if not self.model.objects.get(file_name=project.project_name).exists():
                pytest_project = self.model.objects.create(
                    name=project.project_name,
                    file_name=project.project_name,
                    init_file=project.init_file_path,
                )
                pytest_project_id = pytest_project.id
            else:
                pytest_project_id = self.model.objects.get(name=project.project_name).id
            for module_name in project.module_name:
                if not PytestProjectModule.objects.filter(file_name=module_name).exists():
                    PytestProjectModule.objects.create(
                        pytest_project_id=pytest_project_id,
                        name=module_name,
                        file_name=module_name,
                    )
        return ResponseData.success(RESPONSE_MSG_0078)

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_push(self, request: Request):
        try:
            repo = GitRepo()
            repo.push_repo()
            return ResponseData.success(RESPONSE_MSG_0090)
        except Exception as error:
            return ResponseData.fail(RESPONSE_MSG_0091, data=str(error))

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_read(self, request: Request):
        file_path = self.model.objects.get(id=request.query_params.get('id')).init_file
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()
        return ResponseData.success(RESPONSE_MSG_0084, data=file_content)

    @action(methods=['POST'], detail=False)
    @error_response('pytest')
    def pytest_write(self, request: Request):
        file_path = self.model.objects.get(id=request.data.get('id')).init_file
        file_content = request.data.get('file_content')
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(file_content)
        return ResponseData.success(RESPONSE_MSG_0085)

    @action(methods=['get'], detail=False)
    @error_response('pytest')
    def pytest_project_name(self, request: Request):
        """
        执行单个用例组
        @param request:
        @return:
        """
        res = self.model.objects \
            .filter(project_product_id=request.query_params.get('project_product_id')) \
            .values_list('id', 'name')
        data = []
        for _id, name in res:
            module = PytestProjectModule.objects \
                .filter(pytest_project_id=_id) \
                .values_list('id', 'name')
            data.append(
                {'value': _id, 'label': name, 'children': [{'value': __id, 'label': _name} for __id, _name in module]})

        return ResponseData.success(RESPONSE_MSG_0074, data)

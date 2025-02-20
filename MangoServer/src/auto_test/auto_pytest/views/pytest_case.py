# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-18 20:15
# @Author : 毛鹏
import subprocess

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_pytest.models import PytestCase
from src.auto_test.auto_pytest.service.base.update_file import UpdateFile
from src.auto_test.auto_pytest.views.pytest_module import PytestProjectModuleSerializersC
from src.auto_test.auto_pytest.views.pytest_project import PytestProjectSerializersC
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
    pytest_project = PytestProjectSerializersC(read_only=True)
    module = PytestProjectModuleSerializersC(read_only=True)

    class Meta:
        model = PytestCase
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'module',
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
        for project in UpdateFile(PytestFileTypeEnum.TEST_CASE).find_test_files():
            for file in project.file:
                for act in file.test_case:
                    pytest_act, created = self.model.objects.get_or_create(
                        file_path=act.path,
                        defaults={
                            'name': act.name,
                            'file_name': act.name,
                            'file_status': FileStatusEnum.UNBOUND.value,
                            'file_update_time': act.time.replace(tzinfo=None),

                        }
                    )
                    if not created:
                        pytest_act.file_update_time = act.time.replace(tzinfo=None)
                        pytest_act.save()
        return ResponseData.success(RESPONSE_MSG_0074)

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

    @action(methods=['POST'], detail=False)
    @error_response('pytest')
    def pytest_test_case(self, request: Request):
        file_path = request.data.get('file_path')  # pytest的测试文件
        print(file_path)
        _id = request.data.get('id')
        result = subprocess.run(
            ['pytest', file_path],  # 运行指定文件或目录
            capture_output=True,  # 捕获标准输出和错误
            text=True  # 以文本形式返回输出
        )
        return ResponseData.success(RESPONSE_MSG_0085, data={
            'id': _id,
            'stdout': result.stdout,  # pytest 的标准输出
            'stderr': result.stderr,  # pytest 的错误输出
            'returncode': result.returncode  # 返回码（0 表示成功）
        })

# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-17 21:39
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiPublic
from PyAutoTest.auto_test.auto_api.service.run_api_send import RunApiSend
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.settings import DRIVER, SERVER
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData


class ApiPublicSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiPublic
        fields = '__all__'


class ApiPublicSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = ApiPublic
        fields = '__all__'


class ApiPublicCRUD(ModelCRUD):
    model = ApiPublic
    queryset = ApiPublic.objects.all()
    serializer_class = ApiPublicSerializersC
    serializer = ApiPublicSerializers


class ApiPublicViews(ViewSet):
    model = ApiPublic
    serializer_class = ApiPublicSerializers

    @action(methods=['get'], detail=False)
    def client_refresh(self, request: Request):
        data, res = RunApiSend(request.query_params.get("username")).public_args_data()
        if res:
            return ResponseData.success(f'刷新{DRIVER}api自动化数据成功', data)
        return ResponseData.fail(f'刷新失败，请确保{DRIVER}已连接{SERVER}', data)

    @action(methods=['put'], detail=False)
    def put_status(self, request: Request):
        """
        修改启停用
        :param request:
        :return:
        """
        obj = self.model.objects.get(id=request.data.get('id'))
        obj.status = request.data.get('status')
        obj.save()
        return ResponseData.success('修改API参数状态成功', )

    @action(methods=['get'], detail=False)
    def get_set_cache(self, request: Request):
        from PyAutoTest.auto_test.auto_api.service.driver.common_parameters import CommonParameters
        CommonParameters(request.query_params.get('id'))
        return ResponseData.success('设置API公共参数成功', )

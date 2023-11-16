# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 18:54
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.consumers import socket_conn
from PyAutoTest.auto_test.auto_ui.models import UiConfig
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.enums.actuator_api_enum import UiEnum
from PyAutoTest.enums.system_enum import IsItEnabled, ClientTypeEnum
from PyAutoTest.enums.ui_enum import BrowserTypeEnum, DriveTypeEnum
from PyAutoTest.models.socket_model import SocketDataModel, QueueModel
from PyAutoTest.models.socket_model.ui_model import WEBConfigModel
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.view_tools import enum_list


class UiConfigSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiConfig
        fields = '__all__'


class UiConfigSerializersC(serializers.ModelSerializer):
    user_id = UserSerializers(read_only=True)

    class Meta:
        model = UiConfig
        fields = '__all__'


class UiConfigCRUD(ModelCRUD):
    model = UiConfig
    queryset = UiConfig.objects.all()
    serializer_class = UiConfigSerializersC
    serializer = UiConfigSerializers


class UiConfigViews(ViewSet):
    model = UiConfig
    serializer_class = UiConfigSerializers

    @action(methods=['get'], detail=False)
    def get_browser_type(self, request: Request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success('获取数据成功', enum_list(BrowserTypeEnum))

    @action(methods=['get'], detail=False)
    def get_drive_type(self, request: Request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return ResponseData.success('获取数据成功', enum_list(DriveTypeEnum))

    @action(methods=['put'], detail=False)
    def put_status(self, request: Request):
        """
        获取操作类型
        :param request:
        :return:
        """
        status = request.data.get('status')
        is_headless = request.data.get('is_headless')
        obj = self.model.objects.get(id=request.data.get('id'))

        if status:
            obj_list = self.model.objects.filter(user_id=obj.user_id)
            for i in obj_list:
                if i.status == IsItEnabled.right.value and i.type == obj.type and i.id != obj.id:
                    return ResponseData.fail('当前类型已有开启状态')

            obj.status = request.data.get('status')
            obj.save()
        if is_headless is not None:
            obj.is_headless = request.data.get('is_headless')
            obj.save()
        return ResponseData.success('修改UI配置成功', )

    @action(methods=['get'], detail=False)
    def new_browser_obj(self, request: Request):
        """

        @param request:
        @return:
        """
        config_obj = self.model.objects.get(id=request.query_params.get('id'))
        web_config = WEBConfigModel(browser_type=config_obj.browser_type,
                                    browser_port=config_obj.browser_port,
                                    browser_path=config_obj.browser_path,
                                    is_headless=config_obj.is_headless)
        send_socket_data = SocketDataModel(
            code=200,
            msg="实例化web对象",
            user=request.user.get('username'),
            is_notice=ClientTypeEnum.ACTUATOR.value,
            data=QueueModel(
                func_name=UiEnum.u_page_new_obj.value,
                func_args=web_config
            )
        )
        socket_conn.active_send(send_socket_data)
        return ResponseData.success('发送配置成功', )

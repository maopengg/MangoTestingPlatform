# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-03-25 18:54
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet
from PyAutoTest.exceptions import MangoServerError
from PyAutoTest.auto_test.auto_system.consumers import ChatConsumer
from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.enums.socket_api_enum import UiSocketEnum
from PyAutoTest.auto_test.auto_ui.models import UiConfig
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.enums.tools_enum import StatusEnum, ClientTypeEnum
from PyAutoTest.enums.ui_enum import DriveTypeEnum
from PyAutoTest.models.socket_model import SocketDataModel, QueueModel
from PyAutoTest.models.socket_model.ui_model import WEBConfigModel
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData


class UiConfigSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiConfig
        fields = '__all__'


class UiConfigSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
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
                if i.status == StatusEnum.SUCCESS.value and i.type == obj.type and i.id != obj.id:
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
        is_recording = request.query_params.get('is_recording')
        if is_recording == '1':
            user_obj = User.objects.get(id=request.user['id'])
            config_obj = UiConfig.objects.get(user_id=request.user['id'],
                                              status=StatusEnum.SUCCESS.value,
                                              type=DriveTypeEnum.WEB.value)
            if not user_obj.selected_project:
                return ResponseData.fail('请先选择项目后再尝试', )
            if not user_obj.selected_environment:
                return ResponseData.fail('请先选择测试环境后再尝试', )
            web_config = WEBConfigModel(browser_type=config_obj.browser_type,
                                        browser_port=config_obj.browser_port,
                                        browser_path=config_obj.browser_path,
                                        is_headless=config_obj.is_headless,
                                        project_id=user_obj.selected_project,
                                        is_header_intercept=True,
                                        host=TestObject.objects.get(id=user_obj.selected_environment).value)
        else:
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
                func_name=UiSocketEnum.NEW_PAGE_OBJ.value,
                func_args=web_config
            )
        )
        try:
            ChatConsumer.active_send(send_socket_data)
        except MangoServerError as e:
            return ResponseData.fail(e.msg, )
        return ResponseData.success('浏览器正在启动中...', )

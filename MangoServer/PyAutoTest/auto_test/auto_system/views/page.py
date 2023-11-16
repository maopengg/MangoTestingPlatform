# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import re

from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.service.get_common_parameters import GetCommonParameters
from PyAutoTest.auto_test.auto_system.consumers import socket_conn
from PyAutoTest.enums.actuator_api_enum import ToolsEnum
from PyAutoTest.enums.system_enum import ClientTypeEnum
from PyAutoTest.models.socket_model import SocketDataModel, QueueModel
from PyAutoTest.models.socket_model.api_model import ApiPublicModel
from PyAutoTest.models.socket_model.tools_model import PublicDataModel
from PyAutoTest.models.socket_model.ui_model import UiPublicModel
from PyAutoTest.settings import DRIVER
from PyAutoTest.tools.cache_utils.redis import Cache
from PyAutoTest.tools.data_processor import ObtainRandomData
from PyAutoTest.tools.response_data import ResponseData


class SystemViews(ViewSet):

    @action(methods=['post'], detail=False)
    def test_func(self, request: Request):
        print(request.data)
        return ResponseData.fail(request.data)

    @action(methods=['get'], detail=False)
    def send_common_parameters(self, request: Request):
        test_obj_id = request.query_params.get('test_obj_id')
        mysql = GetCommonParameters.get_mysql_config(test_obj_id)
        # 发送公共数据
        api_public: list[ApiPublicModel] = GetCommonParameters.get_api_args(test_obj_id)
        ui_public: list[UiPublicModel] = GetCommonParameters.get_ui_args(test_obj_id)

        public_data = PublicDataModel(
            mysql=mysql,
            api=api_public,
            ui=ui_public
        )
        socket_data = SocketDataModel(
            code=200,
            msg="接收公共参数成功，正在写入缓存",
            user=request.user.get('username'),
            is_notice=ClientTypeEnum.ACTUATOR.value,
            data=QueueModel(
                func_name=ToolsEnum.public_data_write.value,
                func_args=public_data
            )
        )
        res2 = socket_conn.active_send(socket_data)

        if not res2:
            return ResponseData.fail('发送公共参数失败，请检查执行器是否连接')
        return ResponseData.success(f'请等待{DRIVER}处理参数完成', public_data.dict())

    @action(methods=['get'], detail=False)
    def common_variable(self, request: Request):
        """
        返回公共变量页
        @param request:
        @return:
        """
        return ResponseData.success('获取数据成功', ObtainRandomData.get_methods())

    @action(methods=['get'], detail=False)
    def random_data(self, request: Request):
        name = request.GET.get("name")
        res1 = name.replace("${", "")
        name: str = res1.replace("}", "").strip()
        if not name:
            return ResponseData.fail('请输入函数名称')
        match = re.search(r'\((.*?)\)', name)
        if match:
            return ResponseData.success('获取数据成功', str(ObtainRandomData.regular(name)))
        else:
            if Cache().read_data_from_cache(name):
                return ResponseData.success('获取数据成功', Cache().read_data_from_cache(name))
            else:
                return ResponseData.fail('Redis缓存中不存在')

    @action(methods=['get'], detail=False)
    def get_cache_key_value(self, request: Request):
        socket_data = SocketDataModel(
            code=200,
            msg="查询执行器的缓存",
            user=request.user.get('username'),
            is_notice=ClientTypeEnum.ACTUATOR.value,
            data=QueueModel(
                func_name=ToolsEnum.get_cache_key_value.value,
                func_args=request.query_params.get('key')
            )
        )
        socket_conn.active_send(socket_data)
        return ResponseData.success('获取数据成功')

# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
from PyAutoTest.auto_test.auto_api.service.get_common_parameters import GetCommonParameters
from PyAutoTest.auto_test.auto_system.service.notic_tools import NoticeMain
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.enums.actuator_api_enum import ToolsEnum
from PyAutoTest.enums.system_enum import ClientTypeEnum
from PyAutoTest.models.socket_model import SocketDataModel, QueueModel
from PyAutoTest.models.socket_model.api_model import ApiPublicModel
from PyAutoTest.models.socket_model.tools_model import PublicDataModel
from PyAutoTest.models.socket_model.ui_model import UiPublicModel
from PyAutoTest.tools.cache_utils.redis_base import RedisBase


class SystemConsumer:

    def system_notice_main(self, project_name, case=1):
        """ 启动通知消息，自动进行通知 """
        NoticeMain.test_notice_send(case)
        print('启动通知消息，自动进行通知')

    def t_set_redis(self, data: list[dict]):
        redis = RedisBase('default')
        for i in data:
            for key, value in i.items():
                redis.set_key(key, value)

    def t_get_user_info(self, username: str):
        user = User.objects.get(username=username)
        if user.selected_environment:
            mysql = GetCommonParameters.get_mysql_config(user.selected_environment)
            # 发送公共数据
            api_public: list[ApiPublicModel] = GetCommonParameters.get_api_args(user.selected_environment)
            ui_public: list[UiPublicModel] = GetCommonParameters.get_ui_args(user.selected_environment)

            public_data = PublicDataModel(
                mysql=mysql,
                api=api_public,
                ui=ui_public
            )
            socket_data = SocketDataModel(
                code=200,
                msg="接收公共参数成功，正在写入缓存",
                user=username,
                is_notice=ClientTypeEnum.ACTUATOR.value,
                data=QueueModel(
                    func_name=ToolsEnum.public_data_write.value,
                    func_args=public_data
                )
            )
            from PyAutoTest.auto_test.auto_system.consumers import socket_conn

            res2 = socket_conn.active_send(socket_data)

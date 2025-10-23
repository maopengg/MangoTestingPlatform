# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
import json

from mangotools.enums import CacheValueTypeEnum
from src.auto_test.auto_pytest.service.test_case.case_flow import PyCaseFlow
from src.auto_test.auto_system.models import CacheData
from src.auto_test.auto_system.views.cache_data import CacheDataCRUD
from src.auto_test.auto_ui.service.test_case.case_flow import UiCaseFlow
from src.enums.system_enum import CacheDataKey2Enum, ClientTypeEnum
from src.enums.tools_enum import TestCaseTypeEnum
from src.models.socket_model import SocketDataModel
from src.models.system_model import GetTaskModel
from src.tools.decorator.retry import ensure_db_connection


class SystemConsumer:

    @classmethod
    @ensure_db_connection()
    def t_set_operation_options(cls, data: dict):
        data = {
            'describe': data.get('version'),
            'key': CacheDataKey2Enum.SELECT_VALUE.value,
            'value': json.dumps(data.get('data'), ensure_ascii=False),
            'value_type': CacheValueTypeEnum.DICT.value,
        }
        try:
            cache_data = CacheData.objects.get(key=CacheDataKey2Enum.SELECT_VALUE.value)
            if cache_data:
                CacheDataCRUD.inside_put(cache_data.id, data)
        except CacheData.DoesNotExist:
            CacheDataCRUD.inside_post(data)
        except CacheData.MultipleObjectsReturned:
            cache_data_list = CacheData.objects.filter(key=CacheDataKey2Enum.SELECT_VALUE.value)
            for cache_data in cache_data_list:
                cache_data.delete()
            CacheDataCRUD.inside_post(data)

    @classmethod
    @ensure_db_connection()
    def t_set_userinfo(cls, data):
        from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
        from src.auto_test.auto_system.consumers import ChatConsumer
        SocketUser.set_userinfo(data.get('username'), data.get('is_open'), data.get('debug'))
        ChatConsumer.active_send(SocketDataModel(
            code=200,
            msg=f'设置用户信息成功，请前往执行器页面查看',
            user=data.get("username"),
            is_notice=ClientTypeEnum.WEB,
        ))

    @classmethod
    @ensure_db_connection()
    def t_get_task(cls, data: dict):
        data = GetTaskModel(**data)
        if data.type == TestCaseTypeEnum.UI:
            UiCaseFlow.get_case(data)
        elif data.type == TestCaseTypeEnum.PYTEST:
            PyCaseFlow.get_case(data)

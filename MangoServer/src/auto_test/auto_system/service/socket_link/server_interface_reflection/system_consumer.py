# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023/3/23 11:25
# @Author : 毛鹏
import json

from mangotools.enums import CacheValueTypeEnum

from src.auto_test.auto_system.models import CacheData
from src.auto_test.auto_system.views.cache_data import CacheDataCRUD
from src.enums.system_enum import CacheDataKey2Enum, ClientTypeEnum
from src.models.socket_model import SocketDataModel
from src.tools.decorator.retry import ensure_db_connection
from src.settings import VERSION

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
    def t_set_actuator_open_state(cls, data):
        from src.auto_test.auto_system.service.socket_link.socket_user import SocketUser
        from src.auto_test.auto_system.consumers import ChatConsumer
        SocketUser.set_user_open_status(data.get('username'), data.get('status'))
        ChatConsumer.active_send(SocketDataModel(
            code=200,
            msg=f'执行器连接成功，当前OPEN状态：{SocketUser.get_user_obj(data.get("username")).is_open}',
            user=data.get("username"),
            is_notice=ClientTypeEnum.WEB,
        ))

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-20 16:52
# @Author : 毛鹏
from typing import Any

from pydantic import BaseModel

from src.auto_test.auto_user.models import User
from src.enums.system_enum import ClientNameEnum
from src.exceptions import *


class SocketUserModel(BaseModel):
    user_id: int
    username: str
    web_obj: Any | None = None
    client_obj: Any | None = None


class SocketUser:
    user: list[SocketUserModel] = []

    @classmethod
    def set_user_web_obj(cls, username, web_obj):
        for i in cls.user:
            if i.username == username:
                i.web_obj = web_obj
                return
        cls.user.append(
            SocketUserModel(user_id=User.objects.get(username=username).id, username=username, web_obj=web_obj))

    @classmethod
    def set_user_client_obj(cls, username, client_obj):
        for i in cls.user:
            if i.username == username:
                i.client_obj = client_obj
                return
        cls.user.append(
            SocketUserModel(user_id=User.objects.get(username=username).id, username=username, client_obj=client_obj))

    @classmethod
    def delete_user_web_obj(cls, username):
        for i in cls.user:
            if i.username == username:
                i.web_obj = None
            if i.client_obj is None and i.web_obj is None:
                cls.user.remove(i)

    @classmethod
    def delete_user_client_obj(cls, username):
        for i in cls.user:
            if i.username == username:
                i.client_obj = None
            if i.client_obj is None and i.web_obj is None:
                cls.user.remove(i)

    @classmethod
    def get_user_web_obj(cls, username):
        for i in cls.user:
            if i.username == username:
                if i.web_obj:
                    return i.web_obj
                else:
                    return False
        #             raise SocketClientNotPresentError(*ERROR_MSG_0028,
        #                                               value=(ClientNameEnum.WEB.value, ClientNameEnum.SERVER.value))
        # raise SocketClientNotPresentError(*ERROR_MSG_0028,
        #                                   value=(ClientNameEnum.WEB.value, ClientNameEnum.SERVER.value))

    @classmethod
    def get_user_client_obj(cls, username):
        for i in cls.user:
            if i.username == username:
                if i.client_obj:
                    return i.client_obj
                else:
                    raise SystemEError(*ERROR_MSG_0028,
                                       value=(ClientNameEnum.DRIVER.value, ClientNameEnum.SERVER.value))
        raise SystemEError(*ERROR_MSG_0028,
                           value=(ClientNameEnum.DRIVER.value, ClientNameEnum.SERVER.value))

    @classmethod
    def get_all_user(cls):
        return [i.username for i in cls.user if i.client_obj]

    @classmethod
    def all_keys(cls):
        return len(cls.user)

    @classmethod
    def get_all_user_list(cls):
        return cls.user

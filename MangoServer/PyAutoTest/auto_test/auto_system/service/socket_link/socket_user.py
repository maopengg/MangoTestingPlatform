# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-20 16:52
# @Author : 毛鹏
from typing import Any

from pydantic import BaseModel

from PyAutoTest.enums.tools_enum import ClientNameEnum
from PyAutoTest.exceptions.tools_exception import SocketClientNotPresentError
from PyAutoTest.tools.view_utils.error_msg import ERROR_MSG_0028


class SocketUserModel(BaseModel):
    user_key: str
    web_obj: Any | None = None
    client_obj: Any | None = None


class SocketUser:
    user: list[SocketUserModel] = []

    @classmethod
    def set_user_web_obj(cls, user_key, web_obj):
        for i in cls.user:
            if i.user_key == user_key:
                i.web_obj = web_obj
                return
        cls.user.append(SocketUserModel(user_key=user_key, web_obj=web_obj))

    @classmethod
    def set_user_client_obj(cls, user_key, client_obj):
        for i in cls.user:
            if i.user_key == user_key:
                i.client_obj = client_obj
                return
        cls.user.append(SocketUserModel(user_key=user_key, client_obj=client_obj))

    @classmethod
    def delete_user_web_obj(cls, user_key):
        for i in cls.user:
            if i.user_key == user_key:
                i.web_obj = None
            if i.client_obj is None and i.web_obj is None:
                cls.user.remove(i)

    @classmethod
    def delete_user_client_obj(cls, user_key):
        for i in cls.user:
            if i.user_key == user_key:
                i.client_obj = None
            if i.client_obj is None and i.web_obj is None:
                cls.user.remove(i)

    @classmethod
    def get_user_web_obj(cls, user_key):
        for i in cls.user:
            if i.user_key == user_key:
                if i.web_obj:
                    return i.web_obj
                else:
                    return False
        #             raise SocketClientNotPresentError(*ERROR_MSG_0028,
        #                                               value=(ClientNameEnum.WEB.value, ClientNameEnum.SERVER.value))
        # raise SocketClientNotPresentError(*ERROR_MSG_0028,
        #                                   value=(ClientNameEnum.WEB.value, ClientNameEnum.SERVER.value))

    @classmethod
    def get_user_client_obj(cls, user_key):
        for i in cls.user:
            if i.user_key == user_key:
                if i.client_obj:
                    return i.client_obj
                else:
                    raise SocketClientNotPresentError(*ERROR_MSG_0028,
                                                      value=(ClientNameEnum.DRIVER.value, ClientNameEnum.SERVER.value))
        raise SocketClientNotPresentError(*ERROR_MSG_0028,
                                          value=(ClientNameEnum.DRIVER.value, ClientNameEnum.SERVER.value))

    @classmethod
    def get_all_user(cls):
        return [i.user_key for i in cls.user if i.client_obj]

    @classmethod
    def all_keys(cls):
        return len(cls.user)

    @classmethod
    def get_all_user_list(cls):
        return cls.user

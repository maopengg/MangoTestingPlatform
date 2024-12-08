# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from .role import Role
from .user import User
from .user_log import UserLog


class UserApi(
    User,
    UserLog,
    Role,
):
    pass

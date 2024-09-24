# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-09-13 11:13
# @Author : 毛鹏
from .file_data import FileData
from .module import Module
from .product import Product
from .project import Project
from .role import Role
from .test_file import TestFile
from .test_object import TestObject
from .user import User
from .user_log import UserLog


class UserApi(User, UserLog, Role, Module, Product, Project, FileData, TestFile, TestObject):
    pass

# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.views.menu import ad_routes
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.role import RoleSerializers
from PyAutoTest.middleware.utlis.jwt_auth import create_token
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD, ModelQuery


class UserSerializers(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ['password']


class UserSerializersC(serializers.ModelSerializer):
    department = ProjectSerializers(read_only=True)
    role = RoleSerializers(read_only=True)

    class Meta:
        model = User
        exclude = ['password']


class UserCRUD(ModelCRUD):
    model = User
    queryset = User.objects.all()
    serializer_class = UserSerializersC
    serializer = UserSerializers


class UserQuery(ModelQuery):
    model = User
    serializer_class = UserSerializersC


class UserViews(ViewSet):

    @action(methods=['get'], detail=False)
    def get_nickname(self, request: Request):
        """
        获取用户名称
        :param request:
        :return:
        """
        res = User.objects.values_list('id', 'nickname')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success('获取数据成功', data)


class LoginViews(ViewSet):
    authentication_classes = []

    @action(methods=['post'], detail=False)
    def login(self, request: Request):
        username = request.data.get('username')
        password = request.data.get('password')
        user_info = User.objects.filter(username=username, password=password).first()
        if not user_info:
            return ResponseData.fail('用户名或密码错误')
        token = create_token({'id': user_info.id, 'username': user_info.username})
        data = {
            "nickName": user_info.nickname,
            "userName": user_info.username,
            "userId": user_info.id,
            "roleId": user_info.role.id if user_info.role else None,
            "token": token,
            "roles": [
                {
                    "roleCode": "ROLE_admin",
                    "roleId": 1,
                    "roleName": "超级管理员"
                }
            ]
        }
        return ResponseData.success('登录成功', data)

    @action(methods=['get'], detail=False)
    def menu(self, request: Request):
        return ResponseData.success('获取菜单列表成功', ad_routes())

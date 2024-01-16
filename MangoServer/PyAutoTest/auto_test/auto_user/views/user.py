# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import datetime
import hashlib
import hmac
import json

import time
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.views.menu import ad_routes
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.role import RoleSerializers
from PyAutoTest.auto_test.auto_user.views.user_logs import UserLogsCRUD
from PyAutoTest.middleware.utlis.jwt_auth import create_token
from PyAutoTest.tools.data_processor.encryption_tool import EncryptionTool
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData


class UserSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    last_login_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    department = ProjectSerializers(read_only=True)
    role = RoleSerializers(read_only=True)

    class Meta:
        model = User
        exclude = ['password']


class UserSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    last_login_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
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


class UserViews(ViewSet):
    model = User
    serializer = UserSerializers

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

    @action(methods=['put'], detail=False)
    def put_project(self, request: Request):
        serializer = self.serializer(instance=self.model.objects.get(
            id=request.data.get('id')),
            data={'selected_project': request.data.get('selected_project')})
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(f'修改测试环境成功', serializer.data)

        else:
            return ResponseData.fail(f'修改测试环境失败{serializer.errors}')

    @action(methods=['put'], detail=False)
    def put_environment(self, request: Request):
        serializer = self.serializer(instance=self.model.objects.get(
            id=request.data.get('id')),
            data={'selected_environment': request.data.get('selected_environment')})
        if serializer.is_valid():
            serializer.save()
            return ResponseData.success(f'修改测试环境成功', serializer.data)

        else:
            return ResponseData.fail(f'修改测试环境失败{serializer.errors}')

    @action(methods=['get'], detail=False)
    def get_user_project_environment(self, request: Request):
        obj = self.model.objects.get(id=request.query_params.get('id'))
        data = {'id': obj.id, 'selected_environment': obj.selected_environment,
                'selected_project': obj.selected_project}
        return ResponseData.success(f'修改测试环境成功', data)

    @action(methods=['put'], detail=False)
    def put_password(self, request: Request):
        password = EncryptionTool.md5_encrypt(request.data['password'])
        new_password = EncryptionTool.md5_encrypt(request.data['new_password'])
        confirm_password = EncryptionTool.md5_encrypt(request.data['confirm_password'])

        obj = self.model.objects.get(id=request.data.get('id'))
        if password != obj.password:
            return ResponseData.fail('原始密码不正确')
        if new_password != confirm_password:
            return ResponseData.fail('两次密码输入不一致')
        obj.password = new_password
        obj.save()
        return ResponseData.success(f'修改密码成功')


class LoginViews(ViewSet):
    authentication_classes = []
    access_token = None

    @action(methods=['post'], detail=False)
    def login(self, request: Request):
        username = request.data.get('username')
        password = EncryptionTool.md5_encrypt(request.data.get('password'))
        source_type = request.data.get('type')
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
            "selected_project": user_info.selected_project,
            "selected_environment": user_info.selected_environment,
            "roles": [
                {
                    "description": user_info.role.description,
                    "roleId": user_info.role.id,
                    "roleName": user_info.role.name
                }
            ]
        }
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]  # 取X-Forwarded-For头中的第一个IP（即客户端的真实IP）
        else:
            ip = request.META.get('REMOTE_ADDR')
        data_logs = {"nickname": user_info.nickname,
                     "username": user_info.username,
                     "ip": ip,
                     "source_type": source_type,
                     "user_id": user_info.id}
        UserLogsCRUD().inside_post(data_logs)
        return ResponseData.success('登录成功', data)

    @action(methods=['get'], detail=False)
    def menu(self, request: Request):
        return ResponseData.success('获取菜单列表成功', ad_routes())

    @action(methods=['post'], detail=False)
    def test1(self, request: Request):
        """
        测试webhook密钥
        """
        secret_key = b"daewdaedawe"
        sign = request.headers.get('Sign')
        if not sign:
            return ResponseData.success('缺少签名', )
        # 计算哈希值
        digest = hmac.new(secret_key, json.dumps(request.data).encode(), hashlib.sha1).digest()
        # 将哈希值转换为16进制字符串
        signature = digest.hex()
        print(f'cdxp发送的key:{sign}')
        print(f'自己计算的key:{sign}')
        # 比较签名和哈希值是否相同
        if not hmac.compare_digest(signature, sign):
            return ResponseData.success('签名不正确', )

        return ResponseData.success('验证消息的内容完整成功', )

    @action(methods=['post'], detail=False)
    def test2(self, request: Request):
        """
        测试webhook Basic Authentication
        """
        webhook_username = request.headers.get('username')
        webhook_password = request.headers.get('password')
        username = 'mP1234567.'
        password = 'mP1234567..'
        if username == webhook_username and webhook_password == password:
            pass
        print(f'webhook_username：{webhook_username}', f'webhook_password：{webhook_password}')
        return ResponseData.success('Basic Authentication', )

    @action(methods=['post'], detail=False)
    def test3(self, request: Request):
        """
        测试webhook Oauth2
        """
        authorization = request.headers.get('Authorization')
        print(f'headers中的authorization值：{authorization}'
              f'没有过期的值：{self.access_token}')
        return ResponseData.success('Oauth2', )

    @action(methods=['get'], detail=False)
    def login1(self, request: Request):
        print(f'当前的时间是：{datetime.datetime.now()}')
        self.access_token = int(time.time())
        data = {
            "access_token": self.access_token,
            "token_type": "bde34423earer"
        }
        return Response(data)

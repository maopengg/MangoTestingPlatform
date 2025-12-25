# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import os
from datetime import datetime
from urllib.parse import unquote

from django.forms import model_to_dict
from django.http import FileResponse
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from mangotools.data_processor import EncryptionTool
from src import settings
from src.auto_test.auto_system.service.menu import ad_routes
from src.auto_test.auto_user.models import User
from src.auto_test.auto_user.views.role import RoleSerializers
from src.enums.system_enum import ClientTypeEnum
from src.middleware.utlis.jwt_auth import create_token
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class UserSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    last_login_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = User
        exclude = ['password']


class UserSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    last_login_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    role = RoleSerializers(read_only=True)

    class Meta:
        model = User
        exclude = ['password']

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'role')
        return queryset


class UserCRUD(ModelCRUD):
    model = User
    queryset = User.objects.all()
    serializer_class = UserSerializersC
    serializer = UserSerializers

    @error_response('user')
    def post(self, request: Request):
        data = request.data
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            user = self.model.objects.get(id=serializer.data.get('id'))
            user.password = EncryptionTool.md5_32_small(data['password'])
            user.save()
            return ResponseData.success(RESPONSE_MSG_0002, serializer.data)


class UserViews(ViewSet):
    model = User
    serializer = UserSerializers

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_name(self, request: Request):
        """
        获取用户名称
        :param request:
        :return:
        """
        res = User.objects.values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0033, data)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_project(self, request: Request):

        user = self.model.objects.get(id=request.data.get('id'))
        user.selected_project = request.data.get('selected_project')
        user.save()
        return ResponseData.success(RESPONSE_MSG_0034, model_to_dict(user, exclude=['password']))
        # return ResponseData.fail(RESPONSE_MSG_0035, serializer.errors)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_environment(self, request: Request):
        user = self.model.objects.get(id=request.data.get('id'))
        user.selected_environment = request.data.get('selected_environment')
        user.save()
        return ResponseData.success(RESPONSE_MSG_0036, model_to_dict(user, exclude=['password']))
        # return ResponseData.fail(RESPONSE_MSG_0037, serializer.errors)

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_user_project_environment(self, request: Request):
        obj = self.model.objects.get(id=request.query_params.get('id'))
        data = {'id': obj.id, 'selected_environment': obj.selected_environment,
                'selected_project': obj.selected_project}
        return ResponseData.success(RESPONSE_MSG_0041, data)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_password(self, request: Request):
        password = EncryptionTool.md5_32_small(request.data['password'])
        new_password = EncryptionTool.md5_32_small(request.data['new_password'])
        confirm_password = EncryptionTool.md5_32_small(request.data['confirm_password'])

        obj = self.model.objects.get(id=request.data.get('id'))
        if password != obj.password:
            return ResponseData.fail(RESPONSE_MSG_0038)
        if new_password != confirm_password:
            return ResponseData.fail(RESPONSE_MSG_0039)
        obj.password = new_password
        obj.save()
        return ResponseData.success(RESPONSE_MSG_0040)


class LoginViews(ViewSet):
    authentication_classes = []
    access_token = None

    @error_response('user')
    @action(methods=['post'], detail=False)
    def login(self, request: Request):
        username = request.data.get('username')
        password = request.data.get('password')
        source_type = int(request.headers.get('Source-Type', 1))
        try:
            user_info = User.objects.get(username=username, password=password)
        except User.DoesNotExist:
            return ResponseData.fail(RESPONSE_MSG_0042)
        if not user_info:
            return ResponseData.fail(RESPONSE_MSG_0042)
        if source_type == ClientTypeEnum.ACTUATOR.value:
            if request.data.get('version') != settings.VERSION:
                return ResponseData.fail(RESPONSE_MSG_0037)
        elif source_type == ClientTypeEnum.WEB.value:
            user_info.last_login_time = datetime.now()
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        user_info.ip = ip
        user_info.save()
        return ResponseData.success(RESPONSE_MSG_0043, {
            "name": user_info.name,
            "userName": user_info.username,
            "userId": user_info.id,
            "roleId": user_info.role.id if user_info.role else None,
            "token": create_token({'id': user_info.id, 'username': user_info.username, 'name': user_info.name}),
            "selected_project": user_info.selected_project,
            "selected_environment": user_info.selected_environment,
            "roles": [
                {
                    "description": user_info.role.description if user_info.role else None,
                    "roleId": user_info.role.id if user_info.role else None,
                    "roleName": user_info.role.name if user_info.role else None
                }
            ]
        })

    @error_response('user')
    @action(methods=['post'], detail=False)
    def register(self, request: Request):
        username = request.data.get('username')
        password = request.data.get('password')
        if User.objects.filter(username=username).exists():
            return ResponseData.fail(RESPONSE_MSG_0115)
        if User.objects.filter(name=request.data.get('name')).exists():
            return ResponseData.fail(RESPONSE_MSG_0122)
        else:
            data = UserCRUD.inside_post({
                "name": request.data.get('name'),
                "username": username,
                "password": password,
            })
            user_obj = User.objects.get(id=data.get('id'))
            user_obj.password = password
            user_obj.save()
            return ResponseData.success(RESPONSE_MSG_0114, data)

    @error_response('user')
    @action(methods=['POST'], detail=False)
    def menu(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0044, ad_routes())

    @error_response('user')
    @action(methods=['get'], detail=False)
    def test(self, request: Request):
        v = request.query_params.get('v')
        if v:
            from data_cleanup_scripts import data_cleanup
            data_cleanup(v)
            return ResponseData.success(RESPONSE_MSG_0045, )
        else:
            from src.auto_test.auto_system.service.update_test_suite import UpdateTestSuite
            UpdateTestSuite.send_test_result(268315135315,'')
            return ResponseData.success(RESPONSE_MSG_0044, {'title': ''})

    @error_response('user')
    @action(methods=['get'], detail=False)
    def get_download(self, request: Request):
        file_name = unquote(request.query_params.get('file_name'))
        file_path = os.path.join(settings.BASE_DIR, 'upload_template', file_name)
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=file_name)
        return response

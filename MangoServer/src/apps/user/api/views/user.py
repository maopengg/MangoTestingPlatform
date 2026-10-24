# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-06-04 12:24
# @Author : 毛鹏
import os
import re
from urllib.parse import unquote

from django.conf import settings
from django.http import FileResponse
from rest_framework import exceptions as drf_exceptions
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.system.enums import ClientTypeEnum
from src.apps.system.services.menu import ad_routes
from src.apps.user.api.serializers.user import UserSerializers, UserSerializersC
from src.apps.user.exceptions import (
    USER_REQUEST_FORMAT_INVALID,
    USER_CREDENTIAL_USER_NOT_ALLOWED,
    USER_CREDENTIAL_NOT_FOUND,
    USER_CREDENTIAL_PERMISSION_INVALID,
    UserError,
)
from src.apps.user.middleware.auth import JwtQueryParamsAuthentication
from src.apps.user.models import Department, Role, User
from src.apps.user.services.account_mutation import UserAccountMutationService
from src.apps.user.services.cli_auth import CliAuthService
from src.apps.user.services.credential import UserCredentialService
from src.apps.user.services.environment import UserEnvironmentService
from src.apps.user.services.password import double_md5, verify_password_digest
from src.apps.user.services.permission import PermissionMenuService
from src.apps.user.services.user_cache import UserCacheService
from src.common.decorators.error_response import error_response
from src.common.middleware.jwt_auth import create_token
from src.common.responses.model_crud import ModelCRUD
from src.common.responses.response_data import ResponseData
from src.common.responses.response_msg import (
    RESPONSE_MSG_0001,
    RESPONSE_MSG_0002,
    RESPONSE_MSG_0003,
    RESPONSE_MSG_0005,
    RESPONSE_MSG_0033,
    RESPONSE_MSG_0037,
    RESPONSE_MSG_0038,
    RESPONSE_MSG_0039,
    RESPONSE_MSG_0040,
    RESPONSE_MSG_0041,
    RESPONSE_MSG_0042,
    RESPONSE_MSG_0043,
    RESPONSE_MSG_0044,
    RESPONSE_MSG_0045,
    RESPONSE_MSG_0082,
    RESPONSE_MSG_0122,
    RESPONSE_MSG_0160,
    RESPONSE_MSG_0207,
    RESPONSE_MSG_0240,
    RESPONSE_MSG_0241,
    RESPONSE_MSG_0242,
    RESPONSE_MSG_0245,
    RESPONSE_MSG_0258,
    RESPONSE_MSG_0288,
    RESPONSE_MSG_0289,
    RESPONSE_MSG_0290,
    RESPONSE_MSG_0291,
    RESPONSE_MSG_0292,
    RESPONSE_MSG_0293,
    RESPONSE_MSG_0300,
    RESPONSE_MSG_0301,
    RESPONSE_MSG_0302,
    RESPONSE_MSG_0303,
    RESPONSE_MSG_0304,
    RESPONSE_MSG_0305,
)


class UserCRUD(ModelCRUD):
    model = User
    queryset = User.objects.all()
    serializer_class = UserSerializersC
    serializer = UserSerializers
    permission_key_map = {
        'get': 'system.user',
        'post': 'system.user:create',
        'put': 'system.user:edit',
        'delete': 'system.user:delete',
    }

    @staticmethod
    def save_user_departments(user: User, department_ids: list[int], update_user_id: int | None = None):
        UserAccountMutationService.replace_departments(user, department_ids, update_user_id)

    @error_response('user')
    def post(self, request: Request):
        data = dict(request.data)
        data.setdefault('role', PermissionMenuService.default_role().id)
        data['update_user'] = self.get_request_user_id(request)
        serializer = self.serializer(data=data)
        if serializer.is_valid():
            user = UserAccountMutationService.create_from_validated_data(
                serializer.validated_data,
                department_ids=data.get('department_ids') or [],
                operator_id=self.get_request_user_id(request),
            )
            return ResponseData.success(RESPONSE_MSG_0002, self.serializer(instance=user).data)
        return ResponseData.fail(RESPONSE_MSG_0003, serializer.errors)

    @classmethod
    def inside_post(cls, data: dict) -> dict:
        data = dict(data)
        data.setdefault('api_key', cls.model.unique_api_key())
        data.setdefault('role', PermissionMenuService.default_role().id)
        return super().inside_post(data)

    @error_response('user')
    def put(self, request: Request):
        data = dict(request.data)
        instance_id = data.get('id')
        if data.get('is_super_admin') is False:
            current_user = self.model.objects.filter(pk=instance_id).first()
            if current_user and current_user.is_super_admin and self.model.objects.filter(
                    is_super_admin=True).count() <= 1:
                return ResponseData.fail(RESPONSE_MSG_0207)
        response = super().put(request)
        if response.data.get('code') == 200 and 'department_ids' in data:
            user = self.model.objects.get(pk=instance_id)
            self.save_user_departments(user, data.get('department_ids') or [], self.get_request_user_id(request))
        return response


class UserViews(ViewSet):
    model = User
    serializer = UserSerializers
    action_permission_map = {
        'get_name': 'system.user',
        'get_department_name': 'system.user',
        'put_environment': 'index.home',
        'put_password': 'index.home',
        'register_user': 'system.user:create',
        'reset_password': 'system.user:edit',
        'reset_user_api_key': 'system.user:edit',
        'get_current_api_key': 'index.home',
        'reset_api_key': 'index.home',
        'cli_authorize': 'index.home',
        'get_cache_data': 'index.home',
        'clear_cache_data': 'index.home',
    }

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_cache_data(self, request: Request):
        data = UserCacheService.grouped(request.user.user_obj)
        return ResponseData.success(RESPONSE_MSG_0001, data, len(data))

    @action(methods=['delete'], detail=False)
    @error_response('user')
    def clear_cache_data(self, request: Request):
        count = UserCacheService.clear(
            request.user.user_obj,
            group_key=request.data.get('group_key'),
            cache_key=request.data.get('cache_key'),
        )
        return ResponseData.success(RESPONSE_MSG_0005, {'count': count})

    @action(methods=['post'], detail=False)
    @error_response('user')
    def cli_authorize(self, request: Request):
        if request.data.get('version') != settings.VERSION:
            return ResponseData.fail(RESPONSE_MSG_0304, {'latest_version': settings.VERSION})
        user = request.user.user_obj
        result = CliAuthService.create_code(
            token=str(request.auth),
            user=user,
            redirect_uri=request.data.get('redirect_uri'),
            state=request.data.get('state'),
            code_challenge=request.data.get('code_challenge'),
        )
        if not result:
            return ResponseData.fail(RESPONSE_MSG_0301)
        return ResponseData.success(RESPONSE_MSG_0300, result)

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

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_department_name(self, request: Request):
        res = Department.objects.filter(status=1).values_list('id', 'name')
        data = [{'key': _id, 'title': name} for _id, name in res]
        return ResponseData.success(RESPONSE_MSG_0033, data)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_environment(self, request: Request):
        user = request.user.user_obj
        result = UserEnvironmentService.switch(
            user,
            request.data.get('selected_environment'),
            operator_id=user.id,
        )
        return ResponseData.success(
            RESPONSE_MSG_0245,
            self.serializer(instance=user).data,
            value=(result['selected_environment_title'],),
        )
        # return ResponseData.fail(RESPONSE_MSG_0037, serializer.errors)

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_user_project_environment(self, request: Request):
        obj = self.model.objects.get(id=request.query_params.get('id'))
        data = {'id': obj.id, 'selected_environment': UserCacheService.selected_environment(obj)}
        return ResponseData.success(RESPONSE_MSG_0041, data)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def put_password(self, request: Request):
        password = double_md5(request.data.get('password') or '')
        new_password = request.data.get('new_password') or ''
        confirm_password = request.data.get('confirm_password') or ''

        obj = request.user.user_obj
        valid_password, _ = verify_password_digest(password, obj.password)
        if not valid_password:
            return ResponseData.fail(RESPONSE_MSG_0038)
        if new_password != confirm_password:
            return ResponseData.fail(RESPONSE_MSG_0039)
        requires_migration = not UserCredentialService.is_email_login(obj)
        login_email = obj.username
        if requires_migration:
            login_email = UserCredentialService.normalize_email(request.data.get('email'))
            UserCredentialService.ensure_email_available(login_email, exclude_user_id=obj.id)
        password_error = LoginViews._validate_register_password(login_email, obj.name, new_password)
        if password_error:
            return ResponseData.fail(RESPONSE_MSG_0240, value=(password_error,))

        UserAccountMutationService.update_password(
            obj,
            new_password,
            username=login_email if requires_migration else None,
        )
        if requires_migration:
            return ResponseData.success(RESPONSE_MSG_0291)
        return ResponseData.success(RESPONSE_MSG_0040)

    @action(methods=['post'], detail=False)
    @error_response('user')
    def register_user(self, request: Request):
        name = (request.data.get('name') or '').strip()
        if not name:
            raise UserError(USER_CREDENTIAL_USER_NOT_ALLOWED)
        email = UserCredentialService.normalize_email(request.data.get('email'))
        UserCredentialService.ensure_email_available(email)
        if User.objects.filter(name=name).exists():
            return ResponseData.fail(RESPONSE_MSG_0122)

        role_id = request.data.get('role')
        if role_id in (None, ''):
            role = PermissionMenuService.default_role()
        else:
            role = Role.objects.filter(id=role_id).first()
            if not role:
                raise UserError(USER_CREDENTIAL_NOT_FOUND)

        operator = request.user.user_obj
        is_super_admin = request.data.get('is_super_admin') is True
        if is_super_admin and not PermissionMenuService.is_effective_super_admin(operator):
            raise UserError(USER_CREDENTIAL_PERMISSION_INVALID)

        user_obj = UserAccountMutationService.register(
            name=name,
            email=email,
            role=role,
            is_super_admin=is_super_admin,
            operator=operator,
        )
        return ResponseData.success(RESPONSE_MSG_0288, self.serializer(instance=user_obj).data)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def reset_password(self, request: Request):
        user = UserAccountMutationService.reset_password(
            request.data.get('id'),
            operator=request.user.user_obj,
        )
        if not user:
            return ResponseData.fail(RESPONSE_MSG_0258)
        return ResponseData.success(RESPONSE_MSG_0290)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def reset_user_api_key(self, request: Request):
        user = self.model.objects.filter(id=request.data.get('id')).first()
        if not user:
            return ResponseData.fail(RESPONSE_MSG_0293)
        UserAccountMutationService.reset_api_key(user, operator=request.user.user_obj)
        return ResponseData.success(RESPONSE_MSG_0292)

    @action(methods=['put'], detail=False)
    @error_response('user')
    def reset_api_key(self, request: Request):
        user = request.user.user_obj
        UserAccountMutationService.reset_api_key(user)
        return ResponseData.success(RESPONSE_MSG_0082, {'api_key': user.api_key})

    @action(methods=['get'], detail=False)
    @error_response('user')
    def get_current_api_key(self, request: Request):
        user = request.user.user_obj
        if not user.api_key:
            UserAccountMutationService.reset_api_key(user)
        return ResponseData.success(RESPONSE_MSG_0033, {'api_key': user.api_key})


class LoginViews(ViewSet):
    authentication_classes = []
    access_token = None
    PASSWORD_STRENGTH_MESSAGE = (
        '密码强度不足：至少8位，并包含大写字母、小写字母、数字和特殊字符，且不能包含账号或昵称'
    )

    @action(methods=['get'], detail=False)
    def cli_version(self, request: Request):
        if request.query_params.get('version') != settings.VERSION:
            return ResponseData.fail(RESPONSE_MSG_0304, {'latest_version': settings.VERSION})
        return ResponseData.success(RESPONSE_MSG_0305, {'version': settings.VERSION})

    @staticmethod
    def _get_source_type(request: Request, data) -> int:
        source_type = request.headers.get('Source-Type')
        if source_type is None:
            source_type = data.get('type', ClientTypeEnum.WEB.value)
        try:
            return int(source_type)
        except (TypeError, ValueError):
            return ClientTypeEnum.WEB.value

    @classmethod
    def _validate_register_password(cls, username: str | None, name: str | None, password: str | None) -> str | None:
        password = password or ''
        username = (username or '').lower()
        name = (name or '').lower()
        lower_password = password.lower()
        if len(password) < 8:
            return cls.PASSWORD_STRENGTH_MESSAGE
        if re.fullmatch(r'[a-fA-F0-9]{32}', password):
            return '注册接口需要传入明文密码，服务端会统一加密保存'
        if username and username in lower_password:
            return cls.PASSWORD_STRENGTH_MESSAGE
        if name and name in lower_password:
            return cls.PASSWORD_STRENGTH_MESSAGE
        checks = (
            re.search(r'[a-z]', password),
            re.search(r'[A-Z]', password),
            re.search(r'\d', password),
            re.search(r'[^A-Za-z0-9]', password),
        )
        if not all(checks):
            return cls.PASSWORD_STRENGTH_MESSAGE
        return None

    @staticmethod
    def _validate_register_base(username: str | None, name: str | None, password: str | None) -> str | None:
        if not username or not name or not password:
            return '用户昵称、登录账号和密码不允许为空'
        if re.search(r'[\u4e00-\u9fff]', username):
            return '登录账号不允许包含中文'
        return None

    def get_throttles(self):
        throttle_scope_map = {
            'login': 'login',
            'get_download': 'download',
            'register': 'credential_email',
            'reset_password_by_email': 'credential_email',
        }
        self.throttle_scope = throttle_scope_map.get(getattr(self, 'action', None))
        return super().get_throttles()

    @action(methods=['post'], detail=False)
    def cli_token(self, request: Request):
        result = CliAuthService.exchange_code(
            code=request.data.get('code'),
            code_verifier=request.data.get('code_verifier'),
            redirect_uri=request.data.get('redirect_uri'),
        )
        if not result:
            return ResponseData.fail(RESPONSE_MSG_0302)
        return ResponseData.success(RESPONSE_MSG_0303, result)

    @staticmethod
    def _is_super_admin_registration(request: Request) -> bool:
        try:
            auth_result = JwtQueryParamsAuthentication().authenticate(request)
        except Exception:
            return False
        if not auth_result:
            return False
        user_context, _ = auth_result
        user = user_context.user_obj
        return (
                PermissionMenuService.is_effective_super_admin(user)
                and 'system.user:create' in PermissionMenuService.permission_keys_for_user(user)
        )

    @error_response('user')
    @action(methods=['post'], detail=False)
    def login(self, request: Request):
        try:
            data = request.data
        except (drf_exceptions.UnsupportedMediaType, drf_exceptions.ParseError) as error:
            raise UserError(USER_REQUEST_FORMAT_INVALID, value=(str(error),)) from error
        username = (data.get('username') or '').strip()
        password = data.get('password')
        source_type = self._get_source_type(request, data)
        user_info = User.objects.filter(username=username).first()
        if not user_info and '@' in username:
            user_info = User.objects.filter(username__iexact=username).first()
        if not user_info:
            return ResponseData.fail(RESPONSE_MSG_0042)
        valid_password, upgraded_password = verify_password_digest(password, user_info.password)
        if not valid_password:
            return ResponseData.fail(RESPONSE_MSG_0042)
        if username == 'open' and source_type != ClientTypeEnum.ACTUATOR.value:
            return ResponseData.fail(RESPONSE_MSG_0160)
        if source_type == ClientTypeEnum.ACTUATOR.value:
            if data.get('version') != settings.VERSION:
                return ResponseData.fail(RESPONSE_MSG_0037)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        UserAccountMutationService.record_login(
            user_info,
            ip=ip,
            update_last_login=source_type == ClientTypeEnum.WEB.value,
            upgraded_password=upgraded_password,
        )
        return ResponseData.success(RESPONSE_MSG_0043, {
            "name": user_info.name,
            "userName": user_info.username,
            "userId": user_info.id,
            "roleId": user_info.role.id if user_info.role else None,
            "is_super_admin": PermissionMenuService.is_effective_super_admin(user_info),
            "token": create_token({
                'id': user_info.id,
                'username': user_info.username,
                'name': user_info.name,
                'client_type': source_type,
            }),
            "selected_environment": UserCacheService.selected_environment(user_info),
            "roles": [
                {
                    "description": user_info.role.description if user_info.role else None,
                    "roleId": user_info.role.id if user_info.role else None,
                    "roleName": user_info.role.name if user_info.role else None
                }
            ]
        })

    @error_response('user')
    @action(methods=['get'], detail=False)
    def registration_config(self, request: Request):
        from src.apps.system.services.system_config import SystemConfigService

        response = ResponseData.success(RESPONSE_MSG_0001, SystemConfigService.get_registration_config())
        response['Cache-Control'] = 'no-store'
        return response

    @error_response('user')
    @action(methods=['post'], detail=False)
    def register(self, request: Request):
        from src.apps.system.services.system_config import SystemConfigService

        registration_config = SystemConfigService.get_registration_config()
        if (
                not registration_config['allow_registration']
                and not self._is_super_admin_registration(request)
        ):
            return ResponseData.fail((300, registration_config['disabled_message']))
        name = (request.data.get('name') or '').strip()
        if not name:
            raise UserError(USER_CREDENTIAL_USER_NOT_ALLOWED)
        email = UserCredentialService.normalize_email(request.data.get('email'))
        UserCredentialService.ensure_email_available(email)
        if User.objects.filter(name=name).exists():
            return ResponseData.fail(RESPONSE_MSG_0122)
        user_obj = UserAccountMutationService.register(
            name=name,
            email=email,
            role=PermissionMenuService.default_role(),
        )
        data = UserSerializers(instance=user_obj).data
        return ResponseData.success(RESPONSE_MSG_0288, data)

    @error_response('user')
    @action(methods=['post'], detail=False)
    def reset_password_by_email(self, request: Request):
        email = UserCredentialService.normalize_email(request.data.get('email'))
        user = User.objects.filter(username__iexact=email).first()
        if user:
            UserAccountMutationService.reset_password(user.id)
        return ResponseData.success(RESPONSE_MSG_0289)

    @error_response('user')
    @action(methods=['POST'], detail=False)
    def menu(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0044, ad_routes())

    @error_response('user')
    @action(methods=['get'], detail=False)
    def test(self, request: Request):
        v = request.query_params.get('v')
        if v:
            from version_migration_scripts import data_cleanup
            cleanup_kwargs = {
                key: value
                for key, value in request.query_params.items()
                if key != 'v'
            }
            result = data_cleanup(v, **cleanup_kwargs)
            return ResponseData.success(RESPONSE_MSG_0045, result)
        else:
            return ResponseData.success(RESPONSE_MSG_0044, {'title': ''})

    @error_response('user')
    @action(methods=['get'], detail=False)
    def test2(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0001, {})

    @error_response('user')
    @action(methods=['get'], detail=False)
    def get_download(self, request: Request):
        file_name = unquote(request.query_params.get('file_name') or '')
        safe_file_name = os.path.basename(file_name)
        if not safe_file_name or safe_file_name != file_name:
            return ResponseData.fail(RESPONSE_MSG_0241)
        file_path = os.path.join(settings.STATIC_RESOURCE_DIR, safe_file_name)
        if not os.path.isfile(file_path):
            return ResponseData.fail(RESPONSE_MSG_0242)
        response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=safe_file_name)
        return response


class MenuViews(ViewSet):
    @error_response('user')
    @action(methods=['POST'], detail=False)
    def menu(self, request: Request):
        return ResponseData.success(RESPONSE_MSG_0044, PermissionMenuService.permitted_menu(request.user.user_obj))

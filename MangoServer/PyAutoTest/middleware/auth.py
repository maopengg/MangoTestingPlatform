# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 授权
# @Time   : 2023-03-01 21:32
# @Author : 毛鹏
import jwt
from django.conf import settings
from jwt import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed


class JwtQueryParamsAuthentication(BaseAuthentication):

    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION')
        salt = settings.SECRET_KEY
        # 1.切割
        # 2.解密第二段，判断过期
        # 3.验证第三段合法性
        try:
            payload = jwt.decode(token, salt, algorithms='HS256')
        except exceptions.ExpiredSignatureError:
            raise AuthenticationFailed({'code': 301, 'msg': '当前用户登录已过期，请重新登录', 'data': ''})
        except jwt.DecodeError:
            raise AuthenticationFailed({'code': 302, 'msg': '当前用户登录已过期，请重新登录', 'data': ''})
        except jwt.InvalidTokenError:
            raise AuthenticationFailed({'code': 303, 'msg': '哈哈哈，被我发现了，请不要使用非法token', 'data': ''})
        return payload, token

    def authenticate_header(self, request):
        """这个方法暂时不知道干啥，不加保存，加上不用先"""
        pass

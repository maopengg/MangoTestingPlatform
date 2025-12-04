# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 授权
# @Time   : 2023-03-01 21:32
# @Author : 毛鹏
import jwt
from django.conf import settings
from jwt import exceptions
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from src.auto_test.auto_user.models import User

class JwtQueryParamsAuthentication(BaseAuthentication):

    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION')
        if not token:
            raise AuthenticationFailed({'code': 300, 'msg': '未提供 token', 'data': None})
        salt = settings.SECRET_KEY
        # 1.切割
        # 2.解密第二段，判断过期
        # 3.验证第三段合法性
        try:
            payload = jwt.decode(token, salt, algorithms='HS256')
            User.objects.get(id=payload['id'])
        except User.DoesNotExist:
            raise AuthenticationFailed({'code': 300, 'msg': '没有该用户信息，请重新登录', 'data': None})
        except exceptions.ExpiredSignatureError:
            raise AuthenticationFailed({'code': 301, 'msg': '当前用户登录已过期，请重新登录', 'data': None})
        except jwt.DecodeError:
            raise AuthenticationFailed({'code': 302, 'msg': 'token 无效，请检查后重试', 'data': None})
        except jwt.InvalidTokenError:
            raise AuthenticationFailed({'code': 303, 'msg': 'token 非法，请使用有效的 token', 'data': None})
        except Exception as e:
            
            raise AuthenticationFailed({'code': 304, 'msg': f'token 验证失败: {str(e)}', 'data': None})
        return payload, token

    def authenticate_header(self, request):
        """这个方法暂时不知道干啥，不加保存，加上不用先"""
        pass

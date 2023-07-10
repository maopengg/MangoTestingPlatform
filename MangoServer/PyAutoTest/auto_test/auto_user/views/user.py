# Create your views here.

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.views.menu import ad_routes
from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.role import RoleSerializers
from PyAutoTest.middleware.utlis.jwt_auth import create_token
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD


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
        return Response({
            'code': 200,
            'msg': '获取数据成功',
            'data': data
        })


class LoginViews(ViewSet):
    authentication_classes = []

    @action(methods=['post'], detail=False)
    def login(self, request: Request):
        username = request.data.get('username')
        password = request.data.get('password')
        user_info = User.objects.filter(username=username, password=password).first()
        if not user_info:
            return Response({
                'code': 302,
                'msg': '用户名或密码错误',
                'data': ''
            })
        token = create_token({'id': user_info.id, 'username': user_info.username})
        return Response({
            "code": 200,
            "data": {
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
            },
            "msg": "登录成功"
        })

    @action(methods=['get'], detail=False)
    def menu(self, request: Request):
        dic = ad_routes()
        return Response({
            'code': 200,
            'data': dic,
            'msg': '获取菜单列表成功'
        })

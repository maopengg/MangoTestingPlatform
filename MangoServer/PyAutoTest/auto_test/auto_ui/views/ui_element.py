# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-01-15 22:06
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiElement
from PyAutoTest.auto_test.auto_ui.models import UiPage
from PyAutoTest.auto_test.auto_ui.ui_tools.enum import WebExp
from PyAutoTest.auto_test.auto_user.models import Project
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageSerializers
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD
from PyAutoTest.utils.view_utils.view_tools import option_list, enum_list


class UiElementSerializers(serializers.ModelSerializer):
    team = ProjectSerializers()
    page = UiPageSerializers()

    class Meta:
        model = UiElement
        fields = '__all__'  # 全部进行序列化
        # fields = ['project']  # 选中部分进行序列化
        # exclude = ['name']  # 除了这个字段，其他全序列化

    def create(self, validated_data):
        page_id = validated_data.pop('page')
        team_id = validated_data.pop('team')
        page = UiPage.objects.get(name=page_id)
        team = Project.objects.get(name=team_id)
        ui_element = UiElement.objects.create(page=page, team=team, **validated_data)
        return ui_element

    def update(self, instance, validated_data):
        page_id = validated_data.pop('page', None)
        team_id = validated_data.pop('team', None)
        if page_id:
            page = UiPage.objects.get(name=page_id)
            instance.page = page
        if team_id:
            team = Project.objects.get(name=team_id)
            instance.team = team
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance


class UiElementCRUD(ModelCRUD):
    model = UiElement
    queryset = UiElement.objects.select_related('team', 'page').all()
    serializer_class = UiElementSerializers

    def get(self, request):
        try:
            books = self.model.objects.filter(page_id=request.query_params.get('page_name')).order_by('id')
            return Response({
                "code": 200,
                "msg": "获取数据成功~",
                "data": self.get_serializer_class()(instance=books, many=True).data,
                'totalSize': len(books)
            })
        except:
            return Response({
                'code': 300,
                'msg': '您查询的数据不存在~',
                'data': ''
            })


class UiElementViews(ViewSet):

    @action(methods=['get'], detail=False)
    def get_ele_name(self, request):
        """
        获取
        :param request:
        :return:
        """
        return Response({
            'code': 200,
            'msg': '获取数据成功~',
            'data': option_list(UiElement.objects.filter(page=request.query_params.get('name')))
        })

    @action(methods=['get'], detail=False)
    def get_exp_type(self, request):
        """
        获取操作类型
        :param request:
        :return:
        """
        return Response({
            'code': 200,
            'msg': '获取数据成功~',
            'data': enum_list(WebExp)
        })

# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
import json
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import RunSort, UiCase
from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_element import UiElementSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page import UiPageSerializers
from PyAutoTest.utils.cache_utils.redis_base import RedisBase
from PyAutoTest.utils.view_utils.model_crud import ModelCRUD

logger = logging.getLogger('ui')


class RunSortSerializers(serializers.ModelSerializer):
    class Meta:
        model = RunSort
        fields = '__all__'


class RunSortSerializersC(serializers.ModelSerializer):
    el_page = UiPageSerializers(read_only=True)
    el_name = UiElementSerializers(read_only=True)
    el_name_b = UiElementSerializers(read_only=True)
    case = UiCaseSerializers(read_only=True)

    class Meta:
        model = RunSort
        fields = '__all__'


class RunSortCRUD(ModelCRUD):
    """
        haha
    """
    model = RunSort
    queryset = RunSort.objects.all().order_by('run_sort')
    serializer_class = RunSortSerializersC
    serializer = RunSortSerializers

    def get(self, request: Request):
        books = self.model.objects.filter(case_id=request.GET.get('case_id')).order_by('run_sort')
        data = [self.serializer_class(i).data for i in books]
        return Response({
            "code": 200,
            "msg": "获取数据成功",
            "data": data
        })

    def callback(self, _id):
        data = {'id': _id, 'run_flow': '', 'name': ''}
        run = self.model.objects.filter(case_id=_id).order_by('run_sort')
        for i in run:
            data['run_flow'] += '->'
            if i.el_name:
                data['run_flow'] += i.el_name.name
            else:
                data['run_flow'] += i.ope_type
        data['name'] = run[0].case.name
        from PyAutoTest.auto_test.auto_ui.views.ui_case import UiCaseCRUD
        ui_case = UiCaseCRUD()
        res = ui_case.serializer(instance=UiCase.objects.get(pk=_id), data=data)
        if res.is_valid():
            res.save()
        else:
            logger.error(f'保存用例执行顺序报错！，报错结果：{str(res.errors)}')


class RunSortView(ViewSet):
    model = RunSort
    serializer_class = RunSortSerializers

    @action(methods=['get'], detail=False)
    def get_ope_type(self, request: Request):
        redis = RedisBase('default')
        data = redis.get('PageElementOperations')
        return Response({
            'code': 200,
            'msg': '获取操作类型成功',
            'data': json.loads(data)
        })
        # return Response({
        #     'code': 200,
        #     'msg': '获取操作类型成功',
        #     'data': enum_list(OpeType)
        # })

    @action(methods=['get'], detail=False)
    def get_ass_type(self, request: Request):
        redis = RedisBase('default')
        data = redis.get('PageElementAssertion')
        return Response({
            'code': 200,
            'msg': '获取断言类型成功',
            'data': json.loads(data)
        })
        # return Response({
        #     'code': 200,
        #     'msg': '获取断言类型成功',
        #     'data': enum_list(Assertions)
        # })

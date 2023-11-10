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
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiPageStepsDetailed, UiPageSteps
from PyAutoTest.auto_test.auto_ui.views.ui_element import UiElementSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import UiPageStepsSerializers
from PyAutoTest.enums.ui_enum import DevicePlatform
from PyAutoTest.tools.cache_utils.redis_base import RedisBase
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD

logger = logging.getLogger('ui')


class UiPageStepsDetailedSerializers(serializers.ModelSerializer):
    class Meta:
        model = UiPageStepsDetailed
        fields = '__all__'


class UiPageStepsDetailedSerializersC(serializers.ModelSerializer):
    page_step = UiPageStepsSerializers(read_only=True)
    ele_name_a = UiElementSerializers(read_only=True)
    ele_name_b = UiElementSerializers(read_only=True)

    class Meta:
        model = UiPageStepsDetailed
        fields = '__all__'


class UiPageStepsDetailedCRUD(ModelCRUD):
    """
        haha
    """
    model = UiPageStepsDetailed
    queryset = UiPageStepsDetailed.objects.all().order_by('step_sort')
    serializer_class = UiPageStepsDetailedSerializersC
    serializer = UiPageStepsDetailedSerializers

    def get(self, request: Request):
        books = self.model.objects.filter(page_step_id=request.GET.get('page_step_id')).order_by('step_sort')
        data = [self.serializer_class(i).data for i in books]
        return ResponseData.success('获取数据成功', data)

    def callback(self, _id):
        """
        步骤id查询后排序
        """
        data = {'id': _id, 'run_flow': '', 'name': ''}
        run = self.model.objects.filter(page_step=_id).order_by('step_sort')
        for i in run:
            data['run_flow'] += '->'
            if i.ele_name_a:
                data['run_flow'] += i.ele_name_a.name
            else:
                data['run_flow'] += i.ope_type
        data['name'] = run[0].page_step.name
        from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import UiPageStepsCRUD
        ui_case = UiPageStepsCRUD()
        res = ui_case.serializer(instance=UiPageSteps.objects.get(pk=_id), data=data)
        if res.is_valid():
            res.save()
        else:
            logger.error(f'保存用例执行顺序报错！，报错结果：{str(res.errors)}')


class UiPageStepsDetailedView(ViewSet):
    model = UiPageStepsDetailed
    serializer_class = UiPageStepsDetailedSerializers

    @action(methods=['get'], detail=False)
    def get_ope_type(self, request: Request):
        page_type = int(request.query_params.get('page_type'))
        redis = RedisBase('default')
        if page_type == DevicePlatform.WEB.value:
            data = json.loads(redis.get('PlaywrightElementOperation'))
        elif page_type == DevicePlatform.ANDROID.value:
            data = json.loads(redis.get('UiautomatorApplication'))
        elif page_type == DevicePlatform.DESKTOP.value:
            data = json.loads(redis.get('DESKTOP_OPE'))
        else:
            data = json.loads(redis.get('IOS_OPE'))
        return ResponseData.success('获取操作类型成功', data)

    @action(methods=['get'], detail=False)
    def get_ass_type(self, request: Request):
        page_type = int(request.query_params.get('page_type'))

        redis = RedisBase('default')
        if page_type == DevicePlatform.WEB.value:
            data = json.loads(redis.get('PlaywrightAssertion'))
        elif page_type == DevicePlatform.ANDROID.value:
            data = json.loads(redis.get('UiautomatorAssertion'))
        elif page_type == DevicePlatform.DESKTOP.value:
            data = json.loads(redis.get('DESKTOP_ASS'))
        else:
            data = json.loads(redis.get('IOS_ASS'))
        data.append({'value': 'PublicAssertion',
                     'label': '元素文本',
                     'children': json.loads(redis.get('PublicAssertion'))})

        return ResponseData.success('获取断言类型成功', data)

    @action(methods=['get'], detail=False)
    def get_ass_method(self, request: Request):
        redis = RedisBase('default')
        data = redis.get('assertion')
        return ResponseData.success('获取断言类型成功', json.loads(data))

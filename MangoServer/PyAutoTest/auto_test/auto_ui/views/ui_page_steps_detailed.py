# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.service.cache_data_value import CacheDataValue
from PyAutoTest.auto_test.auto_ui.models import UiPageStepsDetailed, UiPageSteps
from PyAutoTest.auto_test.auto_ui.views.ui_element import UiElementSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import UiPageStepsSerializers
from PyAutoTest.enums.system_enum import CacheDataKey2Enum
from PyAutoTest.enums.ui_enum import DriveTypeEnum
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *

log = logging.getLogger('ui')


class UiPageStepsDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiPageStepsDetailed
        fields = '__all__'


class UiPageStepsDetailedSerializersC(serializers.ModelSerializer):
    page_step = UiPageStepsSerializers(read_only=True)
    ele_name = UiElementSerializers(read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

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
        page_step_id = request.GET.get('page_step_id')
        _id = request.GET.get('id')
        if page_step_id:
            books = self.model.objects.filter(page_step_id=page_step_id).order_by('step_sort')
        else:
            books = self.model.objects.filter(id=_id).order_by('step_sort')
        data = [self.serializer_class(i).data for i in books]
        return ResponseData.success(RESPONSE_MSG_0016, data)

    def callback(self, _id):
        """
        排序
        @param _id: 步骤id
        @return:
        """
        data = {'id': _id, 'run_flow': '', 'name': ''}
        run = self.model.objects.filter(page_step=_id).order_by('step_sort')
        for i in run:
            data['run_flow'] += '->'
            if i.ele_name:
                data['run_flow'] += i.ele_name.name
            else:
                data['run_flow'] += i.ope_type if i.ope_type else '无元素操作'
        data['name'] = run[0].page_step.name
        from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import UiPageStepsCRUD
        ui_case = UiPageStepsCRUD()
        res = ui_case.serializer(instance=UiPageSteps.objects.get(pk=_id), data=data)
        if res.is_valid():
            res.save()
        else:
            log.error(f'保存用例执行顺序报错！，报错结果：{str(res.errors)}')


class UiPageStepsDetailedView(ViewSet):
    model = UiPageStepsDetailed
    serializer_class = UiPageStepsDetailedSerializers

    @action(methods=['get'], detail=False)
    def get_ope_type(self, request: Request):
        page_type = request.query_params.get('page_type')
        # redis = RedisBase('default')
        data = []
        if not page_type:
            data.append({
                'value': 'all',
                'label': '请选择操作端',
                'children': CacheDataValue.get_cache_value(key=CacheDataKey2Enum.PLAYWRIGHT_OPERATION_METHOD.value)
            })
            ui_auto = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.UIAUTOMATOR_OPERATION_METHOD.value)
            if ui_auto:
                data.append({
                    'value': 'all',
                    'label': '请选择操作端',
                    'children': ui_auto
                })
            # desktop = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.DESKTOP_OPERATION_METHOD.value)
            # if desktop:
            #     data.append({
            #         'value': 'all',
            #         'label': '请选择操作端',
            #         'children': desktop
            #     })
            # ios = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.IOS_OPERATION_METHOD.value)
            # if ios:
            #     data.append({
            #         'value': 'all',
            #         'label': '请选择操作端',
            #         'children': ios
            #     })
            return ResponseData.success(RESPONSE_MSG_0017, data)
        if int(page_type) == DriveTypeEnum.WEB.value:
            data = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.PLAYWRIGHT_OPERATION_METHOD.value)
        elif int(page_type) == DriveTypeEnum.ANDROID.value:
            data = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.UIAUTOMATOR_OPERATION_METHOD.value)
        # elif int(page_type) == DriveTypeEnum.DESKTOP.value:
        #     data = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.DESKTOP_OPERATION_METHOD.value)
        #
        # else:
        #     data = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.IOS_OPERATION_METHOD.value)

        return ResponseData.success(RESPONSE_MSG_0017, data)

    @action(methods=['get'], detail=False)
    def get_ass_type(self, request: Request):
        page_type = request.query_params.get('page_type')
        # redis = RedisBase('default')
        if page_type:
            if int(page_type) == DriveTypeEnum.WEB.value:
                data = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.PLAYWRIGHT_ASSERTION_METHOD.value)
            elif int(page_type) == DriveTypeEnum.ANDROID.value:
                data = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.UIAUTOMATOR_ASSERTION_METHOD.value)
            elif int(page_type) == DriveTypeEnum.DESKTOP.value:
                data = CacheDataValue.get_cache_value(key='DESKTOP_ASS')
            else:
                data = CacheDataValue.get_cache_value(key='IOS_ASS')
            data.append({'value': 'PublicAssertion',
                         'label': '元素文本',
                         'children': CacheDataValue.get_cache_value(
                             key=CacheDataKey2Enum.PUBLIC_ASSERTION_METHOD.value)})
            data.append(CacheDataValue.get_cache_value(key=CacheDataKey2Enum.SQL_ASSERTION_METHOD.value)[0])
        else:
            data = CacheDataValue.get_cache_value(key=CacheDataKey2Enum.PUBLIC_ASSERTION_METHOD.value)
        return ResponseData.success(RESPONSE_MSG_0018, data)

    @action(methods=['get'], detail=False)
    def get_ass_method(self, request: Request):
        """
        获取断言类型
        @param request:
        @return:
        """
        # redis = RedisBase('default')
        return ResponseData.success(RESPONSE_MSG_0019,
                                    CacheDataValue.get_cache_value(key=CacheDataKey2Enum.ASSERTION_METHOD.value))

    @action(methods=['put'], detail=False)
    def put_step_sort(self, request: Request):
        """
        修改排序
        @param request:
        @return:
        """
        page_step_id = None

        for i in request.data.get('step_sort_list'):
            obj = self.model.objects.get(id=i['id'])
            obj.step_sort = i['step_sort']
            page_step_id = obj.page_step.id
            obj.save()
        UiPageStepsDetailedCRUD().callback(page_step_id)
        return ResponseData.success(RESPONSE_MSG_0020, )

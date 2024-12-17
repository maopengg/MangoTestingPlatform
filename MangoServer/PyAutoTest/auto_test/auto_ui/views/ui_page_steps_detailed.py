# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏

from django.core.exceptions import FieldError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_system.service.cache_data_value import CacheDataValue
from PyAutoTest.auto_test.auto_ui.models import PageStepsDetailed
from PyAutoTest.auto_test.auto_ui.views.ui_element import PageElementSerializers
from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import PageStepsSerializers
from PyAutoTest.enums.system_enum import CacheDataKey2Enum
from PyAutoTest.enums.ui_enum import DriveTypeEnum, ElementOperationEnum
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class PageStepsDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageStepsDetailed
        fields = '__all__'


class PageStepsDetailedSerializersC(serializers.ModelSerializer):
    page_step = PageStepsSerializers(read_only=True)
    ele_name = PageElementSerializers(read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageStepsDetailed
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'page_step',
            'ele_name')
        return queryset


class PageStepsDetailedCRUD(ModelCRUD):
    """
        haha
    """
    model = PageStepsDetailed
    queryset = PageStepsDetailed.objects.all().order_by('step_sort')
    serializer_class = PageStepsDetailedSerializersC
    serializer = PageStepsDetailedSerializers

    @error_response('ui')
    def get(self, request: Request):
        page_step_id = request.GET.get('page_step_id')
        _id = request.GET.get('id')
        if page_step_id:
            books = self.model.objects.filter(page_step_id=page_step_id).order_by('step_sort')
        else:
            books = self.model.objects.filter(id=_id).order_by('step_sort')

        try:
            books = self.serializer_class.setup_eager_loading(books)
        except FieldError:
            pass
        return ResponseData.success(RESPONSE_MSG_0016,
                                    self.serializer_class(instance=books,
                                                          many=True).data)

    def callback(self, _id):
        """
        排序
        @param _id: 步骤id
        @return:
        """
        data = {'id': _id, 'run_flow': ''}
        run = self.model.objects.filter(page_step=_id).order_by('step_sort')
        for i in run:
            data['run_flow'] += '->'
            if i.ele_name:
                data['run_flow'] += i.ele_name.name
            else:
                if i.type == ElementOperationEnum.CUSTOM.value:
                    data['run_flow'] += '参数'
                elif i.type == ElementOperationEnum.SQL.value:
                    data['run_flow'] += 'SQL'
                else:
                    data['run_flow'] += i.ope_key if i.ope_key else '无元素操作'
        from PyAutoTest.auto_test.auto_ui.views.ui_page_steps import PageStepsCRUD
        PageStepsCRUD.inside_put(data['id'], data)


class PageStepsDetailedView(ViewSet):
    model = PageStepsDetailed
    serializer_class = PageStepsDetailedSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
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
    @error_response('ui')
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
    @error_response('ui')
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
    @error_response('ui')
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
        PageStepsDetailedCRUD().callback(page_step_id)
        return ResponseData.success(RESPONSE_MSG_0020, )

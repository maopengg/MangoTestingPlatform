# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-01-15 10:56
# @Author : 毛鹏
import json

from django.core.exceptions import FieldError
from mangotools.mangos import get_execution_order_with_config_ids
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.exceptions import ToolsError
from src.auto_test.auto_system.models import CacheData
from src.auto_test.auto_system.service.cache_data_value import CacheDataValue
from src.auto_test.auto_ui.models import PageStepsDetailed, PageSteps
from src.auto_test.auto_ui.service.query_ope_key_name import get_by_object
from src.auto_test.auto_ui.views.ui_element import PageElementSerializers
from src.enums.system_enum import CacheDataKey2Enum
from src.enums.ui_enum import DriveTypeEnum, ElementOperationEnum
from src.tools.decorator.error_response import error_response
from src.tools.view.model_crud import ModelCRUD
from src.tools.view.response_data import ResponseData
from src.tools.view.response_msg import *


class PageStepsDetailedSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageStepsDetailed
        fields = '__all__'


class PageStepsDetailedSerializersC(serializers.ModelSerializer):
    # page_step = PageStepsSerializers(read_only=True)
    ele_name = PageElementSerializers(read_only=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = PageStepsDetailed
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            # 'page_step',
            'ele_name')
        return queryset


class PageStepsDetailedCRUD(ModelCRUD):
    """
        haha
    """
    model = PageStepsDetailed
    queryset = PageStepsDetailed.objects.all()
    serializer_class = PageStepsDetailedSerializersC
    serializer = PageStepsDetailedSerializers

    @error_response('ui')
    def get(self, request: Request):
        page_step_id = request.GET.get('page_step_id')
        _id = request.GET.get('id')
        if page_step_id:
            books = self.model.objects.filter(page_step_id=page_step_id)
        else:
            books = self.model.objects.filter(id=_id)
        try:
            books = self.serializer_class.setup_eager_loading(books)
        except FieldError:
            pass
        return ResponseData.success(
            RESPONSE_MSG_0016,
            self.serializer_class(instance=books, many=True).data
        )

    @error_response('ui')
    def post(self, request: Request):
        from src.auto_test.auto_ui.views.ui_page_steps import PageStepsCRUD
        if request.data.get('id') is not None:
            data = self.inside_put(request.data.get('id'), request.data)
        else:
            data = self.inside_post(request.data)
        flow_data = request.data.get('flow_data')
        for i in flow_data.get('nodes'):
            if i.get('id') == request.data.get('node_id'):
                i['config']['id'] = data.get('id')
        PageStepsCRUD.inside_put(request.data.get('page_step'), {'flow_data': flow_data})
        self.asynchronous_callback(request.data.get('parent_id'))
        return ResponseData.success(RESPONSE_MSG_0035, data)

    @error_response('ui')
    def callback(self, _id):
        """
        排序
        @param _id: 步骤id
        @return:
        """
        page_steps = PageSteps.objects.get(id=_id)
        try:
            flow_data = get_execution_order_with_config_ids(page_steps.flow_data)
        except KeyError:
            import traceback
            traceback.print_exc()
            pass
        else:
            run_flow = ''
            select_value = json.loads(CacheData.objects.get(key='select_value').value)
            for __id in flow_data:
                try:
                    flow = self.model.objects.get(id=__id)
                    run_flow += '->'
                    if flow.ele_name:
                        run_flow += flow.ele_name.name
                    else:
                        if flow.ope_key:
                            label = get_by_object(select_value, flow.ope_key)
                            run_flow += flow.ope_key if label is None else label.get('label')
                        else:
                            run_flow += ElementOperationEnum.get_value(flow.type)
                except PageStepsDetailed.DoesNotExist:
                    pass
            page_steps.run_flow = run_flow
            page_steps.save()


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

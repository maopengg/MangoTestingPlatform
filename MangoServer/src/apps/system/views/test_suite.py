# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.apps.system.models import NoticeGroup, TestSuite
from src.apps.system.service.test_suite.base_notice import NoticeMain
from src.apps.system.views.product_module import ProductModuleSerializers
from src.apps.system.views.project_product import ProjectProductSerializersC
from src.apps.system.views.tasks import TasksSerializers
from src.apps.user.views.user import UserSerializers
from src.common.enums.system_enum import TestSuiteNoticeEnum
from src.common.enums.tools_enum import StatusEnum
from src.common.tools.decorator.error_response import error_response
from src.common.tools.view.model_crud import ModelCRUD
from src.common.tools.view.response_data import ResponseData
from src.common.tools.view.response_msg import *


class TestSuiteSerializers(serializers.ModelSerializer):
    id = serializers.IntegerField()
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TestSuite
        fields = '__all__'


class TestSuiteSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    tasks = TasksSerializers(read_only=True)
    user = UserSerializers(read_only=True)

    class Meta:
        model = TestSuite
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'project_product__project',
            'module',
            'tasks',
            'user',
        )
        return queryset


class TestSuiteCRUD(ModelCRUD):
    model = TestSuite
    queryset = TestSuite.objects.all()
    serializer_class = TestSuiteSerializersC
    serializer = TestSuiteSerializers
    # @error_response('system')
    # def get(self, request: Request):
    #     return ResponseData.success('')


class TestSuiteViews(ViewSet):
    model = TestSuite
    serializer_class = TestSuiteSerializers

    @action(methods=['post'], detail=False)
    @error_response('system')
    def send_notice(self, request: Request):
        test_suite = self.model.objects.select_related(
            'tasks',
            'tasks__notice_group',
            'project_product',
            'project_product__project',
        ).get(id=request.data.get('id'))
        if test_suite.status not in [StatusEnum.SUCCESS.value, StatusEnum.FAIL.value]:
            return ResponseData.fail(RESPONSE_MSG_0198)

        notice_group_id = request.data.get('notice_group')
        if not notice_group_id and test_suite.tasks and test_suite.tasks.notice_group_id:
            notice_group_id = test_suite.tasks.notice_group_id
        if not notice_group_id:
            return ResponseData.fail(RESPONSE_MSG_0199)

        notice_group = NoticeGroup.objects.get(id=notice_group_id)
        if notice_group.project_id != test_suite.project_product.project_id:
            return ResponseData.fail(RESPONSE_MSG_0200)

        test_suite.is_notice = TestSuiteNoticeEnum.SENDING.value
        test_suite.save(update_fields=['is_notice', 'update_time'])
        try:
            NoticeMain(int(notice_group_id)).notice_main(test_suite.id)
        except Exception:
            test_suite.is_notice = TestSuiteNoticeEnum.NOT_SENT.value
            test_suite.save(update_fields=['is_notice', 'update_time'])
            raise
        test_suite.is_notice = TestSuiteNoticeEnum.SENT.value
        test_suite.save(update_fields=['is_notice', 'update_time'])
        return ResponseData.success(RESPONSE_MSG_0197)

# -*- coding: utf-8 -*-
# @Project: MangoServer
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from django.db.models import Count
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_system.models import TestSuiteReport
from PyAutoTest.auto_test.auto_ui.models import UiCase
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.tools.response_data import ResponseData
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD


class TestSuiteReportSerializers(serializers.ModelSerializer):
    id = serializers.IntegerField()
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TestSuiteReport
        fields = '__all__'


class TestSuiteReportSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)

    class Meta:
        model = TestSuiteReport
        fields = '__all__'


class TestSuiteReportCRUD(ModelCRUD):
    model = TestSuiteReport
    queryset = TestSuiteReport.objects.all()
    serializer_class = TestSuiteReportSerializersC
    serializer = TestSuiteReportSerializers


class TestSuiteReportViews(ViewSet):
    model = TestSuiteReport
    serializer_class = TestSuiteReportSerializers

    @action(methods=['get'], detail=False)
    def get_all_report_sum(self, request: Request):
        """
        获取三个类型的总数
        @param request:
        @return:
        """
        result = self.model.objects.values('type').annotate(total=Count('type')).values('type', 'total')
        # # 访问结果
        # return ResponseData.success('获取数据成功', [{"ui": item['total']} if item['type'] == 0 else
        #                                        {"api": item['total']} if item['type'] == 1 else {
        #                                            "perf": item['total']} for item in result])
        api = 0
        ui = 0
        perf = 0
        for item in result:
            if item['type'] == AutoTestTypeEnum.UI.value:
                ui = item['total']
            elif item['type'] == AutoTestTypeEnum.API.value:
                api = item['total']
            else:
                perf = item['total']

        return ResponseData.success('获取数据成功',
                                    [
                                        {'value': api, 'name': AutoTestTypeEnum.get(AutoTestTypeEnum.UI.value)},
                                        {'value': ui, 'name': AutoTestTypeEnum.get(AutoTestTypeEnum.API.value)},
                                        {'value': perf, 'name': AutoTestTypeEnum.get(AutoTestTypeEnum.PERF.value)}
                                    ])

    @action(methods=['get'], detail=False)
    def get_all_case_sum(self, request: Request):
        """
        获取所有用例的总数
        @param request:
        @return:
        """

        return ResponseData.success('获取数据成功',
                                    [
                                        {'value': UiCase.objects.count(),
                                         'name': AutoTestTypeEnum.get(AutoTestTypeEnum.UI.value)},
                                        {'value': ApiCase.objects.count(),
                                         'name': AutoTestTypeEnum.get(AutoTestTypeEnum.API.value)},
                                        {'value': 1, 'name': AutoTestTypeEnum.get(AutoTestTypeEnum.PERF.value)}
                                    ])

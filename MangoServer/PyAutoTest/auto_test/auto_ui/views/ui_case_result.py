# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-03-25 18:53
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_ui.models import UiCaseResult, UiPageStepsResult
from PyAutoTest.auto_test.auto_user.views.product_module import ProductModuleSerializers
from PyAutoTest.auto_test.auto_user.views.project import ProjectSerializers
from PyAutoTest.auto_test.auto_user.views.user import UserSerializers
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class UiCaseResultSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = UiCaseResult
        fields = '__all__'


class UiCaseResultSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project = ProjectSerializers(read_only=True)
    module = ProductModuleSerializers(read_only=True)
    case_people = UserSerializers(read_only=True)

    class Meta:
        model = UiCaseResult
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project',
            'module',
            'case_people')
        return queryset


class UiCaseResultCRUD(ModelCRUD):
    model = UiCaseResult
    queryset = UiCaseResult.objects.all()
    serializer_class = UiCaseResultSerializersC
    serializer = UiCaseResultSerializers


class UiCaseResultViews(ViewSet):
    model = UiCaseResult
    serializer_class = UiCaseResultSerializers

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def suite_get_case(self, request: Request):
        case_result = UiCaseResult.objects.filter(test_suite_id=request.query_params.get('test_suite_id'))
        data = []
        for i in case_result:
            page_steps_result = UiPageStepsResult.objects.filter(
                test_suite_id=request.query_params.get('test_suite_id'),
                case_id=i.case_id)
            case_result_obj = {
                'title': i.case_name,
                'status': i.status,
                'key': f'{"{"}"test_suite_id":{i.test_suite_id},"ui_case_result":{i.id},"case_id":{i.case_id}{"}"}',
                'children': [
                    {'title': e.page_step_name,
                     'status': e.status,
                     'key': f'{"{"}"test_suite_id":{e.test_suite_id},"page_steps_result":{e.id},"case_id":{i.case_id},"page_step_id":{e.page_step_id}{"}"}',
                     'children': []
                     } for e in page_steps_result]
            }
            data.append(case_result_obj)
        summary = [
            {'name': '用例总数', 'value': case_result.count()},
            {'name': '成功', 'value': case_result.filter(status=StatusEnum.SUCCESS.value).count()},
            {'name': '警告', 'value': case_result.filter(status=2).count()},
            {'name': '失败', 'value': case_result.filter(status=StatusEnum.FAIL.value).count()}
        ]
        return ResponseData.success(RESPONSE_MSG_0083, {'data': data, 'summary': summary})

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def get_case_res(self, request: Request):
        data = self.model.objects.filter(test_suite_id=request.query_params.get('test_suite_id'))
        return ResponseData.success(RESPONSE_MSG_0083, data)

    @action(methods=['get'], detail=False)
    @error_response('ui')
    def case_result_week_sum(self, request: Request):
        """
        获取三个类型的总数
        @param request:
        @return:
        """
        ui_result = UiCaseResult.objects.raw(
            """
            SELECT
                weeks.id,
                weeks.yearweek,
                COALESCE(api_counts.total_count, 0) AS total_count,
                COALESCE(api_counts.status_0_total, 0) AS status_0_total,
                COALESCE(api_counts.status_1_total, 0) AS status_1_total
            FROM (
                SELECT 'id' as id, YEARWEEK(DATE_SUB(NOW(), INTERVAL n WEEK)) AS yearweek
                FROM (
                    SELECT 0 AS n UNION ALL
                    SELECT 1 UNION ALL
                    SELECT 2 UNION ALL
                    SELECT 3 UNION ALL
                    SELECT 4 UNION ALL
                    SELECT 5 UNION ALL
                    SELECT 6 UNION ALL
                    SELECT 7 UNION ALL
                    SELECT 8 UNION ALL
                    SELECT 9 UNION ALL
                    SELECT 10 UNION ALL
                    SELECT 11
                ) weeks
            ) weeks
            LEFT JOIN (
                SELECT 
                    MAX(ui_case_result.id) as id,
                    YEARWEEK(create_time) AS yearweek, 
                    COUNT(YEARWEEK(create_time)) AS total_count,
                    SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) AS status_0_total,
                    SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS status_1_total
                FROM ui_case_result
                WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
                GROUP BY YEARWEEK(create_time)
            ) api_counts ON weeks.yearweek = api_counts.yearweek
            ORDER BY weeks.yearweek;
        """
        )
        result_dict = {
            'success': [],
            'fail': []
        }
        for row in ui_result:
            result_dict['success'].append(row.status_1_total)
        for row in ui_result:
            result_dict['fail'].append(row.status_0_total)
        result_dict['successSun'] = sum(result_dict['success'])
        result_dict['failSun'] = sum(result_dict['fail'])
        return ResponseData.success(RESPONSE_MSG_0091, result_dict)

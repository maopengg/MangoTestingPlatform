# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCaseResult, ApiInfoResult
from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseSerializers
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoSerializers
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.model_crud import ModelCRUD
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class ApiCaseResultSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiCaseResult
        fields = '__all__'


class ApiCaseResultSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case = ApiCaseSerializers(read_only=True)
    api_info = ApiInfoSerializers(read_only=True)

    class Meta:
        model = ApiCaseResult
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'case',
            'api_info')
        return queryset


class ApiCaseResultCRUD(ModelCRUD):
    model = ApiCaseResult
    queryset = ApiCaseResult.objects.all()
    serializer_class = ApiCaseResultSerializersC
    serializer = ApiCaseResultSerializers


class ApiCaseResultViews(ViewSet):
    model = ApiCaseResult
    serializer_class = ApiCaseResultSerializers

    @action(methods=['get'], detail=False)
    @error_response('api')
    def suite_case_result(self, request: Request):
        test_suite_id = request.query_params.get('test_suite_id')
        api_case_result_list = self.model.objects.filter(test_suite_id=test_suite_id).order_by('create_time')
        data = []
        for api_case_result in api_case_result_list:
            case_result_obj = {
                'title': api_case_result.case.name,
                'status': api_case_result.status,
                'key': f'1-{api_case_result.id}',
                'children': []
            }
            api_info_result_list = ApiInfoResult.objects.filter(test_suite_id=test_suite_id,
                                                                case=api_case_result.case.id).order_by('case_sort')
            for api_info_result in api_info_result_list:
                case_result_obj['children'].append({
                    'title': api_info_result.api_info.name,
                    'status': api_info_result.status,
                    'key': f'2-{api_info_result.id}',
                    'children': []
                })
            data.append(case_result_obj)

        summary = [
            {'name': '用例总数', 'value': api_case_result_list.count()},
            {'name': '成功', 'value': api_case_result_list.filter(status=StatusEnum.SUCCESS.value).count()},
            {'name': '警告', 'value': api_case_result_list.filter(status=2).count()},
            {'name': '失败', 'value': api_case_result_list.filter(status=StatusEnum.FAIL.value).count()}
        ]
        return ResponseData.success(RESPONSE_MSG_0083, {'data': data, 'summary': summary})

    @action(methods=['get'], detail=False)
    @error_response('api')
    def case_result_week_sum(self, request: Request):
        """
        获取三个类型的总数
        @param request:
        @return:
        """
        ui_result = self.model.objects.raw(
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
                    MAX(api_case_result.id) as id,
                    YEARWEEK(create_time) AS yearweek, 
                    COUNT(YEARWEEK(create_time)) AS total_count,
                    SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) AS status_0_total,
                    SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS status_1_total
                FROM api_case_result
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
        return ResponseData.success(RESPONSE_MSG_0084, result_dict)

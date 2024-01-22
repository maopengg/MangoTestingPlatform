# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-11-13 10:42
# @Author : 毛鹏
import logging

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiResult
from PyAutoTest.auto_test.auto_api.views.api_case import ApiCaseSerializers
from PyAutoTest.auto_test.auto_api.views.api_info import ApiInfoSerializers
from PyAutoTest.enums.tools_enum import StatusEnum
from PyAutoTest.tools.view_utils.model_crud import ModelCRUD
from PyAutoTest.tools.view_utils.response_data import ResponseData

logger = logging.getLogger('api')


class ApiResultSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = ApiResult
        fields = '__all__'


class ApiResultSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    case = ApiCaseSerializers(read_only=True)
    api_info = ApiInfoSerializers(read_only=True)

    class Meta:
        model = ApiResult
        fields = '__all__'


class ApiResultCRUD(ModelCRUD):
    model = ApiResult
    queryset = ApiResult.objects.all()
    serializer_class = ApiResultSerializersC
    serializer = ApiResultSerializers


class ApiResultViews(ViewSet):
    model = ApiResult
    serializer_class = ApiResultSerializers

    @action(methods=['get'], detail=False)
    def suite_case_result(self, request: Request):
        result = self.model.objects.filter(test_suite_id=request.query_params.get('test_suite_id')).order_by(
            'create_time')
        data = []
        for i in result:
            case_result_list = self.model.objects.filter(test_suite_id=request.query_params.get('test_suite_id'),
                                                         case=i.case.id)
            for case_result in case_result_list:
                case_result_obj = {
                    'title': case_result.case.name,
                    'key': f'1-{case_result.id}',
                    'children': []
                }
                api_info_list = self.model.objects.filter(test_suite_id=request.query_params.get('test_suite_id'),
                                                          case_id=i.case.id, api_info=case_result.api_info.id)
                for api_info in api_info_list:
                    case_result_obj['children'].append({
                        'title': api_info.api_info.name,
                        'key': f'2-{case_result.id}',
                        'children': []
                    })
                data.append(case_result_obj)
        summary = [
            {'name': '用例总数', 'value': result.count()},
            {'name': '成功', 'value': result.filter(status=StatusEnum.SUCCESS.value).count()},
            {'name': '警告', 'value': result.filter(status=2).count()},
            {'name': '失败', 'value': result.filter(status=StatusEnum.FAIL.value).count()}
        ]
        return ResponseData.success('查询不同类型结果成功', {'data': data, 'summary': summary})

    @action(methods=['get'], detail=False)
    def case_result_week_sum(self, request: Request):
        """
        获取三个类型的总数
        @param request:
        @return:
        """
        ui_result = ApiResult.objects.raw(
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
                    id,
                    YEARWEEK(create_time) AS yearweek, 
                    COUNT(YEARWEEK(create_time)) AS total_count,
                    SUM(CASE WHEN status = 0 THEN 1 ELSE 0 END) AS status_0_total,
                    SUM(CASE WHEN status = 1 THEN 1 ELSE 0 END) AS status_1_total
                FROM api_result
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
            result_dict['success'].append(row.status_0_total)
        for row in ui_result:
            result_dict['fail'].append(row.status_1_total)
        result_dict['successSun'] = sum(result_dict['success'])
        result_dict['failSun'] = sum(result_dict['fail'])
        return ResponseData.success(f'获取图表数据成功', result_dict)

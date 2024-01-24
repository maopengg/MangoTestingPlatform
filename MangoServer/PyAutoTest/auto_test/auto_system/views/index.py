# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-01-12 14:53
# @Author : 毛鹏
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase, ApiCaseResult
from PyAutoTest.auto_test.auto_ui.models import UiCase, UiCaseResult
from PyAutoTest.auto_test.auto_user.models import UserLogs
from PyAutoTest.enums.system_enum import AutoTestTypeEnum
from PyAutoTest.tools.view_utils.response_data import ResponseData


class IndexViews(ViewSet):
    """首页api"""

    @action(methods=['get'], detail=False)
    def case_result_week_sum(self, request: Request):
        """
        获取三个类型的总数
        @param request:
        @return:
        """
        api_result = ApiCaseResult.objects.raw(
            """
                SELECT
                    weeks.id,
                    weeks.yearweek,
                    COALESCE(api_counts.total_count, 0) AS total_count
                FROM (
                    SELECT 'id'as id,YEARWEEK(DATE_SUB(NOW(), INTERVAL n WEEK)) AS yearweek
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
                        COUNT(YEARWEEK(create_time)) AS total_count
                    FROM api_case_result
                    WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
                    GROUP BY YEARWEEK(create_time)
                ) api_counts ON weeks.yearweek = api_counts.yearweek
                ORDER BY weeks.yearweek;
            """
        )
        ui_result = UiCaseResult.objects.raw(
            """
                SELECT
                    weeks.id,
                    weeks.yearweek,
                    COALESCE(api_counts.total_count, 0) AS total_count
                FROM (
                    SELECT 'id'as id,YEARWEEK(DATE_SUB(NOW(), INTERVAL n WEEK)) AS yearweek
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
                        COUNT(YEARWEEK(create_time)) AS total_count
                    FROM ui_case_result
                    WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
                    GROUP BY YEARWEEK(create_time)
                ) api_counts ON weeks.yearweek = api_counts.yearweek
                ORDER BY weeks.yearweek;

            """
        )
        result_dict = {
            'api_count': [],
            'ui_count': []
        }
        for row in api_result:
            result_dict['api_count'].append(row.total_count)
        for row in ui_result:
            result_dict['ui_count'].append(row.total_count)

        return ResponseData.success(f'获取图表数据成功', result_dict)

    @action(methods=['get'], detail=False)
    def case_sum(self, request: Request):
        """
        获取所有用例的总数
        @param request:
        @return:
        """

        return ResponseData.success('获取数据成功',
                                    [
                                        {'value': UiCase.objects.count(),
                                         'name': AutoTestTypeEnum.get_value(AutoTestTypeEnum.UI.value)},
                                        {'value': ApiCase.objects.count(),
                                         'name': AutoTestTypeEnum.get_value(AutoTestTypeEnum.API.value)}
                                    ])

    @action(methods=['get'], detail=False)
    def case_run_sum(self, request: Request):
        """
        获取所有用例的总数
        @param request:
        @return:
        """

        return ResponseData.success('获取数据成功',
                                    [
                                        {'value': UiCaseResult.objects.count(),
                                         'name': AutoTestTypeEnum.get_value(AutoTestTypeEnum.UI.value)},
                                        {'value': ApiCaseResult.objects.count(),
                                         'name': AutoTestTypeEnum.get_value(AutoTestTypeEnum.API.value)}
                                    ])

    @action(methods=['get'], detail=False)
    def activity_level(self, request: Request):
        """
        获取所有用例的总数
        @param request:
        @return:
        """
        active_user_counts = UserLogs.objects.values('user_id', 'nickname').annotate(total_logins=Count('id')).order_by(
            'total_logins')
        active_user_counts_ = {
            'nickname': [],
            'total_logins': [],
        }
        for user_count in active_user_counts:
            active_user_counts_['nickname'].append(user_count['nickname'])
            active_user_counts_['total_logins'].append(user_count['total_logins'])
        return ResponseData.success('获取数据成功', active_user_counts_)

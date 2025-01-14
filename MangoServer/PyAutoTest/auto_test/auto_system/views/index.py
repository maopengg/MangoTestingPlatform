# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-01-12 14:53
# @Author : 毛鹏
import django
from django.db.models import Count
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from PyAutoTest.auto_test.auto_api.models import ApiCase
from PyAutoTest.auto_test.auto_system.models import TestSuiteDetails
from PyAutoTest.auto_test.auto_ui.models import UiCase
from PyAutoTest.auto_test.auto_user.models import UserLogs, User
from PyAutoTest.enums.tools_enum import AutoTestTypeEnum
from PyAutoTest.tools.decorator.error_response import error_response
from PyAutoTest.tools.view.response_data import ResponseData
from PyAutoTest.tools.view.response_msg import *


class IndexViews(ViewSet):
    """首页api"""

    @action(methods=['get'], detail=False)
    @error_response('system')
    def case_result_week_sum(self, request: Request):
        """
        获取三个类型的总数
        @param request:
        @return:
        """
        try:
            api_result = TestSuiteDetails.objects.raw(
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
                            MAX(test_suite_details.id) as id,
                            YEARWEEK(create_time) AS yearweek, 
                            COUNT(YEARWEEK(create_time)) AS total_count
                        FROM test_suite_details
                        WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
                        AND type = 1
                        GROUP BY YEARWEEK(create_time)
                    ) api_counts ON weeks.yearweek = api_counts.yearweek
                    ORDER BY weeks.yearweek;
                """
            )
            ui_result = TestSuiteDetails.objects.raw(
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
                            MAX(test_suite_details.id) as id,
                            YEARWEEK(create_time) AS yearweek, 
                            COUNT(YEARWEEK(create_time)) AS total_count
                        FROM test_suite_details
                        WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
                        AND type = 0
                        GROUP BY YEARWEEK(create_time)
                    ) api_counts ON weeks.yearweek = api_counts.yearweek
                    ORDER BY weeks.yearweek;
    
                """
            )
            result_dict = {
                'api_count': [row.total_count for row in api_result],
                'ui_count': [row.total_count for row in ui_result]
            }
            return ResponseData.success(RESPONSE_MSG_0092, result_dict)
        except django.db.utils.OperationalError:
            result_dict = {
                'api_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                'ui_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            }
            return ResponseData.success(RESPONSE_MSG_0129, result_dict)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def case_sum(self, request: Request):
        """
        获取所有用例的总数
        @param request:
        @return:
        """

        return ResponseData.success(RESPONSE_MSG_0093,
                                    [
                                        {'value': UiCase.objects.count(),
                                         'name': AutoTestTypeEnum.get_value(AutoTestTypeEnum.UI.value)},
                                        {'value': ApiCase.objects.count(),
                                         'name': AutoTestTypeEnum.get_value(AutoTestTypeEnum.API.value)}
                                    ])

    @action(methods=['get'], detail=False)
    @error_response('system')
    def case_run_sum(self, request: Request):
        """
        获取所有用例的总数
        @param request:
        @return:
        """
        return ResponseData.success(RESPONSE_MSG_0094, [
            {
                'value': TestSuiteDetails.objects.filter(type=AutoTestTypeEnum.UI.value).count(),
                'name': AutoTestTypeEnum.get_value(AutoTestTypeEnum.UI.value)
            },
            {
                'value': TestSuiteDetails.objects.filter(type=AutoTestTypeEnum.API.value).count(),
                'name': AutoTestTypeEnum.get_value(AutoTestTypeEnum.API.value)
            }
        ])

    @action(methods=['get'], detail=False)
    @error_response('system')
    def activity_level(self, request: Request):
        """

        @param request:
        @return:
        """
        active_user_counts = UserLogs.objects.values('user').annotate(total_logins=Count('id')).order_by(
            '-total_logins')[:10]
        name_list = []
        total_logins_list = []
        for user_count in active_user_counts:
            name_list.append(User.objects.get(id=user_count.get('user')).name)
            total_logins_list.append(user_count.get('total_logins'))
        return ResponseData.success(RESPONSE_MSG_0092, {
            'name': name_list[::-1],
            'total_logins': total_logins_list[::-1],
        })

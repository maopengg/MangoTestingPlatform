# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
import django
from django.db import OperationalError
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.viewsets import ViewSet

from src.auto_test.auto_system.models import TestSuiteDetails
from src.auto_test.auto_system.views.project_product import ProjectProductSerializersC
from src.auto_test.auto_system.views.test_suite import TestSuiteSerializers
from src.enums.tools_enum import StatusEnum, TaskEnum, TestCaseTypeEnum
from src.tools.decorator.error_response import error_response
from src.tools.view import *
from src.tools.view.model_crud import ModelCRUD


class TestSuiteDetailsSerializers(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = TestSuiteDetails
        fields = '__all__'


class TestSuiteDetailsSerializersC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product = ProjectProductSerializersC(read_only=True)
    test_suite = TestSuiteSerializers(read_only=True)

    class Meta:
        model = TestSuiteDetails
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.select_related(
            'project_product',
            'test_suite',
        )
        return queryset


class TestSuiteDetailsCRUD(ModelCRUD):
    model = TestSuiteDetails
    queryset = TestSuiteDetails.objects.all()
    serializer_class = TestSuiteDetailsSerializersC
    serializer = TestSuiteDetailsSerializers

    @error_response('system')
    def get(self, request: Request):
        query_dict = {}
        for k, v in dict(request.query_params.lists()).items():
            if k and isinstance(v[0], str) and k not in self.not_matching_str and 'id' not in k:
                query_dict[f'{k}__contains'] = v[0]
            else:
                query_dict[k] = v[0]
        del query_dict['pageSize']
        del query_dict['page']
        books = self.model.objects.filter(**query_dict)
        data_list, count = self.paging_list(
            request.query_params.get("pageSize"),
            request.query_params.get("page"),
            books,
            self.get_serializer_class()
        )
        for item in data_list:
            if 'result_data' in item:
                item['children'] = item.pop('result_data')
                if item.get('children'):
                    for i in item.get('children'):
                        i['case_type'] = item['type']
        return ResponseData.success(
            RESPONSE_MSG_0001,
            data_list,
            count
        )


class TestSuiteDetailsViews(ViewSet):
    model = TestSuiteDetails
    serializer_class = TestSuiteDetailsSerializers

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_all_retry(self, request: Request):
        test_suite_details = self.model.objects.filter(test_suite_id=request.query_params.get('test_suite_id'))
        for i in test_suite_details:
            i.retry = 0
            i.status = TaskEnum.STAY_BEGIN.value
            i.save()
        return ResponseData.success(RESPONSE_MSG_0132)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_retry(self, request: Request):
        test_suite_details = self.model.objects.get(id=request.query_params.get('id'))
        test_suite_details.retry = test_suite_details.retry - 1
        test_suite_details.status = TaskEnum.STAY_BEGIN.value
        test_suite_details.save()
        return ResponseData.success(RESPONSE_MSG_0133)

    @action(methods=['get'], detail=False)
    @error_response('user')
    def test_suite_details_report(self, request):
        data = {
            'success': [],
            'fail': [],
            'failSun': self.model.objects.filter(status=StatusEnum.FAIL.value).count(),
            'successSun': self.model.objects.filter(status=StatusEnum.SUCCESS.value).count(),
        }
        try:
            fail = TestSuiteDetails.objects.raw(
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
                        AND status = 0
                        GROUP BY YEARWEEK(create_time)
                    ) api_counts ON weeks.yearweek = api_counts.yearweek
                    ORDER BY weeks.yearweek;
    
                """
            )
            success = TestSuiteDetails.objects.raw(
                """
                     SELECT
                        weeks.id,
                        weeks.yearweek,
                        COALESCE(api_counts.total_count, 0) AS total_count
                    FROM (
                        SELECT 'id' AS id, YEARWEEK(DATE_SUB(NOW(), INTERVAL n WEEK)) AS yearweek
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
                            MAX(test_suite_details.id) AS id,
                            YEARWEEK(create_time) AS yearweek, 
                            COUNT(*) AS total_count
                        FROM test_suite_details
                        WHERE create_time >= DATE_SUB(NOW(), INTERVAL 12 WEEK)
                        AND status = 1
                        GROUP BY YEARWEEK(create_time)
                    ) api_counts ON weeks.yearweek = api_counts.yearweek
                    ORDER BY weeks.yearweek;
    
                """
            )
            data['fail'] = [result.total_count for result in fail]
            data['success'] = [result.total_count for result in success]
            return ResponseData.success(RESPONSE_MSG_0096, data)
        except django.db.utils.OperationalError:
            data['fail'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            data['success'] = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            return ResponseData.success(RESPONSE_MSG_0129, data)

    @action(methods=['get'], detail=False)
    @error_response('system')
    def get_summary(self, request: Request):
        test_suite_id = request.query_params.get('test_suite_id')
        model = self.model.objects.filter(test_suite_id=test_suite_id)
        return ResponseData.success(RESPONSE_MSG_0065, {
            'count': model.count(),
            'fail_count': model.filter(status=TaskEnum.FAIL.value).count(),
            'success_count': model.filter(status=TaskEnum.SUCCESS.value).count(),
            'stay_begin_count': model.filter(status=TaskEnum.STAY_BEGIN.value).count(),
            'proceed_count': model.filter(status=TaskEnum.PROCEED.value).count(),
            'api_count': model.filter(type=TestCaseTypeEnum.API.value).count(),
            'ui_count': model.filter(type=TestCaseTypeEnum.UI.value).count(),
            'pytest_count': model.filter(type=TestCaseTypeEnum.PYTEST.value).count(),
            'api_in_progress_count': model.filter(
                type=TestCaseTypeEnum.API.value,
                status__in=[TaskEnum.FAIL.value, TaskEnum.SUCCESS.value]
            ).count(),
            'ui_in_progress_count': model.filter(
                type=TestCaseTypeEnum.UI.value,
                status__in=[TaskEnum.FAIL.value, TaskEnum.SUCCESS.value]
            ).count(),
            'pytest_in_progress_count': model.filter(
                type=TestCaseTypeEnum.PYTEST.value,
                status__in=[TaskEnum.FAIL.value, TaskEnum.SUCCESS.value]
            ).count(),
        })

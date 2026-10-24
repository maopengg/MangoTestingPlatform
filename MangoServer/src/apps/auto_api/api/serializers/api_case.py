# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-17 20:20
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.task_center.models import TasksDetails
from src.apps.auto_api.enums.case import ApiCaseConfigurationFilterEnum


class ApiCaseBoundTaskSerializers(serializers.ModelSerializer):
    task_detail_id = serializers.IntegerField(source='id', read_only=True)
    task_id = serializers.IntegerField(source='task.id', read_only=True)
    task_name = serializers.CharField(source='task.name', read_only=True)
    timing_strategies = serializers.SerializerMethodField()
    test_envs = serializers.JSONField(source='task.test_envs', read_only=True)
    case_people_name = serializers.CharField(source='task.case_people.name', read_only=True)
    status = serializers.IntegerField(source='task.status', read_only=True)
    is_notice = serializers.IntegerField(source='task.is_notice', read_only=True)
    fail_notice = serializers.IntegerField(source='task.fail_notice', read_only=True)
    update_time = serializers.DateTimeField(source='task.update_time', format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product_id = serializers.IntegerField(source='task.project_product.id', read_only=True)
    module_id = serializers.IntegerField(source='task.module.id', read_only=True, allow_null=True)

    @staticmethod
    def get_timing_strategies(instance):
        return [
            {
                'id': timing_strategy.id,
                'name': timing_strategy.name,
                'cron': timing_strategy.cron,
            }
            for timing_strategy in instance.task.timing_strategies.all()
        ]

    class Meta:
        model = TasksDetails
        fields = (
            'task_detail_id',
            'task_id',
            'task_name',
            'timing_strategies',
            'test_envs',
            'case_people_name',
            'status',
            'is_notice',
            'fail_notice',
            'update_time',
            'project_product_id',
            'module_id',
        )


class ApiCaseConfigurationSummaryQuery(serializers.Serializer):
    case_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=200)


class ApiCaseConfigurationFilterQuery(serializers.Serializer):
    execution_configuration = serializers.ListField(
        child=serializers.ChoiceField(choices=ApiCaseConfigurationFilterEnum.choices()),
        required=False, default=list, max_length=4,
    )


class ApiCaseConfigurationDetailQuery(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    page = serializers.IntegerField(min_value=1, default=1)
    pageSize = serializers.IntegerField(min_value=1, max_value=100, default=20)

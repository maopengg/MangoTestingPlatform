from rest_framework import serializers
from mangotools.enums import TestCaseTypeEnum


class ExecutionEfficiencyQuerySerializer(serializers.Serializer):
    section = serializers.ChoiceField(choices=['queue', 'timing', 'anomalies'], default='queue')
    start_at = serializers.DateTimeField(required=False)
    end_at = serializers.DateTimeField(required=False)
    project_id = serializers.IntegerField(min_value=1, required=False)
    project_product_id = serializers.IntegerField(min_value=1, required=False)
    module_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=1000, required=False)
    test_env = serializers.ListField(child=serializers.IntegerField(), max_length=30, required=False)
    case_type = serializers.ListField(child=serializers.ChoiceField(choices=[item.value for item in TestCaseTypeEnum]), max_length=10, required=False)
    task_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=100, required=False)
    task_group_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=100, required=False)
    report_id = serializers.IntegerField(min_value=1, required=False)
    page = serializers.IntegerField(min_value=1, max_value=10000, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)

    @classmethod
    def from_params(cls, params):
        values = params.dict()
        for key in ('module_ids', 'test_env', 'case_type', 'task_ids', 'task_group_ids'):
            source = key + '__in' if key + '__in' in params else key
            if source in params:
                values.pop(source, None)
                values[key] = [item for raw in params.getlist(source) for item in raw.split(',') if item]
        return cls(data=values)


class ExecutionEfficiencyOptionsSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=['tasks', 'groups'], default='tasks')
    product_id = serializers.IntegerField(min_value=1, required=False)
    keyword = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    page = serializers.IntegerField(min_value=1, max_value=10000, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=50)

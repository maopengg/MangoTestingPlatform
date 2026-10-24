from rest_framework import serializers


class ApiInfoExecutionTargetQuery(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    revision_id = serializers.IntegerField(min_value=1, required=False)
    release_id = serializers.IntegerField(min_value=1, required=False)


class ApiInfoRuntimeParametersQuery(serializers.Serializer):
    runtime_parameters = serializers.DictField(child=serializers.JSONField(), required=False, default=dict)


class ApiInfoExecutionQuery(ApiInfoExecutionTargetQuery, ApiInfoRuntimeParametersQuery):
    test_env = serializers.IntegerField(min_value=0)

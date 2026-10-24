from rest_framework import serializers

from src.apps.data_factory.models import SqlExecutionRecord
from src.apps.test_center.enums.environment import EnvironmentEnum


class SqlExecutionRecordSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product_name = serializers.CharField(source='project_product.name', read_only=True)
    datasource_alias_name = serializers.CharField(source='datasource_alias.name', read_only=True)
    database_name = serializers.CharField(source='datasource_binding.database_name', read_only=True, allow_null=True)
    test_env_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SqlExecutionRecord
        fields = '__all__'

    @staticmethod
    def get_test_env_name(obj):
        return EnvironmentEnum.obj().get(obj.test_env, obj.test_env)

from rest_framework import serializers

from src.apps.data_factory.models import SqlExecutionRecord
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.enums.data_source import DataSourceTypeEnum


class SqlExecutionRecordSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    project_product_name = serializers.CharField(source='project_product.name', read_only=True)
    datasource_alias_name = serializers.CharField(source='datasource_alias.name', read_only=True)
    database_name = serializers.SerializerMethodField(read_only=True)
    datasource_type_name = serializers.SerializerMethodField(read_only=True)
    test_env_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SqlExecutionRecord
        fields = '__all__'

    @staticmethod
    def get_test_env_name(obj):
        return EnvironmentEnum.obj().get(obj.test_env, obj.test_env) if obj.test_env is not None else '不适用'

    @staticmethod
    def get_database_name(obj):
        return (obj.source_detail or {}).get('database_name') or '-'

    @staticmethod
    def get_datasource_type_name(obj):
        if obj.datasource_type is not None:
            return DataSourceTypeEnum.obj().get(obj.datasource_type, '未知类型')
        if obj.database is not None:
            return f'{DataSourceTypeEnum.obj().get(obj.database.db_type, "未知类型")}（当前配置）'
        return '历史未记录'

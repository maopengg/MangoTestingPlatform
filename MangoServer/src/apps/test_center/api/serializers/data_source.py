# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023-02-16 20:58
# @Author : 毛鹏
from rest_framework import serializers

from src.apps.data_factory.models import Database
from src.apps.test_center.enums.data_source import (
    DataSourceCategoryEnum,
    DataSourceTypeEnum,
)
from src.apps.test_center.services.datasource.data_source import DataSourceConnectionService
from src.apps.test_center.services.datasource.data_source_configuration import DataSourceConfigurationService
from src.apps.user.formatters import format_user_simple
from src.common.validators.serializer_fields import RelatedObjectField


class DataSourceDiscoverySerializer(serializers.Serializer):
    data_source_id = serializers.IntegerField(min_value=1)
    refresh = serializers.BooleanField(default=False)
    table_name = serializers.CharField(required=False, max_length=255)
    database_name = serializers.CharField(required=False, allow_blank=True, max_length=128, default='')


class DataSourceAliasSerializer(serializers.Serializer):
    data_source_id = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=128, required=False, allow_blank=True, default='')


class DataSourceQuerySerializer(serializers.Serializer):
    data_source_id = serializers.IntegerField(min_value=1)
    database_name = serializers.CharField(max_length=128)
    sql = serializers.CharField(max_length=20000)


class DataSourceSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Database
        fields = '__all__'

    def validate(self, attrs):
        source_category = attrs.get(
            'source_category',
            self.instance.source_category if self.instance else DataSourceCategoryEnum.DATABASE.value,
        )
        source_type = attrs.get('db_type', self.instance.db_type if self.instance else None)
        expected_category = DataSourceTypeEnum.category(source_type)
        if source_type in {DataSourceTypeEnum.ORACLE.value, DataSourceTypeEnum.SQLSERVER.value}:
            raise serializers.ValidationError({'db_type': '当前类型尚未实现连接和执行适配器'})
        if expected_category is None:
            raise serializers.ValidationError({'db_type': '不支持的数据库类型'})
        if source_category != expected_category:
            raise serializers.ValidationError({'source_category': '数据库分类与具体类型不匹配'})
        extra_config = attrs.get('extra_config', self.instance.extra_config if self.instance else {}) or {}
        if not isinstance(extra_config, dict):
            raise serializers.ValidationError({'extra_config': '扩展配置必须是对象'})
        attrs['display_name'] = str(
            attrs.get('display_name', self.instance.display_name if self.instance else '') or ''
        ).strip()
        if not attrs['display_name']:
            raise serializers.ValidationError({'display_name': '连接名称不能为空'})
        if source_type == DataSourceTypeEnum.SQLITE.value:
            if not attrs.get('file_path', self.instance.file_path if self.instance else ''):
                raise serializers.ValidationError({'file_path': 'SQLite必须填写已有文件路径'})
            attrs['host'] = ''
            attrs['port'] = 0
        elif attrs.get('file_path', self.instance.file_path if self.instance else ''):
            raise serializers.ValidationError({'file_path': '此类型不使用SQLite文件路径'})
        if source_type != DataSourceTypeEnum.SQLITE.value:
            if not attrs.get('host', self.instance.host if self.instance else ''):
                raise serializers.ValidationError({'host': '网络数据源必须填写地址'})
            if not 1 <= attrs.get('port', self.instance.port if self.instance else 0) <= 65535:
                raise serializers.ValidationError({'port': '端口必须在1到65535之间'})
        allowed_keys = {
            DataSourceTypeEnum.REDIS.value: {'ssl'},
            DataSourceTypeEnum.ELASTICSEARCH.value: {'scheme', 'path_prefix', 'verify_certs'},
        }.get(source_type, set())
        unknown_keys = set(extra_config) - allowed_keys
        if unknown_keys:
            raise serializers.ValidationError(
                {'extra_config': f"当前数据库不支持配置项：{', '.join(sorted(unknown_keys))}"})
        if source_type == DataSourceTypeEnum.REDIS.value:
            if not isinstance(extra_config.get('ssl', False), bool):
                raise serializers.ValidationError({'extra_config': 'Redis ssl 必须是布尔值'})
        if source_type == DataSourceTypeEnum.ELASTICSEARCH.value:
            scheme = extra_config.get('scheme', 'http')
            if scheme not in {'http', 'https'}:
                raise serializers.ValidationError({'extra_config': 'Elasticsearch scheme 只支持 http 或 https'})
            if not isinstance(extra_config.get('path_prefix', ''), str):
                raise serializers.ValidationError({'extra_config': 'Elasticsearch path_prefix 必须是字符串'})
            if not isinstance(extra_config.get('verify_certs', True), bool):
                raise serializers.ValidationError({'extra_config': 'Elasticsearch verify_certs 必须是布尔值'})
        if self.instance is not None and not attrs.get('password'):
            attrs.pop('password', None)
        DataSourceConfigurationService.validate_unique(attrs, instance=self.instance)
        return attrs


class DataSourceSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_user = RelatedObjectField(formatter=format_user_simple, read_only=True)
    capabilities = serializers.SerializerMethodField()

    class Meta:
        model = Database
        exclude = ('password',)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related('update_user')

    @staticmethod
    def get_capabilities(obj):
        return DataSourceConnectionService.capabilities(obj)

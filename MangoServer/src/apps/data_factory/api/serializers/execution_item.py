# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂执行明细视图

from rest_framework import serializers

from src.apps.data_factory.api.serializers.execution import DataFactoryExecutionSerializerC
from src.apps.data_factory.api.serializers.template import DataFactoryTemplateSerializerC
from src.apps.data_factory.models import DataFactoryExecutionItem, SqlExecutionRecord
from src.apps.data_factory.services.execution_snapshot import get_insert_snapshot
from src.apps.test_center.formatters.related import format_data_source
from src.common.validators.serializer_fields import RelatedObjectField


class DataFactoryExecutionItemListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        items = list(data.all() if hasattr(data, 'all') else data)
        records_by_item = {}
        for record in SqlExecutionRecord.objects.filter(
                source_type='data_factory',
                source_id__in=[item.id for item in items],
        ).order_by('create_time', 'id'):
            records_by_item.setdefault(record.source_id, []).append(record)
        for item in items:
            item._sql_execution_records = records_by_item.get(item.id, [])
        return super().to_representation(items)


class DataFactoryExecutionItemSerializer(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    storage_snapshot = serializers.SerializerMethodField(read_only=True)
    sql_executions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DataFactoryExecutionItem
        fields = '__all__'
        list_serializer_class = DataFactoryExecutionItemListSerializer

    @staticmethod
    def get_storage_snapshot(obj):
        snapshot = dict(get_insert_snapshot(obj))
        entity = obj.template.entity if obj.template_id and obj.template else None
        snapshot.setdefault('database_id', obj.database_id)
        snapshot.setdefault('database_name', None)
        snapshot.setdefault('table_name', entity.table_name if entity else None)
        snapshot.setdefault('primary_key', entity.primary_key if entity else None)
        return snapshot

    @staticmethod
    def serialize_sql_execution(record):
        return {
            'id': record.id,
            'source_stage': record.source_stage,
            'source_detail': record.source_detail,
            'sql_text': record.sql_text,
            'sql_parameters': record.sql_parameters,
            'status': record.status,
            'duration_ms': record.duration_ms,
            'row_count': record.row_count,
            'affected_rows': record.affected_rows,
            'result_preview': record.result_preview,
            'result_truncated': record.result_truncated,
            'error_message': record.error_message,
            'is_slow': record.is_slow,
            'create_time': record.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        }

    @classmethod
    def get_sql_executions(cls, obj):
        records = getattr(obj, '_sql_execution_records', None)
        if records is None:
            records = SqlExecutionRecord.objects.filter(
                source_type='data_factory',
                source_id=obj.id,
            ).order_by('create_time', 'id')
        result = [cls.serialize_sql_execution(record) for record in records]
        if result:
            return result
        if obj.insert_sql:
            result.append({
                'id': f'legacy-create-{obj.id}',
                'source_stage': 'create',
                'sql_text': obj.insert_sql,
                'sql_parameters': {
                    key: value
                    for key, value in (obj.insert_sql_params or {}).items()
                    if key != '__data_factory_insert_snapshot__'
                },
                'status': 'success',
                'duration_ms': None,
                'row_count': 0,
                'affected_rows': 1,
                'result_preview': '',
                'result_truncated': False,
                'error_message': None,
                'is_slow': False,
                'create_time': obj.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'legacy': True,
            })
        if obj.cleanup_sql:
            result.append({
                'id': f'legacy-cleanup-{obj.id}',
                'source_stage': 'cleanup',
                'sql_text': obj.cleanup_sql,
                'sql_parameters': obj.cleanup_sql_params or {},
                'status': 'success' if obj.cleanup_status == 1 else 'fail',
                'duration_ms': None,
                'row_count': 0,
                'affected_rows': 0,
                'result_preview': '',
                'result_truncated': False,
                'error_message': obj.cleanup_error,
                'is_slow': False,
                'create_time': (
                        obj.cleanup_time or obj.update_time
                ).strftime('%Y-%m-%d %H:%M:%S'),
                'legacy': True,
            })
        return result


class DataFactoryExecutionItemSerializerC(serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    cleanup_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    execution = DataFactoryExecutionSerializerC(read_only=True)
    template = DataFactoryTemplateSerializerC(read_only=True)
    database = RelatedObjectField(formatter=format_data_source, read_only=True)
    storage_snapshot = serializers.SerializerMethodField(read_only=True)
    sql_executions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = DataFactoryExecutionItem
        fields = '__all__'
        list_serializer_class = DataFactoryExecutionItemListSerializer

    get_storage_snapshot = staticmethod(DataFactoryExecutionItemSerializer.get_storage_snapshot)

    @staticmethod
    def get_sql_executions(obj):
        return DataFactoryExecutionItemSerializer.get_sql_executions(obj)

    @staticmethod
    def setup_eager_loading(queryset):
        return queryset.select_related(
            'execution',
            'execution__project_product',
            'execution__project_product__project',
            'execution__template',
            'template',
            'template__project_product',
            'template__project_product__project',
            'template__entity',
            'template__entity__project_product',
            'template__entity__project_product__project',
            'template__entity__datasource_alias',
            'template__entity__datasource_alias__project_product',
            'template__entity__datasource_alias__project_product__project',
            'database',
            'datasource_binding',
            'datasource_binding__datasource_alias',
        )

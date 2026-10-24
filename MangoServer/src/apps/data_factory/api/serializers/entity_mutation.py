from rest_framework import serializers

from src.apps.data_factory.api.serializers.mixins import ProductModuleBindingSerializerMixin
from src.apps.data_factory.enums import DataFactoryEntityStatusChangeSourceEnum
from src.apps.data_factory.enums import DataFactoryOperationTypeEnum
from src.apps.data_factory.models import DataFactoryEntity
from src.apps.data_factory.services.entity import DataFactoryEntityService


class DataFactoryEntitySerializer(ProductModuleBindingSerializerMixin, serializers.ModelSerializer):
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)
    update_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', read_only=True)

    class Meta:
        model = DataFactoryEntity
        fields = '__all__'
        validators = []
        read_only_fields = [
            'status_change_source',
            'status_change_reason_code',
            'status_change_reason',
            'status_changed_at',
            'status_changed_by',
            'status_change_reference_type',
            'status_change_reference_id',
        ]

    def validate(self, attrs):
        attrs['create_type'] = DataFactoryOperationTypeEnum.SQL.value
        attrs['delete_type'] = DataFactoryOperationTypeEnum.SQL.value
        datasource_alias = attrs.get(
            'datasource_alias',
            self.instance.datasource_alias if self.instance else None
        )
        if not datasource_alias:
            raise serializers.ValidationError("数据实体必须绑定逻辑数据库")
        project_product = attrs.get(
            'project_product',
            self.instance.project_product if self.instance else None
        )
        module = attrs.get('module', self.instance.module if self.instance else None)
        if not module:
            raise serializers.ValidationError("数据实体必须绑定模块")
        if project_product and module and module.project_product_id != project_product.id:
            raise serializers.ValidationError("模块不属于当前项目/产品")
        table_name = attrs.get('table_name', self.instance.table_name if self.instance else None)
        if not table_name:
            raise serializers.ValidationError("数据实体必须绑定表名")
        if project_product and datasource_alias and table_name:
            queryset = DataFactoryEntity.objects.filter(
                project_product=project_product,
                datasource_alias=datasource_alias,
                table_name=table_name,
                schema_name=attrs.get('schema_name', self.instance.schema_name if self.instance else ''),
            )
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise serializers.ValidationError(f"当前逻辑数据库下已存在表实体：{table_name}")
        return attrs

    def update(self, instance, validated_data):
        target_status = validated_data.pop('status', instance.status)
        operator = validated_data.get('update_user')
        instance = super().update(instance, validated_data)
        if target_status != instance.status:
            action_name = "启用" if target_status == 1 else "停用"
            result = DataFactoryEntityService.change_status(
                entity_id=instance.id,
                status=target_status,
                source=DataFactoryEntityStatusChangeSourceEnum.PAGE_MANUAL.value,
                reason_code=f"manual_{'enabled' if target_status == 1 else 'disabled'}",
                reason=f"页面手动{action_name}实体",
                operator_id=operator.id if operator else None,
                restore_invalidated_templates=target_status == 1,
            )
            instance = result["entity"]
        return instance

    def create(self, validated_data):
        # 新实体必须先同步字段，再通过统一启用校验。
        validated_data['status'] = 0
        validated_data['status_change_source'] = DataFactoryEntityStatusChangeSourceEnum.DATA_SYNC.value
        validated_data['status_change_reason_code'] = 'created_pending_schema_validation'
        validated_data['status_change_reason'] = '实体创建后等待表结构与字段规则校验'
        return super().create(validated_data)

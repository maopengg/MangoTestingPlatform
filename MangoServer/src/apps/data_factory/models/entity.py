from django.db import models
from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import (
    DataFactoryEntityStatusChangeSourceEnum,
    DataFactoryGeneratorTypeEnum,
    DataFactoryOperationTypeEnum,
)
from src.apps.data_factory.exceptions import (
    DATA_FACTORY_ENTITY_SCENARIO_TEMPLATE_RELATION_DELETE_BINDING_INVALID,
    DataFactoryError,
)
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.user.models import User

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂模型

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""

from django.apps import apps


class DataFactoryEntity(models.Model):
    """数据工厂实体"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    datasource_alias = models.ForeignKey(
        to="DataFactoryDatasourceAlias",
        to_field="id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    update_user = models.ForeignKey(to=User, to_field="id", related_name="data_factory_entity_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(verbose_name="实体名称", max_length=64)
    description = models.TextField(verbose_name="实体描述", null=True, blank=True)

    table_name = models.CharField(verbose_name="表名", max_length=128, null=True, blank=True)
    schema_name = models.CharField(verbose_name="schema", max_length=128, blank=True, default="")
    primary_key = models.CharField(verbose_name="主键字段", max_length=128, default="id")
    unique_key = models.CharField(verbose_name="唯一字段", max_length=128, null=True, blank=True)

    create_type = models.SmallIntegerField(
        verbose_name="创建方式",
        choices=DataFactoryOperationTypeEnum.choices(),
        default=DataFactoryOperationTypeEnum.SQL.value,
    )
    delete_type = models.SmallIntegerField(
        verbose_name="删除方式",
        choices=DataFactoryOperationTypeEnum.choices(),
        default=DataFactoryOperationTypeEnum.SQL.value,
    )

    cleanup_order = models.IntegerField(verbose_name="清理顺序", default=100)
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=StatusEnum.choices(),
        default=StatusEnum.SUCCESS.value,
        db_index=True,
    )
    status_change_source = models.SmallIntegerField(
        verbose_name="状态变更来源",
        choices=DataFactoryEntityStatusChangeSourceEnum.choices(),
        default=DataFactoryEntityStatusChangeSourceEnum.UNKNOWN.value,
        db_index=True,
    )
    status_change_reason_code = models.CharField(
        verbose_name="状态变更原因编码",
        max_length=64,
        default="historical_unknown",
    )
    status_change_reason = models.TextField(
        verbose_name="状态变更原因",
        default="历史数据未记录状态变更来源",
    )
    status_changed_at = models.DateTimeField(verbose_name="状态变更时间", null=True, blank=True)
    status_changed_by = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="data_factory_entity_status_changed_by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    status_change_reference_type = models.CharField(
        verbose_name="状态来源记录类型",
        max_length=32,
        null=True,
        blank=True,
    )
    status_change_reference_id = models.BigIntegerField(
        verbose_name="状态来源记录ID",
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'data_factory_entity'
        ordering = ['-id']
        constraints = [models.UniqueConstraint(
            fields=['project_product', 'datasource_alias', 'schema_name', 'table_name'],
            name='uniq_entity_source_schema_table',
        )]

    def delete(self, *args, **kwargs):
        if apps.get_model("data_factory", "DataFactoryTemplate").objects.filter(entity=self).exists():
            raise DataFactoryError(DATA_FACTORY_ENTITY_SCENARIO_TEMPLATE_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.name}({self.table_name})"


class DataFactoryEntityStatusLog(models.Model):
    """数据工厂实体状态变更审计。"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    entity = models.ForeignKey(
        to="DataFactoryEntity",
        to_field="id",
        related_name="status_logs",
        on_delete=models.CASCADE,
    )
    from_status = models.SmallIntegerField(verbose_name="变更前状态", choices=StatusEnum.choices())
    to_status = models.SmallIntegerField(verbose_name="变更后状态", choices=StatusEnum.choices())
    source = models.SmallIntegerField(
        verbose_name="变更来源",
        choices=DataFactoryEntityStatusChangeSourceEnum.choices(),
        default=DataFactoryEntityStatusChangeSourceEnum.UNKNOWN.value,
        db_index=True,
    )
    reason_code = models.CharField(verbose_name="原因编码", max_length=64)
    reason = models.TextField(verbose_name="变更原因")
    operator = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="data_factory_entity_status_logs",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    source_record_type = models.CharField(
        verbose_name="来源记录类型",
        max_length=32,
        null=True,
        blank=True,
    )
    source_record_id = models.BigIntegerField(verbose_name="来源记录ID", null=True, blank=True)
    context = models.JSONField(
        verbose_name="状态变更上下文",
        default=dict, blank=True,
        help_text="固定结构：job_key、database_ids、binding_ids、differences、invalidated_template_ids",
    )

    class Meta:
        db_table = 'data_factory_entity_status_log'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['entity', '-id']),
            models.Index(fields=['source', '-create_time']),
        ]

    def __str__(self):
        return f"{self.entity_id}:{self.from_status}->{self.to_status}"


class DataFactoryField(models.Model):
    """数据工厂字段规则"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    entity = models.ForeignKey(to="DataFactoryEntity", to_field="id", on_delete=models.CASCADE)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="data_factory_field_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(verbose_name="字段名", max_length=128)
    label = models.CharField(verbose_name="字段说明", max_length=128, null=True, blank=True)
    db_type = models.CharField(verbose_name="数据库类型", max_length=128)
    platform_type = models.CharField(verbose_name="平台类型", max_length=32)
    nullable = models.BooleanField(verbose_name="是否可空", default=True)
    primary_key = models.BooleanField(verbose_name="是否主键", default=False)
    autoincrement = models.BooleanField(verbose_name="是否自增", default=False)
    max_length = models.IntegerField(verbose_name="最大长度", null=True, blank=True)
    enum_values = models.JSONField(verbose_name="枚举值", default=list, blank=True)

    generator_type = models.SmallIntegerField(
        verbose_name="生成方式",
        choices=DataFactoryGeneratorTypeEnum.choices(),
        default=DataFactoryGeneratorTypeEnum.FIXED.value,
    )
    generator_config = models.JSONField(verbose_name="生成配置", default=dict, blank=True)
    sort = models.IntegerField(verbose_name="排序", default=0)

    class Meta:
        db_table = 'data_factory_field'
        ordering = ['sort', 'id']
        unique_together = ('entity', 'name')

    def __str__(self):
        return f"{self.entity.name}.{self.name}"

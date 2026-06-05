# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂模型

from django.db import models

from src.apps.auto_system.models import Database, ProductModule, ProjectProduct, TestObject
from src.common.enums.data_factory_enum import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionSourceEnum,
    DataFactoryExecutionStageEnum,
    DataFactoryExecutionStatusEnum,
    DataFactoryGeneratorTypeEnum,
    DataFactoryOperationTypeEnum,
    DataFactoryTemplateConfigStatusEnum,
    DataFactoryTemplateUsageScopeEnum,
)
from src.common.enums.tools_enum import StatusEnum
from src.common.exceptions import ToolsError

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class DataFactoryDatasourceAlias(models.Model):
    """数据工厂逻辑数据源"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)

    name = models.CharField(verbose_name="逻辑数据源名称", max_length=64)
    code = models.CharField(verbose_name="逻辑数据源编码", max_length=64)
    db_type = models.SmallIntegerField(verbose_name="数据库类型", default=0)
    description = models.TextField(verbose_name="描述", null=True, blank=True)
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=StatusEnum.choices(),
        default=StatusEnum.SUCCESS.value,
        db_index=True,
    )

    class Meta:
        db_table = 'data_factory_datasource_alias'
        ordering = ['-id']
        unique_together = ('project_product', 'code')

    def __str__(self):
        return f"{self.name}({self.code})"


class DataFactoryDatasourceBinding(models.Model):
    """逻辑数据源与测试环境真实数据库绑定"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    datasource_alias = models.ForeignKey(to=DataFactoryDatasourceAlias, to_field="id", on_delete=models.CASCADE)
    test_object = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.PROTECT)
    database = models.ForeignKey(to=Database, to_field="id", on_delete=models.PROTECT)
    description = models.TextField(verbose_name="描述", null=True, blank=True)
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=StatusEnum.choices(),
        default=StatusEnum.SUCCESS.value,
        db_index=True,
    )

    class Meta:
        db_table = 'data_factory_datasource_binding'
        ordering = ['-id']
        unique_together = ('datasource_alias', 'test_object')

    def __str__(self):
        return f"{self.datasource_alias.code}:{self.test_object_id}->{self.database_id}"


class DataFactoryEntity(models.Model):
    """数据工厂实体"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    datasource_alias = models.ForeignKey(
        to=DataFactoryDatasourceAlias,
        to_field="id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    name = models.CharField(verbose_name="实体名称", max_length=64)
    description = models.TextField(verbose_name="实体描述", null=True, blank=True)

    table_name = models.CharField(verbose_name="表名", max_length=128, null=True, blank=True)
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

    class Meta:
        db_table = 'data_factory_entity'
        ordering = ['-id']
        unique_together = ('project_product', 'datasource_alias', 'table_name')

    def delete(self, *args, **kwargs):
        if DataFactoryTemplate.objects.filter(entity=self).exists():
            raise ToolsError(300, "场景模板-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.name}({self.table_name})"


class DataFactoryField(models.Model):
    """数据工厂字段规则"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    entity = models.ForeignKey(to=DataFactoryEntity, to_field="id", on_delete=models.CASCADE)

    name = models.CharField(verbose_name="字段名", max_length=128)
    label = models.CharField(verbose_name="字段说明", max_length=128, null=True, blank=True)
    db_type = models.CharField(verbose_name="数据库类型", max_length=128)
    platform_type = models.CharField(verbose_name="平台类型", max_length=32)
    nullable = models.BooleanField(verbose_name="是否可空", default=True)
    primary_key = models.BooleanField(verbose_name="是否主键", default=False)
    autoincrement = models.BooleanField(verbose_name="是否自增", default=False)
    max_length = models.IntegerField(verbose_name="最大长度", null=True, blank=True)
    enum_values = models.JSONField(verbose_name="枚举值", default=list)

    generator_type = models.SmallIntegerField(
        verbose_name="生成方式",
        choices=DataFactoryGeneratorTypeEnum.choices(),
        default=DataFactoryGeneratorTypeEnum.FIXED.value,
    )
    generator_config = models.JSONField(verbose_name="生成配置", default=dict)
    sort = models.IntegerField(verbose_name="排序", default=0)

    class Meta:
        db_table = 'data_factory_field'
        ordering = ['sort', 'id']
        unique_together = ('entity', 'name')

    def __str__(self):
        return f"{self.entity.name}.{self.name}"


class DataFactoryTemplate(models.Model):
    """数据工厂场景模板"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    entity = models.ForeignKey(to=DataFactoryEntity, to_field="id", on_delete=models.PROTECT)

    name = models.CharField(verbose_name="模板名称", max_length=64)
    description = models.TextField(verbose_name="模板描述", null=True, blank=True)
    field_overrides = models.JSONField(verbose_name="字段覆盖", default=dict)
    output_config = models.JSONField(verbose_name="输出配置", default=list)
    cleanup_strategy = models.SmallIntegerField(
        verbose_name="默认清理策略",
        choices=DataFactoryCleanupStrategyEnum.choices(),
        default=DataFactoryCleanupStrategyEnum.MANUAL.value,
    )
    is_default = models.BooleanField(verbose_name="是否默认模板", default=False, db_index=True)
    usage_scope = models.SmallIntegerField(
        verbose_name="场景用途",
        choices=DataFactoryTemplateUsageScopeEnum.choices(),
        default=DataFactoryTemplateUsageScopeEnum.CASE.value,
        db_index=True,
    )
    config_status = models.SmallIntegerField(
        verbose_name="配置状态",
        choices=DataFactoryTemplateConfigStatusEnum.choices(),
        default=DataFactoryTemplateConfigStatusEnum.INCOMPLETE.value,
        db_index=True,
    )
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=StatusEnum.choices(),
        default=StatusEnum.SUCCESS.value,
        db_index=True,
    )

    class Meta:
        db_table = 'data_factory_template'
        ordering = ['-id']
        unique_together = ('entity', 'name')

    def __str__(self):
        return self.name


class DataFactoryTemplateItem(models.Model):
    """数据工厂场景模板关联项"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)

    template = models.ForeignKey(
        to=DataFactoryTemplate,
        to_field="id",
        related_name="items",
        on_delete=models.CASCADE,
    )
    child_template = models.ForeignKey(
        to=DataFactoryTemplate,
        to_field="id",
        related_name="used_in_template_items",
        on_delete=models.PROTECT,
    )
    name = models.CharField(verbose_name="关联名称", max_length=64)
    sort = models.IntegerField(verbose_name="执行顺序", default=0)
    field_overrides = models.JSONField(verbose_name="字段覆盖", default=dict)

    class Meta:
        db_table = 'data_factory_template_item'
        ordering = ['sort', 'id']

    def __str__(self):
        return f"{self.template_id}:{self.name or self.child_template_id}"


class DataFactoryCaseConfig(models.Model):
    """自动化用例数据工厂前置配置"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)

    source_type = models.SmallIntegerField(
        verbose_name="用例类型",
        choices=DataFactoryCaseSourceTypeEnum.choices(),
        db_index=True,
    )
    source_id = models.IntegerField(verbose_name="用例ID", db_index=True)
    template = models.ForeignKey(to=DataFactoryTemplate, to_field="id", on_delete=models.PROTECT)

    name = models.CharField(verbose_name="数据名称", max_length=64, null=True, blank=True)
    stage = models.SmallIntegerField(verbose_name="执行阶段", default=1)
    sort = models.IntegerField(verbose_name="执行顺序", default=0)
    field_overrides = models.JSONField(verbose_name="字段覆盖", default=dict)
    cleanup_strategy = models.SmallIntegerField(verbose_name="清理策略覆盖", null=True, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=StatusEnum.SUCCESS.value, db_index=True)

    class Meta:
        db_table = 'data_factory_case_config'
        ordering = ['sort', 'id']
        indexes = [
            models.Index(fields=['source_type', 'source_id', 'stage', 'status']),
        ]

    def __str__(self):
        return f"{self.source_type}:{self.source_id}:{self.name or self.template_id}"


class DataFactoryExecution(models.Model):
    """数据工厂执行批次"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    cleanup_time = models.DateTimeField(verbose_name="清理时间", null=True, blank=True)

    execution_no = models.CharField(verbose_name="执行编号", max_length=64, unique=True)
    source_type = models.SmallIntegerField(
        verbose_name="执行来源",
        choices=DataFactoryExecutionSourceEnum.choices(),
        default=DataFactoryExecutionSourceEnum.TEMPLATE_DEBUG.value,
    )
    source_id = models.IntegerField(verbose_name="来源ID", null=True, blank=True)
    template = models.ForeignKey(to=DataFactoryTemplate, to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    stage = models.SmallIntegerField(
        verbose_name="执行阶段",
        choices=DataFactoryExecutionStageEnum.choices(),
        default=DataFactoryExecutionStageEnum.DEBUG.value,
    )
    status = models.SmallIntegerField(
        verbose_name="执行状态",
        choices=DataFactoryExecutionStatusEnum.choices(),
        default=DataFactoryExecutionStatusEnum.PENDING.value,
        db_index=True,
    )
    cleanup_status = models.SmallIntegerField(
        verbose_name="清理状态",
        choices=DataFactoryCleanupStatusEnum.choices(),
        default=DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
        db_index=True,
    )
    context = models.JSONField(verbose_name="执行上下文", default=dict)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)

    class Meta:
        db_table = 'data_factory_execution'
        ordering = ['-create_time']

    def __str__(self):
        return self.execution_no


class DataFactoryExecutionItem(models.Model):
    """数据工厂执行明细"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    cleanup_time = models.DateTimeField(verbose_name="清理时间", null=True, blank=True)

    execution = models.ForeignKey(to=DataFactoryExecution, to_field="id", on_delete=models.CASCADE)
    template = models.ForeignKey(to=DataFactoryTemplate, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    database = models.ForeignKey(to=Database, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    alias = models.CharField(verbose_name="上下文别名", max_length=64)
    primary_value = models.CharField(verbose_name="主键值", max_length=256, null=True, blank=True)
    data = models.JSONField(verbose_name="创建数据", default=dict)
    insert_data = models.JSONField(verbose_name="插入数据", default=dict)
    insert_sql = models.TextField(verbose_name="插入SQL", null=True, blank=True)
    insert_sql_params = models.JSONField(verbose_name="插入SQL参数", default=dict)

    cleanup_strategy = models.SmallIntegerField(
        verbose_name="清理策略",
        choices=DataFactoryCleanupStrategyEnum.choices(),
        default=DataFactoryCleanupStrategyEnum.MANUAL.value,
    )
    cleanup_order = models.IntegerField(verbose_name="清理顺序", default=100)
    cleanup_status = models.SmallIntegerField(
        verbose_name="清理状态",
        choices=DataFactoryCleanupStatusEnum.choices(),
        default=DataFactoryCleanupStatusEnum.NOT_CLEANED.value,
        db_index=True,
    )
    cleanup_error = models.TextField(verbose_name="清理错误", null=True, blank=True)
    cleanup_sql = models.TextField(verbose_name="清理SQL", null=True, blank=True)
    cleanup_sql_params = models.JSONField(verbose_name="清理SQL参数", default=dict)

    class Meta:
        db_table = 'data_factory_execution_item'
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.execution.execution_no}:{self.alias}"

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂模型

from django.db import models

from src.apps.data_factory.enums import (
    DataFactoryCleanupStatusEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryExecutionSourceEnum,
    DataFactoryExecutionStageEnum,
    DataFactoryExecutionStatusEnum,
)
from src.apps.data_factory.models import Database
from src.apps.test_center.models import ProductModule, ProjectProduct

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


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
    template = models.ForeignKey(to="DataFactoryTemplate", to_field="id", on_delete=models.SET_NULL, null=True,
                                 blank=True)
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
    context = models.JSONField(verbose_name="执行上下文", default=dict, blank=True)
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

    execution = models.ForeignKey(to="DataFactoryExecution", to_field="id", on_delete=models.CASCADE)
    template = models.ForeignKey(to="DataFactoryTemplate", to_field="id", on_delete=models.PROTECT, null=True,
                                 blank=True)
    database = models.ForeignKey(to=Database, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    datasource_binding = models.ForeignKey(
        to="DataFactoryDatasourceBinding",
        to_field="id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    alias = models.CharField(verbose_name="上下文别名", max_length=64)
    primary_value = models.CharField(verbose_name="主键值", max_length=256, null=True, blank=True)
    data = models.JSONField(verbose_name="创建数据", default=dict, blank=True)
    insert_data = models.JSONField(verbose_name="插入数据", default=dict, blank=True)
    insert_sql = models.TextField(verbose_name="插入SQL", null=True, blank=True)
    insert_sql_params = models.JSONField(verbose_name="插入SQL参数", default=dict, blank=True)
    post_update_records = models.JSONField(
        verbose_name="插入后回写记录",
        default=list, blank=True,
        help_text="回写字段、来源、脱敏 SQL 参数、影响行数及执行状态审计",
    )

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
    cleanup_sql_params = models.JSONField(verbose_name="清理SQL参数", default=dict, blank=True)
    cleanup_resources = models.JSONField(
        verbose_name='关联资源清理快照与结果', default=dict, blank=True, editable=False,
        help_text='CleanupResourceState：执行时ES目标及所有权快照、SQL完成标记、逐资源回查结果',
    )

    class Meta:
        db_table = 'data_factory_execution_item'
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.execution.execution_no}:{self.alias}"


class SqlExecutionRecord(models.Model):
    """测试数据源的一次执行审计（SQL、Redis、ES及连接操作）。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True, db_index=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    request_id = models.CharField(verbose_name="幂等请求ID", max_length=64, unique=True)
    source_type = models.CharField(verbose_name="来源类型", max_length=64, db_index=True)
    source_id = models.BigIntegerField(verbose_name="来源资产ID", null=True, blank=True, db_index=True)
    source_stage = models.CharField(verbose_name="来源阶段", max_length=64, db_index=True)
    source_detail = models.JSONField(
        verbose_name="来源说明", default=dict, blank=True,
        help_text="按来源保存case_id、全局变量ID、数据工厂execution/item、步骤或MCP工具等定位信息",
    )

    project_product = models.ForeignKey(
        to=ProjectProduct, to_field="id", on_delete=models.PROTECT, null=True, blank=True,
    )
    test_env = models.SmallIntegerField(verbose_name="测试环境", db_index=True, null=True, blank=True)
    datasource_type = models.SmallIntegerField(verbose_name="执行时数据源类型", null=True, blank=True)
    datasource_alias = models.ForeignKey(
        to="DataFactoryDatasourceAlias", to_field="id", on_delete=models.PROTECT, null=True, blank=True,
    )
    database = models.ForeignKey(
        to=Database, to_field="id", on_delete=models.PROTECT, null=True, blank=True,
    )
    sql_text = models.TextField(verbose_name="脱敏执行内容")
    sql_parameters = models.JSONField(verbose_name="脱敏执行参数", default=dict, blank=True)
    sql_fingerprint = models.CharField(verbose_name="操作指纹", max_length=64, db_index=True)

    status = models.CharField(verbose_name="执行状态", max_length=16, default="running", db_index=True)
    duration_ms = models.DecimalField(
        verbose_name="执行耗时毫秒", max_digits=14, decimal_places=2, null=True, blank=True,
    )
    row_count = models.IntegerField(verbose_name="返回行数", default=0)
    affected_rows = models.IntegerField(verbose_name="影响行数", default=0)
    result_preview = models.TextField(verbose_name="结果预览", blank=True)
    result_truncated = models.BooleanField(verbose_name="结果是否截断", default=False)
    error_message = models.TextField(verbose_name="脱敏错误", null=True, blank=True)
    slow_threshold_ms = models.IntegerField(verbose_name="慢执行阈值毫秒", default=20000)
    is_slow = models.BooleanField(verbose_name="是否慢执行", default=False, db_index=True)

    class Meta:
        db_table = "sql_execution_record"
        ordering = ["-create_time", "-id"]
        indexes = [
            models.Index(fields=["datasource_type", "create_time"], name="idx_sql_type_time"),
            models.Index(fields=["is_slow", "create_time"], name="idx_sql_slow_time"),
            models.Index(fields=["source_type", "source_id", "create_time"], name="idx_sql_source_time"),
            models.Index(fields=["sql_fingerprint", "create_time"], name="idx_sql_fingerprint_time"),
        ]

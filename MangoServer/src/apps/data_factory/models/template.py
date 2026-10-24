# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂模型

from django.db import models, transaction
from django.db.models.deletion import ProtectedError
from mangotools.enums import StatusEnum

from src.apps.data_factory.enums import (
    DataFactoryCaseSourceTypeEnum,
    DataFactoryCleanupStrategyEnum,
    DataFactoryTemplateConfigStatusEnum,
    DataFactoryTemplateUsageScopeEnum,
)
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class DataFactoryTemplateQuerySet(models.QuerySet):
    def delete(self):
        from src.apps.data_factory.services.template_deletion import DataFactoryTemplateDeletionService

        with transaction.atomic(using=self.db):
            templates = list(self.select_for_update().order_by('pk'))
            for template in templates:
                DataFactoryTemplateDeletionService.validate(template, using=self.db)
            try:
                return super().delete()
            except ProtectedError as error:
                raise DataFactoryTemplateDeletionService.protected_error(templates[0]) from error


class DataFactoryTemplate(models.Model):
    """数据工厂场景模板"""
    objects = DataFactoryTemplateQuerySet.as_manager()
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT, null=True, blank=True)
    entity = models.ForeignKey(to="DataFactoryEntity", to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="data_factory_template_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(verbose_name="模板名称", max_length=64)
    description = models.TextField(verbose_name="模板描述", null=True, blank=True)
    field_overrides = models.JSONField(verbose_name="字段覆盖", default=dict, blank=True)
    output_config = models.JSONField(verbose_name="输出配置", default=list, blank=True)
    post_insert_updates = models.JSONField(
        verbose_name="插入后回写配置",
        default=list, blank=True,
        help_text=(
            "全部场景节点插入后，使用同一 execution 内来源节点字段值，"
            "按目标节点主键回写目标字段的结构化配置"
        ),
    )
    cleanup_strategy = models.SmallIntegerField(
        verbose_name="默认清理策略",
        choices=DataFactoryCleanupStrategyEnum.choices(),
        default=DataFactoryCleanupStrategyEnum.EXECUTION_END.value,
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

    def delete(self, using=None, keep_parents=False):
        from src.apps.data_factory.services.template_deletion import DataFactoryTemplateDeletionService

        using = using or self._state.db or 'default'
        with transaction.atomic(using=using):
            type(self).objects.using(using).select_for_update().get(pk=self.pk)
            DataFactoryTemplateDeletionService.validate(self, using=using)
            try:
                return super().delete(using=using, keep_parents=keep_parents)
            except ProtectedError as error:
                raise DataFactoryTemplateDeletionService.protected_error(self) from error


class DataFactoryTemplateItem(models.Model):
    """数据工厂场景模板关联项"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)

    template = models.ForeignKey(
        to="DataFactoryTemplate",
        to_field="id",
        related_name="items",
        on_delete=models.CASCADE,
    )
    child_template = models.ForeignKey(
        to="DataFactoryTemplate",
        to_field="id",
        related_name="used_in_template_items",
        on_delete=models.PROTECT,
    )
    update_user = models.ForeignKey(to=User, to_field="id", related_name="data_factory_template_item_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="关联名称", max_length=64)
    sort = models.IntegerField(verbose_name="执行顺序", default=0)
    field_overrides = models.JSONField(verbose_name="字段覆盖", default=dict, blank=True)

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
    template = models.ForeignKey(to="DataFactoryTemplate", to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="data_factory_case_config_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(verbose_name="数据名称", max_length=64, null=True, blank=True)
    stage = models.SmallIntegerField(verbose_name="执行阶段", default=1)
    sort = models.IntegerField(verbose_name="执行顺序", default=0)
    field_overrides = models.JSONField(verbose_name="字段覆盖", default=dict, blank=True)
    cleanup_strategy = models.SmallIntegerField(
        verbose_name="清理策略覆盖", null=True, blank=True,
        default=DataFactoryCleanupStrategyEnum.EXECUTION_END.value,
    )
    status = models.SmallIntegerField(verbose_name="状态", default=StatusEnum.SUCCESS.value, db_index=True)

    class Meta:
        db_table = 'data_factory_case_config'
        ordering = ['sort', 'id']
        indexes = [
            models.Index(fields=['source_type', 'source_id', 'stage', 'status']),
        ]

    def __str__(self):
        return f"{self.source_type}:{self.source_id}:{self.name or self.template_id}"

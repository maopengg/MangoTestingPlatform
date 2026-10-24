# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 数据工厂模型

from django.db import models
from mangotools.enums import StatusEnum

from src.apps.data_factory.exceptions import (
    DATA_SOURCE_DATABASE_CONFIG_DELETE_BINDING_INVALID,
    DataFactoryError,
)
from src.apps.test_center.models import ProjectProduct
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class Database(models.Model):
    """全局数据源连接；产品与环境关系由逻辑数据源绑定维护。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="database_update_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    source_category = models.SmallIntegerField(verbose_name="数据源分类", default=0, db_index=True)
    db_type = models.SmallIntegerField(verbose_name="数据源类型", default=0)
    display_name = models.CharField(verbose_name="连接名称", max_length=64, default="")
    file_path = models.CharField(verbose_name="SQLite文件路径", max_length=1024, blank=True, default="")
    user = models.CharField(verbose_name="登录用户名", max_length=64, blank=True, default="")
    password = models.CharField(verbose_name="登录密码", max_length=64, blank=True, default="")
    host = models.CharField(verbose_name="数据库地址", max_length=255, blank=True, default="")
    port = models.PositiveIntegerField(verbose_name="端口", default=0)
    extra_config = models.JSONField(
        verbose_name="扩展配置",
        default=dict,
        blank=True,
        help_text="Redis: {ssl}; Elasticsearch: {scheme, path_prefix, verify_certs}",
    )

    class Meta:
        db_table = "data_base"
        ordering = ["-id"]

    def delete(self, *args, **kwargs):
        if DataFactoryDatasourceBinding.objects.filter(database=self).exists():
            raise DataFactoryError(DATA_SOURCE_DATABASE_CONFIG_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)


class DataFactoryDatasourceAlias(models.Model):
    """数据工厂逻辑数据源"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="data_factory_datasource_alias_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(verbose_name="逻辑数据源名称", max_length=64)
    source_category = models.SmallIntegerField(verbose_name="数据源分类", default=0)
    db_type = models.SmallIntegerField(verbose_name="数据源类型", default=0)
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
        unique_together = ('project_product', 'name')

    def __str__(self):
        return self.name


class DataFactoryDatasourceBinding(models.Model):
    """逻辑数据源与环境下全局数据源连接的绑定"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    datasource_alias = models.ForeignKey(to="DataFactoryDatasourceAlias", to_field="id", on_delete=models.CASCADE)
    environment = models.SmallIntegerField(verbose_name="测试环境", db_index=True)
    database_name = models.CharField(verbose_name="实际数据库", max_length=128, blank=True, default="")
    schema_name = models.CharField(verbose_name="默认schema", max_length=128, blank=True, default="")
    redis_db = models.PositiveIntegerField(verbose_name="Redis DB编号", null=True, blank=True)
    database = models.ForeignKey(to=Database, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="data_factory_datasource_binding_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(verbose_name="描述", null=True, blank=True)
    db_c_status = models.SmallIntegerField(verbose_name="读取权限", default=StatusEnum.FAIL.value)
    db_rud_status = models.SmallIntegerField(verbose_name="写入权限", default=StatusEnum.FAIL.value)

    class Meta:
        db_table = 'data_factory_datasource_binding'
        ordering = ['-id']
        constraints = [
            models.UniqueConstraint(
                fields=['datasource_alias', 'environment'],
                name='uniq_datasource_alias_environment',
            ),
        ]

    def __str__(self):
        return f"{self.datasource_alias.name}:{self.environment}->{self.database_id}"

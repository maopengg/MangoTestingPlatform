from django.db import models
from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import (
    ApiAuthRefreshModeEnum,
    ApiAuthRefreshStatusEnum,
    ApiAuthTypeEnum,
    ApiPublicTypeEnum,
)
from src.apps.auto_api.exceptions import (
    API_HEADER_REQUEST_DELETE_INVALID,
    API_HEADER_SCENARIO_REQUEST_DELETE_INVALID,
    AutoApiError,
)
from src.apps.task_center.models import TimeTasks
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import NoticeGroup, ProjectProduct
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""

from src.apps.auto_api.models.core import ApiCase, ApiCaseDetailedParameter


class ApiHeaders(models.Model):
    """api公共"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="api_headers_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    key = models.CharField(verbose_name="键", max_length=128)
    value = models.TextField(verbose_name="值")
    status = models.SmallIntegerField(verbose_name="是否默认开启", default=0, db_index=True)

    class Meta:
        db_table = 'api_headers'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if self.status == StatusEnum.SUCCESS.value:
            raise AutoApiError(API_HEADER_REQUEST_DELETE_INVALID)
        case_reference_exists = ApiCase.objects.filter(
            project_product_id=self.project_product_id,
            front_headers__contains=[self.id],
        ).exists()
        parameter_reference_exists = (
                not case_reference_exists
                and ApiCaseDetailedParameter.objects.filter(
            case_detailed__case__project_product_id=self.project_product_id,
            headers__contains=[self.id],
        ).exists()
        )
        if case_reference_exists or parameter_reference_exists:
            raise AutoApiError(API_HEADER_SCENARIO_REQUEST_DELETE_INVALID)
        super().delete(*args, **kwargs)


class ApiPublic(models.Model):
    """api公共"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="api_public_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    # Deprecated: 环境范围已迁移到 test_envs，保留用于历史数据回滚和后续清理。
    test_env = models.SmallIntegerField(verbose_name="测试环境", null=True, blank=True, default=None)
    test_envs = models.JSONField(verbose_name="适用环境", default=list, blank=True)
    type = models.SmallIntegerField(
        verbose_name="自定义变量类型",
        choices=ApiPublicTypeEnum.choices(),
        default=ApiPublicTypeEnum.CUSTOM.value,
        db_index=True,
    )
    name = models.CharField(verbose_name="名称", max_length=64)
    tags = models.JSONField(verbose_name="分类标签", default=list, blank=True)
    key = models.CharField(verbose_name="键", max_length=128)
    value = models.TextField(verbose_name="值")
    datasource_alias = models.ForeignKey(
        to='auto_data_factory.DataFactoryDatasourceAlias',
        to_field="id",
        verbose_name="逻辑数据源",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    status = models.SmallIntegerField(verbose_name="状态", default=0, db_index=True)

    class Meta:
        db_table = 'api_public'
        ordering = ['-id']


class ApiAuthConfig(models.Model):
    """API授权Token配置"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="api_auth_config_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    test_env = models.SmallIntegerField(
        verbose_name="测试环境",
        choices=EnvironmentEnum.choices(),
        null=True,
        blank=True,
        default=None,
    )
    name = models.CharField(verbose_name="授权名称", max_length=64)
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=StatusEnum.choices(),
        default=StatusEnum.SUCCESS.value,
        db_index=True,
    )

    # 0=接口登录，1=自定义代码
    auth_type = models.SmallIntegerField(
        verbose_name="授权方式",
        choices=ApiAuthTypeEnum.choices(),
        default=ApiAuthTypeEnum.API.value,
        db_index=True,
    )
    api_info = models.ForeignKey(
        to="ApiInfo",
        to_field="id",
        verbose_name="登录接口",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    custom_code = models.TextField(verbose_name="自定义授权代码", null=True, blank=True)
    # ApiPublic 主键列表，仅在隔离的认证上下文中按默认项后覆盖加载。
    public_variable_ids = models.JSONField(verbose_name="授权关联公共变量", default=list, blank=True)
    target_address = models.CharField(verbose_name="适用目标地址", max_length=1024, default='', blank=True)

    cache_keys = models.JSONField(verbose_name="缓存变量名", default=list, blank=True)
    cache_data = models.JSONField(verbose_name="授权缓存数据", default=dict, blank=True)
    token_ttl = models.IntegerField(verbose_name="Token有效期(分钟)", default=1440)
    refresh_margin = models.IntegerField(verbose_name="提前刷新时间(分钟)", default=10)
    expire_notice_minutes = models.IntegerField(verbose_name="到期提前通知时间(分钟)", default=30)
    expires_at = models.DateTimeField(verbose_name="过期时间", null=True, blank=True)
    expire_notice_sent_at = models.DateTimeField(verbose_name="到期通知发送时间", null=True, blank=True)

    last_refresh_time = models.DateTimeField(verbose_name="最近刷新时间", null=True, blank=True)
    last_refresh_status = models.SmallIntegerField(
        verbose_name="最近刷新状态",
        choices=ApiAuthRefreshStatusEnum.choices(),
        default=ApiAuthRefreshStatusEnum.INIT.value,
    )
    last_refresh_error = models.TextField(verbose_name="最近刷新错误", null=True, blank=True)

    # 0=执行时检测刷新，1=定时刷新，2=执行时检测+定时刷新
    refresh_mode = models.SmallIntegerField(
        verbose_name="刷新方式",
        choices=ApiAuthRefreshModeEnum.choices(),
        default=ApiAuthRefreshModeEnum.PASSIVE.value,
        db_index=True,
    )
    time_task = models.ForeignKey(
        to=TimeTasks,
        to_field="id",
        verbose_name="定时策略",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    notice_group = models.ForeignKey(
        to=NoticeGroup,
        to_field="id",
        verbose_name="到期通知组",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    refreshing = models.BooleanField(verbose_name="是否刷新中", default=False)
    refresh_lock_until = models.DateTimeField(verbose_name="刷新锁过期时间", null=True, blank=True)

    class Meta:
        db_table = 'api_auth_config'
        ordering = ['-id']
        unique_together = ('project_product', 'test_env', 'name')

    def __str__(self):
        return f"{self.project_product_id}:{self.test_env}:{self.name}"

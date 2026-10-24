from django.db import models
from mangotools.enums import StatusEnum

from src.apps.auto_ui.enums import UiAuthRefreshModeEnum, UiAuthRefreshStatusEnum, UiAuthTypeEnum
from src.apps.task_center.models import TimeTasks
from src.apps.test_center.enums.environment import EnvironmentEnum
from src.apps.test_center.models import NoticeGroup, ProjectProduct
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class UiPublic(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="ui_public_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    # Deprecated: 环境范围已迁移到 test_envs，保留用于历史数据回滚和后续清理。
    test_env = models.SmallIntegerField(
        verbose_name="测试环境",
        choices=EnvironmentEnum.choices(),
        null=True,
        blank=True,
        default=None,
    )
    test_envs = models.JSONField(verbose_name="适用环境", default=list, blank=True)
    # 0等于自定义，1等于sql，2等于登录，3等于header
    type = models.SmallIntegerField(verbose_name="自定义变量类型")
    name = models.CharField(verbose_name="名称", max_length=64)
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
    status = models.SmallIntegerField(verbose_name="状态", default=0)

    class Meta:
        db_table = 'ui_public'
        ordering = ['-id']


class UiAuthConfig(models.Model):
    """UI授权配置"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="ui_auth_config_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
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

    auth_type = models.SmallIntegerField(
        verbose_name="授权方式",
        choices=UiAuthTypeEnum.choices(),
        default=UiAuthTypeEnum.MANUAL.value,
        db_index=True,
    )
    cache_data = models.JSONField(verbose_name="授权缓存数据", default=dict, blank=True)
    manual_config = models.JSONField(verbose_name="手动复制配置", default=dict, blank=True)
    auto_auth_config = models.JSONField(verbose_name="自动授权配置", default=dict, blank=True)
    api_config = models.JSONField(verbose_name="接口转入配置", default=dict, blank=True)
    custom_code = models.TextField(verbose_name="自定义授权代码", null=True, blank=True)
    page_step = models.ForeignKey(
        to="PageSteps",
        to_field="id",
        verbose_name="登录页面步骤",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    token_ttl = models.IntegerField(verbose_name="授权有效期(分钟)", default=1440)
    expire_notice_minutes = models.IntegerField(verbose_name="到期提前通知时间(分钟)", default=30)
    expires_at = models.DateTimeField(verbose_name="过期时间", null=True, blank=True)
    expire_notice_sent_at = models.DateTimeField(verbose_name="到期通知发送时间", null=True, blank=True)

    last_refresh_time = models.DateTimeField(verbose_name="最近刷新时间", null=True, blank=True)
    last_refresh_status = models.SmallIntegerField(
        verbose_name="最近刷新状态",
        choices=UiAuthRefreshStatusEnum.choices(),
        default=UiAuthRefreshStatusEnum.INIT.value,
    )
    last_refresh_error = models.TextField(verbose_name="最近刷新错误", null=True, blank=True)
    refresh_mode = models.SmallIntegerField(
        verbose_name="刷新方式",
        choices=UiAuthRefreshModeEnum.choices(),
        default=UiAuthRefreshModeEnum.MANUAL.value,
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
        db_table = 'ui_auth_config'
        ordering = ['-id']
        unique_together = ('project_product', 'test_env', 'name')

    def __str__(self):
        return f"{self.project_product_id}:{self.test_env}:{self.name}"

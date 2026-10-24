from django.db import models

from src.apps.system.constants import SNOWFLAKE_SEQUENCE_KEY
from src.apps.system.enums.cache import SystemConfigManagementLevelEnum
from src.apps.system.exceptions import SYSTEM_ID_SEQUENCE_PROTECTED, SystemError
from src.apps.user.models import User


class CacheData(models.Model):
    """ 缓存表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="cache_data_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    describe = models.CharField(verbose_name="描述", max_length=1024, null=True, blank=True)
    key = models.CharField(verbose_name="key", max_length=128, unique=True)
    value = models.TextField(verbose_name="value", null=True, blank=True)
    value_type = models.SmallIntegerField(verbose_name="value的类型枚举", null=True, blank=True)
    group = models.CharField(verbose_name="配置分组", max_length=64, default="system")
    sort = models.IntegerField(verbose_name="排序", default=100)
    required = models.BooleanField(verbose_name="是否必填", default=False)
    is_enabled = models.BooleanField(verbose_name="是否启用", default=True)
    is_secret = models.BooleanField(verbose_name="是否敏感配置", default=False)
    management_level = models.PositiveSmallIntegerField(
        verbose_name="配置管理级别",
        choices=SystemConfigManagementLevelEnum.choices(),
        default=SystemConfigManagementLevelEnum.STANDARD.value,
    )
    placeholder = models.CharField(verbose_name="输入提示", max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'cache_data'

    def save(self, *args, **kwargs):
        using = kwargs.get('using') or self._state.db or 'default'
        if self.key == SNOWFLAKE_SEQUENCE_KEY or (
            self.pk and type(self).objects.using(using).filter(pk=self.pk, key=SNOWFLAKE_SEQUENCE_KEY).exists()
        ):
            raise SystemError(SYSTEM_ID_SEQUENCE_PROTECTED)
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.key == SNOWFLAKE_SEQUENCE_KEY:
            raise SystemError(SYSTEM_ID_SEQUENCE_PROTECTED)
        return super().delete(*args, **kwargs)

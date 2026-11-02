from django.db import models

from src.apps.system.enums.runtime_kv import RuntimeKVNamespaceEnum, RuntimeKVValueTypeEnum


class RuntimeKVEntry(models.Model):
    namespace = models.CharField('模块', max_length=64, choices=RuntimeKVNamespaceEnum.choices(),
                                 db_collation='utf8mb4_bin')
    key = models.CharField('业务键', max_length=192, db_collation='utf8mb4_bin')
    value_type = models.PositiveSmallIntegerField('值类型', choices=RuntimeKVValueTypeEnum.choices())
    value = models.JSONField('值内容', default=dict, blank=True)
    expires_at = models.DateTimeField('过期时间', null=True, blank=True)
    revision = models.PositiveBigIntegerField('修订号', default=1)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('修改时间', auto_now=True)

    class Meta:
        db_table = 'runtime_kv'
        verbose_name = '运行态键值数据'
        constraints = [models.UniqueConstraint(fields=['namespace', 'key'], name='uniq_runtime_kv_key')]
        indexes = [
            models.Index(fields=['expires_at', 'id'], name='idx_runtime_kv_expiry'),
            models.Index(fields=['namespace', 'id'], name='idx_runtime_kv_scan'),
        ]

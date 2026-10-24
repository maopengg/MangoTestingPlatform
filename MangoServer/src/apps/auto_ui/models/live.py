from django.db import models

from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class UiLiveStreamSession(models.Model):
    """UI实时画面会话表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    stream_id = models.CharField(verbose_name="直播会话ID", max_length=64, unique=True)
    user = models.ForeignKey(to=User, to_field="id", on_delete=models.CASCADE)
    executor_username = models.CharField(verbose_name="执行器账号", max_length=64, db_index=True)
    connection_id = models.CharField(verbose_name="执行器连接ID", max_length=128)
    execution_type = models.CharField(verbose_name="执行类型", max_length=64, db_index=True)
    execution_id = models.CharField(verbose_name="执行ID", max_length=128)
    resource_id = models.CharField(verbose_name="资源ID", max_length=128)
    read_only = models.BooleanField(verbose_name="是否只读", default=False)
    status = models.SmallIntegerField(verbose_name="状态", default=0, db_index=True)
    claims = models.JSONField(verbose_name="会话声明", default=dict, blank=True)

    class Meta:
        db_table = 'ui_live_stream_session'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['executor_username', 'status']),
        ]

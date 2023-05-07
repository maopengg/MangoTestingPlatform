from django.db import models

from PyAutoTest.auto_test.auto_user.models import Project
from PyAutoTest.auto_test.auto_user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class TestObject(models.Model):
    """测试对象"""
    environment = models.SmallIntegerField(verbose_name="环境备注")
    name = models.CharField(verbose_name="被测试的对象", max_length=64)
    value = models.CharField(verbose_name="被测试的对象", max_length=1024)
    # 0是web， 1是app， 2是小程序
    test_type = models.SmallIntegerField(verbose_name="对应什么客户端")
    executor_name = models.ForeignKey(to=User, to_field="id", on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'test_obj'
        ordering = ['-id']


class NoticeConfig(models.Model):
    """通知配置表"""
    team = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    type = models.SmallIntegerField(verbose_name="是否选中发送", null=True)
    config = models.CharField(verbose_name="通知配置", max_length=1028)
    state = models.SmallIntegerField(verbose_name="是否选中发送", null=True)

    class Meta:
        db_table = 'notice_config'
        ordering = ['-id']


class Database(models.Model):
    """数据库表"""
    team = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    test_obj = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="数据库名称", max_length=64)
    user = models.CharField(verbose_name="登录用户名", max_length=64, null=True)
    password = models.CharField(verbose_name="登录密码", max_length=64, null=True)
    host = models.CharField(verbose_name="数据库地址", max_length=64, null=True)
    post = models.IntegerField(verbose_name="端口", null=True)

    class Meta:
        db_table = 'data_base'
        ordering = ['-id']


class TimeTasks(models.Model):
    name = models.CharField(verbose_name="定时策略名称", max_length=64, null=True, unique=True)
    trigger_type = models.CharField(verbose_name="触发器类型", max_length=64, null=True)
    month = models.CharField(verbose_name="月", max_length=64, null=True)
    day = models.CharField(verbose_name="天", max_length=64, null=True)
    hour = models.CharField(verbose_name="小时", max_length=64, null=True)
    minute = models.CharField(verbose_name="分钟", max_length=64, null=True)

    class Meta:
        db_table = 'time_tasks'
        ordering = ['-id']

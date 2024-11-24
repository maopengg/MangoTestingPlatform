from django.db import models

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class Role(models.Model):
    """角色表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="角色名称", max_length=64)
    description = models.CharField(verbose_name="角色描述", max_length=64, null=True)

    class Meta:
        db_table = 'role'
        ordering = ['-id']


class User(models.Model):
    """用户表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="昵称", max_length=64, unique=True)
    username = models.CharField(verbose_name="登录账号", max_length=64, unique=True)
    password = models.CharField(verbose_name="登录密码", max_length=64)
    role = models.ForeignKey(to=Role, to_field="id", on_delete=models.SET_NULL, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True)
    mailbox = models.JSONField(verbose_name="邮箱", max_length=64, null=True)
    selected_project = models.SmallIntegerField(verbose_name="选中的项目ID", null=True)
    selected_environment = models.SmallIntegerField(verbose_name="选中的环境ID", null=True)
    last_login_time = models.DateTimeField(verbose_name="修改时间", null=True)
    config = models.JSONField(verbose_name="用户配置", null=True)

    class Meta:
        db_table = 'user'
        ordering = ['id']


class UserLogs(models.Model):
    """用户登录日志表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    user = models.ForeignKey(to=User, to_field="id", on_delete=models.SET_NULL, null=True)
    source_type = models.CharField(verbose_name="来源类型", max_length=64, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True)

    class Meta:
        db_table = 'user_logs'
        ordering = ['-create_time']

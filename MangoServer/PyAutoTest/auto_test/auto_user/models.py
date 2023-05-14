from django.db import models

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class Project(models.Model):
    """项目表"""
    name = models.CharField(verbose_name="项目组名称", max_length=64)
    status = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'project'
        ordering = ['-id']


class Role(models.Model):
    """角色表"""
    name = models.CharField(verbose_name="角色名称", max_length=64)
    description = models.CharField(verbose_name="角色描述", max_length=64, null=True)

    class Meta:
        db_table = 'role'
        ordering = ['-id']


class User(models.Model):
    """用户表"""
    nickname = models.CharField(verbose_name="昵称", max_length=64, null=True)
    username = models.CharField(verbose_name="登录账号", max_length=64, null=True)
    password = models.CharField(verbose_name="登录密码", max_length=64, null=True)
    role = models.ForeignKey(to=Role, to_field="id", on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True)
    lastLoginTime = models.TimeField(verbose_name="上次登录时间", null=True)
    mailbox = models.CharField(verbose_name="邮箱", max_length=64, null=True)

    class Meta:
        db_table = 'user'
        ordering = ['-id']

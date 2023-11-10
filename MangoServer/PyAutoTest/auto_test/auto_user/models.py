from django.db import models

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class Project(models.Model):
    """项目表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="项目名称", max_length=64)
    status = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'project'
        ordering = ['-id']


class ProjectModule(models.Model):
    """ 项目模块表 """
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    superior_module = models.CharField(verbose_name="上级模块名称", max_length=64)
    module_name = models.CharField(verbose_name="模块名称", max_length=64)

    class Meta:
        db_table = 'project_module'
        ordering = ['-id']


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
    nickname = models.CharField(verbose_name="昵称", max_length=64, null=True)
    username = models.CharField(verbose_name="登录账号", max_length=64, null=True)
    password = models.CharField(verbose_name="登录密码", max_length=64, null=True)
    role = models.ForeignKey(to=Role, to_field="id", on_delete=models.SET_NULL, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True)
    # 需要修改
    lastLoginTime = models.TimeField(verbose_name="上次登录时间", null=True)
    mailbox = models.CharField(verbose_name="邮箱", max_length=64, null=True)

    class Meta:
        db_table = 'user'
        ordering = ['id']

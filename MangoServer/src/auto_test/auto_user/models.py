from django.db import models

from src.exceptions import ToolsError

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

    def delete(self, *args, **kwargs):
        if User.objects.filter(role=self).exists():
            raise ToolsError(300, "用户-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class User(models.Model):
    """用户表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="昵称", max_length=64, unique=True)
    username = models.CharField(verbose_name="登录账号", max_length=64, unique=True)
    password = models.CharField(verbose_name="登录密码", max_length=64)
    role = models.ForeignKey(to=Role, to_field="id", on_delete=models.SET_NULL, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True)
    mailbox = models.JSONField(verbose_name="邮箱", max_length=64, default=list)
    selected_project = models.SmallIntegerField(verbose_name="选中的项目ID", null=True)
    selected_environment = models.SmallIntegerField(verbose_name="选中的环境ID", null=True)
    last_login_time = models.DateTimeField(verbose_name="修改时间", null=True)
    config = models.JSONField(verbose_name="用户配置", default=dict)

    class Meta:
        db_table = 'user'
        ordering = ['id']

    def delete(self, *args, **kwargs):
        from src.auto_test.auto_api.models import ApiCase
        if ApiCase.objects.filter(case_people=self).exists():
            raise ToolsError(300, "API测试用例-有关联数据，请先删除绑定的数据后再删除！")
        from src.auto_test.auto_ui.models import UiCase, UiConfig
        if UiCase.objects.filter(case_people=self).exists():
            raise ToolsError(300, "UI测试用例-有关联数据，请先删除绑定的数据后再删除！")
        from src.auto_test.auto_system.models import TestObject, Tasks, TestSuite
        if TestObject.objects.filter(executor_name=self).exists():
            raise ToolsError(300, "测试对象-有关联数据，请先删除绑定的数据后再删除！")
        if Tasks.objects.filter(case_people=self).exists():
            raise ToolsError(300, "定时任务-有关联数据，请先删除绑定的数据后再删除！")
        if TestSuite.objects.filter(user=self).exists():
            TestSuite.objects.filter(user=self).delete()
        if UiConfig.objects.filter(user=self).exists():
            UiConfig.objects.filter(user=self).delete()
        if UserLogs.objects.filter(user=self).exists():
            UserLogs.objects.filter(user=self).delete()
        super().delete(*args, **kwargs)


class UserLogs(models.Model):
    """用户登录日志表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    user = models.ForeignKey(to=User, to_field="id", on_delete=models.PROTECT)
    source_type = models.CharField(verbose_name="来源类型", max_length=64, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True)

    # url = models.CharField(verbose_name="url", max_length=64, null=True)
    # request_data = models.TextField(verbose_name="请求数据", null=True)
    # response_data = models.TextField(verbose_name="响应数据", null=True)

    class Meta:
        db_table = 'user_logs'
        ordering = ['-create_time']

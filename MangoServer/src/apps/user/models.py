import secrets

from django.apps import apps
from django.db import models

from src.apps.user.exceptions import (
    USER_GENERAL_USER_RELATION_DELETE_BINDING_INVALID,
    USER_GENERAL_CASE_RELATION_DELETE_BINDING_INVALID,
    USER_GENERAL_CASE_RELATION_DELETE_BINDING_INVALID_CODE_CASE_RELATION_DELETE_BINDING_INVALID,
    USER_GENERAL_TASK_RELATION_DELETE_BINDING_INVALID,
    USER_GENERAL_USER_RELATION_DELETE_BINDING_INVALID_CODE_USER_RELATION_DELETE_BINDING_INVALID,
    USER_GENERAL_PROJECT_PRODUCT_PERMISSION_RELATION_DELETE_BINDING_INVALID,
    USER_PROJECT_PRODUCT_OWNER_DELETE_BINDING_INVALID,
    UserError,
)

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class Role(models.Model):
    """角色表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    update_user = models.ForeignKey(to='User', to_field="id", related_name="role_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="角色名称", max_length=64)
    description = models.CharField(verbose_name="角色描述", max_length=64, null=True, blank=True)
    # {version: 1, menu_keys: [菜单键], endpoint_permissions: {接口ID: endpoint_allow|endpoint_deny}}
    authorization = models.JSONField(verbose_name="角色授权配置", default=dict, blank=True)

    class Meta:
        db_table = 'role'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if User.objects.filter(role=self).exists():
            raise UserError(USER_GENERAL_USER_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)


class User(models.Model):
    """用户表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    update_user = models.ForeignKey(to='User', to_field="id", related_name="user_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="昵称", max_length=64, unique=True)
    username = models.CharField(verbose_name="登录账号", max_length=64, unique=True)
    password = models.CharField(verbose_name="登录密码", max_length=1024)
    role = models.ForeignKey(to=Role, to_field="id", on_delete=models.SET_NULL, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True, blank=True)
    # [{key, name, value, value_type, description, clearable, updated_at}]，统一由 UserConfigService 维护。
    config = models.JSONField(verbose_name="用户配置", default=list, blank=True)
    api_key = models.CharField(verbose_name="MCP APIKey", max_length=128, unique=True, null=True, blank=True)
    is_super_admin = models.BooleanField(verbose_name="是否超级管理员", default=False)

    class Meta:
        db_table = 'user'
        ordering = ['id']

    def delete(self, *args, **kwargs):
        ApiCase = apps.get_model("auto_api", "ApiCase")
        if ApiCase.objects.filter(case_people=self).exists():
            raise UserError(USER_GENERAL_CASE_RELATION_DELETE_BINDING_INVALID)
        UiCase = apps.get_model("auto_ui", "UiCase")
        if UiCase.objects.filter(case_people=self).exists():
            raise UserError(USER_GENERAL_CASE_RELATION_DELETE_BINDING_INVALID_CODE_CASE_RELATION_DELETE_BINDING_INVALID)
        ProjectProduct = apps.get_model("test_center", "ProjectProduct")
        Tasks = apps.get_model("task_center", "Tasks")
        TestSuite = apps.get_model("test_center", "TestSuite")
        if ProjectProduct.objects.filter(owners=self).exists():
            raise UserError(USER_PROJECT_PRODUCT_OWNER_DELETE_BINDING_INVALID)
        if Tasks.objects.filter(case_people=self).exists():
            raise UserError(USER_GENERAL_TASK_RELATION_DELETE_BINDING_INVALID)
        if TestSuite.objects.filter(user=self).exists():
            TestSuite.objects.filter(user=self).delete()
        if UserLogs.objects.filter(user=self).exists():
            UserLogs.objects.filter(user=self).delete()
        super().delete(*args, **kwargs)

    @staticmethod
    def generate_api_key() -> str:
        return f"mango_{secrets.token_urlsafe(32)}"

    @classmethod
    def unique_api_key(cls) -> str:
        api_key = cls.generate_api_key()
        while cls.objects.filter(api_key=api_key).exists():
            api_key = cls.generate_api_key()
        return api_key


class Department(models.Model):
    """部门表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="department_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="部门名称", max_length=64, unique=True)
    status = models.SmallIntegerField(verbose_name="状态", default=1)
    description = models.CharField(verbose_name="部门描述", max_length=128, null=True, blank=True)

    class Meta:
        db_table = 'department'
        ordering = ['id']

    def delete(self, *args, **kwargs):
        if UserDepartment.objects.filter(department=self).exists():
            raise UserError(USER_GENERAL_USER_RELATION_DELETE_BINDING_INVALID_CODE_USER_RELATION_DELETE_BINDING_INVALID)
        if DepartmentProjectProductPermission.objects.filter(department=self).exists():
            raise UserError(USER_GENERAL_PROJECT_PRODUCT_PERMISSION_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)


class UserDepartment(models.Model):
    """用户部门关联表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="user_department_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(to=User, to_field="id", on_delete=models.CASCADE)
    department = models.ForeignKey(to=Department, to_field="id", on_delete=models.PROTECT)

    class Meta:
        db_table = 'user_department'
        ordering = ['id']
        unique_together = ('user', 'department')


class DepartmentProjectProductPermission(models.Model):
    """部门可访问项目产品表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="department_project_product_permission_update_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    department = models.ForeignKey(to=Department, to_field="id", on_delete=models.CASCADE)
    project_product = models.ForeignKey(to='test_center.ProjectProduct', to_field="id", on_delete=models.CASCADE)

    class Meta:
        db_table = 'department_project_product_permission'
        ordering = ['id']
        unique_together = ('department', 'project_product')


class UserLogs(models.Model):
    """用户登录日志表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    user = models.ForeignKey(to=User, to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    source_type = models.CharField(verbose_name="来源类型", max_length=64, null=True, blank=True)
    ip = models.CharField(verbose_name="IP", max_length=64, null=True, blank=True)

    url = models.CharField(verbose_name="url", max_length=256, null=True, blank=True)
    method = models.CharField(verbose_name="method", max_length=64, null=True, blank=True)
    status_code = models.CharField(verbose_name="status_code", max_length=64, null=True, blank=True)
    request_data = models.TextField(verbose_name="请求数据", null=True, blank=True)
    response_data = models.TextField(verbose_name="响应数据", null=True, blank=True)

    class Meta:
        db_table = 'user_logs'
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['-create_time', 'user'], name='idx_user_log_time_user'),
            models.Index(fields=['user', '-create_time'], name='idx_user_log_user_time'),
        ]

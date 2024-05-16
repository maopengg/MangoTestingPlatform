from django.db import models

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class Project(models.Model):
    """项目表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="项目名称", max_length=64, unique=True)
    bucket_name = models.CharField(verbose_name="上传文件存放的文件夹", max_length=64, null=True)
    status = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'project'
        ordering = ['-id']


class ProjectProduct(models.Model):
    """项目产品表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="产品名称", max_length=64)
    # 0是web， 1是app， 2是小程序
    type = models.SmallIntegerField(verbose_name="对应什么客户端")

    class Meta:
        db_table = 'project_product'
        ordering = ['-id']


class ProductModule(models.Model):
    """ 产品模块表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="模块名称", max_length=64)
    superior_module = models.CharField(verbose_name="上级模块名称", max_length=64, null=True)

    class Meta:
        db_table = 'product_module'
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
    username = models.CharField(verbose_name="登录账号", max_length=64, null=True, unique=True)
    password = models.CharField(verbose_name="登录密码", max_length=64, null=True)
    role = models.ForeignKey(to=Role, to_field="id", on_delete=models.SET_NULL, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True)
    # 需要修改
    last_login_time = models.DateTimeField(verbose_name="上次登录时间", null=True)
    mailbox = models.CharField(verbose_name="邮箱", max_length=64, null=True)
    selected_project = models.SmallIntegerField(verbose_name="选中的项目ID", null=True)
    selected_environment = models.SmallIntegerField(verbose_name="选中的环境ID", null=True)

    class Meta:
        db_table = 'user'
        ordering = ['id']


class UserLogs(models.Model):
    """用户登录日志表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    nickname = models.CharField(verbose_name="昵称", max_length=64, null=True)
    username = models.CharField(verbose_name="登录账号", max_length=64, null=True)
    source_type = models.CharField(verbose_name="来源类型", max_length=64, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True)
    user_id = models.SmallIntegerField(verbose_name="选中的项目ID", null=True)

    class Meta:
        db_table = 'user_logs'
        ordering = ['-create_time']

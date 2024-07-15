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
    auto_type = models.SmallIntegerField(verbose_name="自动化类型")
    client_type = models.SmallIntegerField(verbose_name="客户端类型")

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
    nickname = models.CharField(verbose_name="昵称", max_length=64, null=True, unique=True)
    username = models.CharField(verbose_name="登录账号", max_length=64, null=True, unique=True)
    password = models.CharField(verbose_name="登录密码", max_length=64, null=True)
    role = models.ForeignKey(to=Role, to_field="id", on_delete=models.SET_NULL, null=True)
    ip = models.CharField(verbose_name="登录IP", max_length=64, null=True)
    mailbox = models.JSONField(verbose_name="邮箱", max_length=64, null=True)
    selected_project = models.SmallIntegerField(verbose_name="选中的项目ID", null=True)
    selected_environment = models.SmallIntegerField(verbose_name="选中的环境ID", null=True)
    last_login_time = models.DateTimeField(verbose_name="修改时间",  null=True)

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


class TestObject(models.Model):
    """测试对象"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    executor_name = models.ForeignKey(to=User, to_field="id", on_delete=models.SET_NULL, null=True)
    environment = models.SmallIntegerField(verbose_name="环境备注")
    name = models.CharField(verbose_name="被测试的对象", max_length=64)
    value = models.CharField(verbose_name="被测试的对象", max_length=1024)
    db_c_status = models.SmallIntegerField(verbose_name="查询权限", null=True)
    db_rud_status = models.SmallIntegerField(verbose_name="增删改权限", null=True)

    class Meta:
        db_table = 'test_object'
        ordering = ['-id']


class FileData(models.Model):
    """ 文件表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    type = models.SmallIntegerField(verbose_name="类型", null=True)
    name = models.CharField(verbose_name="文件名称", max_length=64, null=True)
    price = models.DecimalField(verbose_name="文件大小", max_digits=10, decimal_places=2, null=True)
    file = models.FileField(verbose_name='文件', upload_to='files/', null=True)

    class Meta:
        db_table = 'file_data'

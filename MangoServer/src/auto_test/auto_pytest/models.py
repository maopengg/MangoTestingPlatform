from django.db import models

from src.auto_test.auto_system.models import ProductModule
from src.auto_test.auto_system.models import ProjectProduct, TasksDetails
from src.auto_test.auto_user.models import User
from src.exceptions import ToolsError


class PytestProduct(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="名称", max_length=1024, null=True)
    file_name = models.CharField(verbose_name="文件名称", max_length=1024)
    init_file = models.CharField(verbose_name="__init__文件", max_length=1024, null=True)
    auto_type = models.SmallIntegerField(verbose_name="自动化类型", default=0)

    class Meta:
        db_table = 'pytest_product'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class PytestAct(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=PytestProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="自定义ACT名称", max_length=1024)
    file_name = models.CharField(verbose_name="文件名称", max_length=1024)
    file_path = models.CharField(verbose_name="文件路径", max_length=1024)
    file_status = models.SmallIntegerField(verbose_name="文件状态", default=0)
    file_update_time = models.DateTimeField(verbose_name="文档修改时间")

    class Meta:
        db_table = 'pytest_act'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class PytestCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=PytestProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.SET_NULL, null=True)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.SET_NULL,
                                    null=True)
    name = models.CharField(verbose_name="自定义用例名称", max_length=1024)
    level = models.SmallIntegerField(verbose_name="用例级别", default=1)
    status = models.SmallIntegerField(verbose_name="状态", default=0)
    file_name = models.CharField(verbose_name="文件名称", max_length=1024)
    file_path = models.CharField(verbose_name="文件路径", max_length=1024)
    file_status = models.SmallIntegerField(verbose_name="文件状态", default=0)
    file_update_time = models.DateTimeField(verbose_name="文档修改时间")
    result_data = models.JSONField(verbose_name='最新一次测试结果', null=True)

    class Meta:
        db_table = 'pytest_case'

    def delete(self, *args, **kwargs):
        if TasksDetails.objects.filter(pytest_case=self).exists():
            raise ToolsError(300, "定时任务详情-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class PytestTools(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=PytestProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="自定义用例名称", max_length=1024)
    file_name = models.CharField(verbose_name="文件名称", max_length=1024)
    file_path = models.CharField(verbose_name="文件路径", max_length=1024)
    file_status = models.SmallIntegerField(verbose_name="文件状态", default=0)
    file_update_time = models.DateTimeField(verbose_name="文档修改时间")

    class Meta:
        db_table = 'pytest_tools'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class PytestTestFile(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=PytestProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="文件名称", max_length=1024)
    file_name = models.CharField(verbose_name="带目录的文件名称", max_length=1024)
    file_path = models.CharField(verbose_name="文件路径", max_length=1024)
    file_update_time = models.DateTimeField(verbose_name="文档修改时间")

    class Meta:
        db_table = 'pytest_test_file'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

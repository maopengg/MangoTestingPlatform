from django.db import models

from src.auto_test.auto_system.models import ProjectProduct


class PytestProject(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="目录名称", max_length=1024, null=True)

    class Meta:
        db_table = 'pytest_project'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class PytestProjectModule(models.Model):
    """ 产品模块表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    pytest_project = models.ForeignKey(to=PytestProject, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="模块目录名称", max_length=64)

    class Meta:
        db_table = 'product_module'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class PytestInit(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    pytest_project = models.ForeignKey(to=PytestProject, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="目录名称", max_length=1024, null=True)

    class Meta:
        db_table = 'pytest_init'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class PytestAct(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    pytest_project = models.ForeignKey(to=PytestProject, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=PytestProjectModule, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="自定义ACT名称", max_length=1024, null=True)
    file_name = models.CharField(verbose_name="文件名称", max_length=1024, null=True)

    class Meta:
        db_table = 'pytest_act'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class PytestCae(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    pytest_project = models.ForeignKey(to=PytestProject, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=PytestProjectModule, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="自定义用例名称", max_length=1024, null=True)
    file_name = models.CharField(verbose_name="文件名称", max_length=1024, null=True)

    class Meta:
        db_table = 'pytest_case'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class PytestUpload(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    pytest_project = models.ForeignKey(to=PytestProject, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=PytestProjectModule, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="文件名称", max_length=1024, null=True)

    class Meta:
        db_table = 'pytest_upload'

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

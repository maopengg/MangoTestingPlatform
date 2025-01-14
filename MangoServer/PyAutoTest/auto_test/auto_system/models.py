from django.db import models

from PyAutoTest.auto_test.auto_user.models import User
from PyAutoTest.exceptions import ToolsError

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class Project(models.Model):
    """项目表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="项目名称", max_length=64, unique=True)
    status = models.SmallIntegerField(verbose_name="状态", default=1)

    class Meta:
        db_table = 'project'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if ProjectProduct.objects.filter(project=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的产品后再删除！")
        if FileData.objects.filter(project=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的测试文件后再删除！")
        super().delete(*args, **kwargs)


class ProjectProduct(models.Model):
    """项目产品表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="产品名称", max_length=64)
    client_type = models.SmallIntegerField(verbose_name="客户端类型")
    auto_type = models.SmallIntegerField(verbose_name="自动化类型")

    class Meta:
        db_table = 'project_product'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if ProductModule.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的产品模块后再删除！")
        if TestObject.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的测试对象后再删除！")
        from PyAutoTest.auto_test.auto_api.models import ApiPublic, ApiCase, ApiInfo
        if ApiInfo.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的接口信息后再删除！")
        if ApiCase.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的API用例后再删除！")
        if ApiPublic.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的API全局参数后再删除！")
        from PyAutoTest.auto_test.auto_ui.models import UiPublic, UiCase, PageSteps, Page
        if Page.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的UI页面后再删除！")
        if PageSteps.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的页面步骤后再删除！")
        if UiCase.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的UI用例后再删除！")
        if UiPublic.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的UI全局参数后再删除！")
        if Tasks.objects.filter(project_product=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的定时任务后再删除！")
        if TestSuiteDetails.objects.filter(project_product=self).exists():
            TestSuiteDetails.objects.filter(project_product=self).delete()
        if TestSuite.objects.filter(project_product=self).exists():
            TestSuite.objects.filter(project_product=self).delete()
        super().delete(*args, **kwargs)


class ProductModule(models.Model):
    """ 产品模块表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="模块名称", max_length=64)
    superior_module_1 = models.CharField(verbose_name="一级模块模块名称", max_length=64, null=True)
    superior_module_2 = models.CharField(verbose_name="二级模块模块名称", max_length=64, null=True)

    class Meta:
        db_table = 'product_module'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        from PyAutoTest.auto_test.auto_api.models import ApiCase, ApiInfo
        if ApiInfo.objects.filter(module=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的接口信息后再删除！")
        if ApiCase.objects.filter(module=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的API用例后再删除！")
        from PyAutoTest.auto_test.auto_ui.models import UiCase, PageSteps, Page
        if UiCase.objects.filter(module=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的UI用例后再删除！")
        if Page.objects.filter(module=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的UI页面后再删除！")
        if PageSteps.objects.filter(module=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的页面步骤后再删除！")
        super().delete(*args, **kwargs)


class TestObject(models.Model):
    """测试对象"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    executor_name = models.ForeignKey(to=User, to_field="id", on_delete=models.SET_NULL, null=True)
    environment = models.SmallIntegerField(verbose_name="环境备注")
    name = models.CharField(verbose_name="被测试的对象", max_length=64)
    value = models.CharField(verbose_name="被测试的对象", max_length=1024)
    db_c_status = models.SmallIntegerField(verbose_name="查询权限")
    db_rud_status = models.SmallIntegerField(verbose_name="增删改权限")
    auto_type = models.SmallIntegerField(verbose_name="自动化使用类型")

    class Meta:
        db_table = 'test_object'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if NoticeConfig.objects.filter(test_object=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的通知配置后再删除！")
        if Database.objects.filter(test_object=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的数据库配置后再删除！")
        super().delete(*args, **kwargs)


class NoticeConfig(models.Model):
    """通知配置表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_object = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)
    type = models.SmallIntegerField(verbose_name="类型")
    config = models.CharField(verbose_name="通知配置", max_length=1028)
    status = models.SmallIntegerField(verbose_name="是否选中发送", default=0)

    class Meta:
        db_table = 'notice_config'
        ordering = ['-id']


class Database(models.Model):
    """数据库表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_object = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="数据库名称", max_length=64)
    user = models.CharField(verbose_name="登录用户名", max_length=64)
    password = models.CharField(verbose_name="登录密码", max_length=64)
    host = models.CharField(verbose_name="数据库地址", max_length=64)
    port = models.IntegerField(verbose_name="端口")
    status = models.SmallIntegerField(verbose_name="是否启用", default=0)

    class Meta:
        db_table = 'data_base'
        ordering = ['-id']




class FileData(models.Model):
    """ 文件表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    type = models.SmallIntegerField(verbose_name="类型")
    name = models.CharField(verbose_name="文件名称", max_length=64)
    price = models.DecimalField(verbose_name="文件大小", max_digits=10, decimal_places=2)
    file = models.FileField(verbose_name='文件', upload_to='files/')

    class Meta:
        db_table = 'file_data'


class TimeTasks(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="定时策略名称", max_length=64, unique=True)
    cron = models.CharField(verbose_name="cron表达式", max_length=64)

    class Meta:
        db_table = 'time_tasks'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if Tasks.objects.filter(timing_strategy=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的定时任务后再删除！")
        super().delete(*args, **kwargs)


class Tasks(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    name = models.CharField(verbose_name="任务名称", max_length=64)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.SET_NULL,
                                    null=True)
    type = models.SmallIntegerField(verbose_name="任务类型")
    status = models.SmallIntegerField(verbose_name="任务状态")
    timing_strategy = models.ForeignKey(to=TimeTasks, to_field="id", on_delete=models.SET_NULL, null=True)
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知")

    class Meta:
        db_table = 'tasks'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if TasksDetails.objects.filter(task=self).exists():
            raise ToolsError(300, "有关联数据，请先删除绑定的任务明细后再删除！")
        # if TestSuite.objects.filter(tasks=self).exists():
        #     TestSuite.objects.filter(tasks=self).delete()
        super().delete(*args, **kwargs)


class TasksDetails(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    task = models.ForeignKey(to=Tasks, to_field="id", on_delete=models.SET_NULL, null=True)
    case_id = models.SmallIntegerField(verbose_name="用例ID", null=True)
    command = models.TextField(verbose_name="命令", null=True)

    class Meta:
        db_table = 'tasks_details'
        ordering = ['-id']


class CacheData(models.Model):
    """ 缓存表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    describe = models.CharField(verbose_name="描述", max_length=1024, null=True)
    key = models.CharField(verbose_name="key", max_length=128)
    value = models.TextField(verbose_name="value", null=True)
    value_type = models.SmallIntegerField(verbose_name="value的类型枚举", null=True)
    case_type = models.SmallIntegerField(verbose_name="用例类型", null=True)
    case_id = models.SmallIntegerField(verbose_name="绑定的用例ID", null=True)

    class Meta:
        db_table = 'cache_data'


class TestSuite(models.Model):
    id = models.BigIntegerField(primary_key=True, editable=False)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    # type=0是UI,=1是接口,=2是性能
    type = models.SmallIntegerField(verbose_name="类型")
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    user = models.ForeignKey(to=User, to_field="id", verbose_name='用例执行人', on_delete=models.SET_NULL, null=True)
    tasks = models.ForeignKey(to=Tasks, to_field="id", on_delete=models.SET_NULL, null=True)

    status = models.SmallIntegerField(verbose_name="测试结果")
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知")

    class Meta:
        db_table = 'test_suite'
        ordering = ['-create_time']

    def delete(self, *args, **kwargs):
        if TestSuiteDetails.objects.filter(test_suite=self).exists():
            TestSuiteDetails.objects.filter(test_suite=self).delete()
        super().delete(*args, **kwargs)


class TestSuiteDetails(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_suite = models.ForeignKey(to=TestSuite, to_field="id", on_delete=models.SET_NULL, null=True)
    # type=0是UI,=1是接口,=2是性能
    type = models.SmallIntegerField(verbose_name="类型")
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    case_id = models.SmallIntegerField(verbose_name="用例ID")
    case_name = models.CharField(verbose_name="key", max_length=528, null=True)  # 制作展示用
    # 2待开始，3是进行中，0是失败，1是成功
    status = models.SmallIntegerField(verbose_name="测试结果")
    error_message = models.TextField(verbose_name="错误提示", null=True)
    result_data = models.JSONField(verbose_name="用例缓存数据", null=True)
    retry = models.SmallIntegerField(verbose_name="重试次数")
    push_time = models.DateTimeField(verbose_name="修改时间", null=True)

    class Meta:
        db_table = 'test_suite_details'
        ordering = ['-create_time']

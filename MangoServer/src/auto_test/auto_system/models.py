from django.db import models, transaction

from src.auto_test.auto_user.models import User
from src.exceptions import ToolsError

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
            raise ToolsError(300, "项目产品-有关联数据，请先删除绑定的数据后再删除！")
        if NoticeGroup.objects.filter(project=self).exists():
            raise ToolsError(300, "通知组-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class ProjectProduct(models.Model):
    """项目产品表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="产品名称", max_length=64, unique=True)
    ui_client_type = models.SmallIntegerField(verbose_name="UI客户端类型", default=0)
    api_client_type = models.SmallIntegerField(verbose_name="API客户端类型", default=0)

    class Meta:
        db_table = 'project_product'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if ProductModule.objects.filter(project_product=self).exists():
            raise ToolsError(300, "产品模块-有关联数据，请先删除绑定的数据后再删除！")
        if TestObject.objects.filter(project_product=self).exists():
            raise ToolsError(300, "测试对象-有关联数据，请先删除绑定的数据后再删除！")
        from src.auto_test.auto_api.models import ApiPublic, ApiCase, ApiInfo, ApiHeaders
        if ApiInfo.objects.filter(project_product=self).exists():
            raise ToolsError(300, "接口信息-有关联数据，请先删除绑定的数据后再删除！")
        if ApiCase.objects.filter(project_product=self).exists():
            raise ToolsError(300, "API用例-有关联数据，请先删除绑定的数据后再删除！")
        if ApiPublic.objects.filter(project_product=self).exists():
            raise ToolsError(300, "API全局参数-有关联数据，请先删除绑定的数据后再删除！")
        if ApiHeaders.objects.filter(project_product=self).exists():
            raise ToolsError(300, "API请求头-有关联数据，请先删除绑定的数据后再删除！")
        from src.auto_test.auto_ui.models import UiPublic, UiCase, PageSteps, Page
        if Page.objects.filter(project_product=self).exists():
            raise ToolsError(300, "UI页面-有关联数据，请先删除绑定的数据后再删除！")
        if PageSteps.objects.filter(project_product=self).exists():
            raise ToolsError(300, "页面步骤-有关联数据，请先删除绑定的数据后再删除！")
        if UiCase.objects.filter(project_product=self).exists():
            raise ToolsError(300, "UI用例-有关联数据，请先删除绑定的数据后再删除！")
        if UiPublic.objects.filter(project_product=self).exists():
            raise ToolsError(300, "UI全局参数-有关联数据，请先删除绑定的数据后再删除！")
        if Tasks.objects.filter(project_product=self).exists():
            raise ToolsError(300, "定时任务-有关联数据，请先删除绑定的数据后再删除！")
        from src.auto_test.auto_pytest.models import PytestProduct
        if PytestProduct.objects.filter(project_product=self).exists():
            raise ToolsError(300, "项目绑定-有关联数据，请先删除绑定的数据后再删除！")
        if TestSuiteDetails.objects.filter(project_product=self).exists():
            TestSuiteDetails.objects.filter(project_product=self).delete()
        if TestSuite.objects.filter(project_product=self).exists():
            TestSuite.objects.filter(project_product=self).delete()
        super().delete(*args, **kwargs)


class ProductModule(models.Model):
    """ 产品模块表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="模块名称", max_length=64)
    superior_module_1 = models.CharField(verbose_name="一级模块模块名称", max_length=64, null=True)
    superior_module_2 = models.CharField(verbose_name="二级模块模块名称", max_length=64, null=True)

    class Meta:
        db_table = 'product_module'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        from src.auto_test.auto_api.models import ApiCase, ApiInfo
        if ApiInfo.objects.filter(module=self).exists():
            raise ToolsError(300, "接口信息-有关联数据，请先删除绑定的数据后再删除！")
        if ApiCase.objects.filter(module=self).exists():
            raise ToolsError(300, "API用例-有关联数据，请先删除绑定的数据后再删除！")
        from src.auto_test.auto_ui.models import UiCase, PageSteps, Page
        if UiCase.objects.filter(module=self).exists():
            raise ToolsError(300, "UI用例-有关联数据，请先删除绑定的数据后再删除！")
        if Page.objects.filter(module=self).exists():
            raise ToolsError(300, "UI页面-有关联数据，请先删除绑定的数据后再删除！")
        if PageSteps.objects.filter(module=self).exists():
            raise ToolsError(300, "页面步骤-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class TestObject(models.Model):
    """测试对象"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    executor_name = models.ForeignKey(to=User, to_field="id", on_delete=models.PROTECT)
    environment = models.SmallIntegerField(verbose_name="环境备注")
    name = models.CharField(verbose_name="被测试的对象", max_length=64)
    value = models.CharField(verbose_name="被测试的对象", max_length=1024)
    db_c_status = models.SmallIntegerField(verbose_name="查询权限", default=0)
    db_rud_status = models.SmallIntegerField(verbose_name="增删改权限", default=0)
    auto_type = models.SmallIntegerField(verbose_name="自动化使用类型", default=0)

    class Meta:
        db_table = 'test_object'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if Database.objects.filter(test_object=self).exists():
            raise ToolsError(300, "数据库配置-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class NoticeGroup(models.Model):
    """通知组表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="通知组名称", max_length=64)
    mail = models.JSONField(verbose_name="邮箱", default=list)
    feishu = models.CharField(verbose_name="飞书通知", max_length=255, null=True)
    dingding = models.CharField(verbose_name="钉钉通知", max_length=255, null=True)
    work_weixin = models.CharField(verbose_name="企业微信通知", max_length=255, null=True)

    class Meta:
        db_table = 'notice_group'
        ordering = ['-id']


class Database(models.Model):
    """数据库表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_object = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.PROTECT)
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
    type = models.SmallIntegerField(verbose_name="类型")
    name = models.CharField(verbose_name="文件名称", max_length=255, unique=True)
    test_file = models.FileField(verbose_name='文件', upload_to='test_file/', null=True)
    failed_screenshot = models.ImageField(verbose_name='失败截图', upload_to='failed_screenshot/', null=True)

    class Meta:
        db_table = 'file_data'

    def delete(self, *args, **kwargs):
        if self.test_file:
            self.test_file.delete()
        if self.failed_screenshot:
            self.failed_screenshot.delete()
        super().delete(*args, **kwargs)


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
            raise ToolsError(300, "定时任务-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class Tasks(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    test_env = models.SmallIntegerField(verbose_name="测试环境", default=0)
    name = models.CharField(verbose_name="任务名称", max_length=64)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.PROTECT)
    status = models.SmallIntegerField(verbose_name="任务状态", default=0)
    timing_strategy = models.ForeignKey(to=TimeTasks, to_field="id", on_delete=models.PROTECT)
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知", default=0)
    notice_group = models.ForeignKey(to=NoticeGroup, to_field="id", verbose_name='通知组', on_delete=models.SET_NULL,
                                     null=True)

    class Meta:
        db_table = 'tasks'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if TasksDetails.objects.filter(task=self).exists():
            raise ToolsError(300, "任务明细-有关联数据，请先删除绑定的数据后再删除！")
        if TestSuite.objects.filter(tasks=self).exists():
            TestSuite.objects.filter(tasks=self).delete()
        super().delete(*args, **kwargs)


class TasksDetails(models.Model):
    type = models.SmallIntegerField(verbose_name="任务类型", default=0)
    task = models.ForeignKey(to='Tasks', to_field="id", on_delete=models.PROTECT)
    ui_case = models.ForeignKey(to='auto_ui.UiCase', to_field="id", on_delete=models.SET_NULL, null=True)
    api_case = models.ForeignKey(to='auto_api.ApiCase', to_field="id", on_delete=models.SET_NULL, null=True)
    pytest_case = models.ForeignKey(to='auto_pytest.PytestCase', to_field="id", on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'tasks_details'
        ordering = ['-id']


class CacheData(models.Model):
    """ 缓存表 """
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    describe = models.CharField(verbose_name="描述", max_length=1024, null=True)
    key = models.CharField(verbose_name="key", max_length=128, unique=True)
    value = models.TextField(verbose_name="value", null=True)
    value_type = models.SmallIntegerField(verbose_name="value的类型枚举", null=True)

    class Meta:
        db_table = 'cache_data'


class TestSuite(models.Model):
    id = models.BigIntegerField(primary_key=True, editable=False)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    user = models.ForeignKey(to=User, to_field="id", verbose_name='用例执行人', on_delete=models.PROTECT)
    tasks = models.ForeignKey(to=Tasks, to_field="id", on_delete=models.SET_NULL, null=True)

    status = models.SmallIntegerField(verbose_name="测试结果")
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知")

    class Meta:
        db_table = 'test_suite'
        ordering = ['-create_time']

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            TestSuiteDetails.objects.filter(test_suite=self).delete()
            super().delete(*args, **kwargs)


class TestSuiteDetails(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_suite = models.ForeignKey(to=TestSuite, to_field="id", on_delete=models.CASCADE)
    # type=0是UI,=1是接口,=2是pytest
    type = models.SmallIntegerField(verbose_name="类型")
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    case_id = models.SmallIntegerField(verbose_name="用例ID")
    case_name = models.CharField(verbose_name="key", max_length=528, null=True)
    parametrize = models.JSONField(verbose_name="参数化", default=list)
    # 2待开始，3是进行中，0是失败，1是成功
    status = models.SmallIntegerField(verbose_name="测试结果")
    error_message = models.TextField(verbose_name="错误提示", null=True)
    result_data = models.JSONField(verbose_name="用例缓存数据", null=True)
    retry = models.SmallIntegerField(verbose_name="重试次数")
    push_time = models.DateTimeField(verbose_name="修改时间", null=True)
    case_sum = models.SmallIntegerField(verbose_name="用例数", default=0)
    success = models.SmallIntegerField(verbose_name="成功数", default=0)
    fail = models.SmallIntegerField(verbose_name="失败数", default=0)
    warning = models.SmallIntegerField(verbose_name="警告数", default=0)

    class Meta:
        db_table = 'test_suite_details'
        ordering = ['-create_time']

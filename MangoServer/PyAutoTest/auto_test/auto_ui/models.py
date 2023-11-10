from django.db import models

from PyAutoTest.auto_test.auto_user.models import Project, ProjectModule
from PyAutoTest.auto_test.auto_user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class UiPage(models.Model):
    """页面表"""
    create_Time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="页面名称", max_length=64)
    url = models.CharField(verbose_name="url", max_length=128)
    # 0是web，1是小程序， 3是app
    type = models.SmallIntegerField(verbose_name="页面是什么端")

    class Meta:
        db_table = 'ui_page'
        ordering = ['-id']


class UiElement(models.Model):
    """页面元素表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    page = models.ForeignKey(to=UiPage, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="元素名称", max_length=64)
    exp = models.SmallIntegerField(verbose_name="元素表达式")
    loc = models.CharField(verbose_name="元素定位", max_length=1048)
    sleep = models.IntegerField(verbose_name="等待时间", null=True)
    sub = models.IntegerField(verbose_name="下标", null=True)

    class Meta:
        db_table = 'ui_ele'
        ordering = ['-id']


class UiPageSteps(models.Model):
    """页面步骤表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    page = models.ForeignKey(to=UiPage, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="步骤名称", max_length=64)
    run_flow = models.CharField(verbose_name="步骤顺序", max_length=2000, null=True)
    # 0和空等于调试用例，1等于调试完成
    type = models.SmallIntegerField(verbose_name="步骤类型", null=True)

    class Meta:
        db_table = 'ui_page_steps'
        ordering = ['-id']


class UiPageStepsDetailed(models.Model):
    """步骤详情表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    page_step = models.ForeignKey(to=UiPageSteps, to_field="id", on_delete=models.SET_NULL, null=True)
    ele_name_a = models.ForeignKey(to=UiElement, to_field="id", related_name='related_UiElement_a',
                                   on_delete=models.SET_NULL, null=True)
    ele_name_b = models.ForeignKey(to=UiElement, to_field="id", related_name='related_UiElement_b',
                                   on_delete=models.SET_NULL, null=True)
    step_sort = models.IntegerField(verbose_name="顺序的排序", null=True)
    ope_type = models.CharField(verbose_name="对该元素的操作类型", max_length=1048, null=True)
    ope_value = models.CharField(verbose_name="操作内容", max_length=1048, null=True)
    # type==0是进行操作，==1是进行断言
    type = models.SmallIntegerField(verbose_name="操作类型", null=True)
    ass_type = models.CharField(verbose_name="断言类型", max_length=1048, null=True)
    ass_value = models.CharField(verbose_name="操作内容", max_length=1048, null=True)

    class Meta:
        db_table = 'ui_page_steps_detailed'
        ordering = ['-id']


class UiCase(models.Model):
    """用例表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    module_name = models.ForeignKey(to=ProjectModule, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="用例组名称", max_length=64)
    case_flow = models.CharField(verbose_name="步骤顺序", max_length=2000, null=True)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', related_name='related_case_people',
                                    on_delete=models.SET_NULL, null=True)
    # 0失败，1成功，2警告
    state = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'ui_case'
        ordering = ['-id']


class UiCaseStepsDetailed(models.Model):
    """用例详情表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    case = models.ForeignKey(to=UiCase, to_field="id", on_delete=models.SET_NULL, null=True)
    page_step = models.ForeignKey(to=UiPageSteps, to_field="id", on_delete=models.SET_NULL, null=True)
    case_sort = models.IntegerField(verbose_name="用例排序", null=True)
    case_cache_data = models.TextField(verbose_name="用例缓存数据", null=True)
    case_cache_ass = models.TextField(verbose_name="步骤缓存断言", null=True)

    class Meta:
        db_table = 'ui_case_steps_detailed'
        ordering = ['-id']


class UiPublic(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="名称", max_length=64)
    key = models.CharField(verbose_name="键", max_length=128, null=True)
    value = models.CharField(verbose_name="值", max_length=2048, null=True)
    state = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'ui_public'
        ordering = ['-id']


class UiConfig(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    user_id = models.ForeignKey(to=User, to_field="id", on_delete=models.SET_NULL, null=True)
    # 0是web，1是安卓
    type = models.SmallIntegerField(verbose_name="什么客户端", null=True)
    browser_port = models.CharField(verbose_name="web端口", max_length=64, null=True)
    browser_path = models.CharField(verbose_name="chrome路径", max_length=1024, null=True)
    browser_type = models.SmallIntegerField(verbose_name="浏览器类型", null=True)
    equipment = models.CharField(verbose_name="安卓设备名称", max_length=64, null=True)
    # 0关闭，1开启
    is_headless = models.SmallIntegerField(verbose_name="状态", null=True)
    # 0未选中，1选中
    state = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'ui_config'
        ordering = ['-id']


class UiCaseResult(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_suite_id = models.BigIntegerField(verbose_name="测试套件id", null=True)
    case_id = models.IntegerField(verbose_name="用例ID", null=True)
    case_name = models.CharField(verbose_name="用例名称", max_length=64, null=True)
    module_name = models.CharField(verbose_name="模块名称", max_length=64, null=True)
    case_people = models.CharField(verbose_name="负责人名称", max_length=64, null=True)
    test_obj = models.CharField(verbose_name="测试环境", max_length=1024, null=True)
    case_cache_data = models.TextField(verbose_name="用例缓存数据", null=True)
    status = models.SmallIntegerField(verbose_name="用例测试结果", null=True)

    class Meta:
        db_table = 'ui_case_result'


class UiPageStepsResult(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_suite_id = models.BigIntegerField(verbose_name="测试套件id", null=True)
    case_id = models.IntegerField(verbose_name="用例ID", null=True)
    page_step_id = models.IntegerField(verbose_name="步骤id", null=True)
    page_step_name = models.CharField(verbose_name="步骤名称", max_length=64, null=True)
    status = models.SmallIntegerField(verbose_name="步骤测试结果", null=True)

    class Meta:
        db_table = 'ui_page_steps_result'


class UiEleResult(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_suite_id = models.BigIntegerField(verbose_name="测试套件id", null=True)
    case_id = models.IntegerField(verbose_name="用例ID", null=True)
    page_step_id = models.IntegerField(verbose_name="步骤id", null=True)
    ele_name_a = models.CharField(verbose_name="元素名称A", max_length=64, null=True)
    ele_name_b = models.CharField(verbose_name="元素名称B", max_length=64, null=True)
    ele_quantity = models.SmallIntegerField(verbose_name="元素个数", null=True)
    status = models.SmallIntegerField(verbose_name="元素测试结果", null=True)
    picture_path = models.CharField(verbose_name="用例名称", max_length=1000, null=True)
    exp = models.SmallIntegerField(verbose_name="元素表达式", null=True)
    loc = models.CharField(verbose_name="元素定位", max_length=1048, null=True)
    sleep = models.IntegerField(verbose_name="等待时间", null=True)
    sub = models.IntegerField(verbose_name="下标", null=True)
    ope_type = models.CharField(verbose_name="对该元素的操作类型", max_length=1048, null=True)
    ope_value = models.CharField(verbose_name="操作内容", max_length=1048, null=True)
    ass_type = models.CharField(verbose_name="断言类型", max_length=1048, null=True)
    ass_value = models.CharField(verbose_name="操作内容", max_length=1048, null=True)

    class Meta:
        db_table = 'ui_ele_result'

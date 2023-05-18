from django.db import models

from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_system.models import TimeTasks
from PyAutoTest.auto_test.auto_user.models import Project
from PyAutoTest.auto_test.auto_user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class UiPage(models.Model):
    """页面表"""
    team = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="页面名称", max_length=64)
    url = models.CharField(verbose_name="url", max_length=128)
    # 0是web，1是小程序， 3是app
    type = models.SmallIntegerField(verbose_name="页面是什么端")

    class Meta:
        db_table = 'ui_page'
        ordering = ['-id']


class UiElement(models.Model):
    """元素定位表"""
    name = models.CharField(verbose_name="元素名称", max_length=64)
    exp = models.SmallIntegerField(verbose_name="元素表达式")
    loc = models.CharField(verbose_name="元素定位", max_length=1048)
    page = models.ForeignKey(to=UiPage, to_field="id", on_delete=models.SET_NULL, null=True)
    sleep = models.IntegerField(verbose_name="等待时间", null=True)
    sub = models.IntegerField(verbose_name="下标", null=True)

    class Meta:
        db_table = 'ui_ele'
        ordering = ['-id']


class UiCase(models.Model):
    """UI用例表"""
    team = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="用例名称", max_length=64)
    run_flow = models.CharField(verbose_name="执行顺序的展示", max_length=2000, null=True)
    state = models.SmallIntegerField(verbose_name="状态", null=True)
    # 0是web，1是app，2是小程序
    case_type = models.SmallIntegerField(verbose_name="用例的类型", null=True)
    # 0和空等于调试用例，1等于测试用例，5等于已经被设置为定时执行
    type = models.SmallIntegerField(verbose_name="用例的类型", null=True)

    class Meta:
        db_table = 'ui_case'
        ordering = ['-id']


class UiCaseGroup(models.Model):
    team = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    test_obj = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="用例组名称", max_length=64)
    case_id = models.CharField(verbose_name="存放组内所有用例ID", max_length=1048, null=True)
    case_name = models.CharField(verbose_name="存放组内所有用例名称", max_length=1048, null=True)
    # 0失败，1成功，2警告
    state = models.SmallIntegerField(verbose_name="状态", null=True)
    time_name = models.ForeignKey(to=TimeTasks, to_field="id", on_delete=models.SET_NULL, null=True)
    timing_actuator = models.ForeignKey(to=User, to_field="id", related_name='related_timing_actuator',
                                        verbose_name='定时执行的设备', on_delete=models.SET_NULL, null=True)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', related_name='related_case_people',
                                    on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'ui_case_group'
        ordering = ['-id']


class RunSort(models.Model):
    el_page = models.ForeignKey(to=UiPage, to_field="id", on_delete=models.SET_NULL, null=True)
    el_name = models.ForeignKey(to=UiElement, to_field="id", on_delete=models.SET_NULL, null=True)
    case = models.ForeignKey(to=UiCase, to_field="id", on_delete=models.SET_NULL, null=True)
    ope_type = models.SmallIntegerField(verbose_name="对该元素的操作类型", null=True)
    ass_type = models.SmallIntegerField(verbose_name="断言类型", null=True)
    ope_value = models.CharField(verbose_name="操作内容", max_length=1048, null=True)
    ope_value_key = models.CharField(verbose_name="输入内容的key，用来保存变量", max_length=64, null=True)
    ass_value = models.CharField(verbose_name="操作内容", max_length=1048, null=True)
    run_sort = models.IntegerField(verbose_name="执行顺序的展示", null=True)

    class Meta:
        db_table = 'ui_run_sort'
        ordering = ['-id']


class UiPublic(models.Model):
    team = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="名称", max_length=64)
    key = models.CharField(verbose_name="键", max_length=128, null=True)
    value = models.CharField(verbose_name="值", max_length=2048, null=True)
    state = models.SmallIntegerField(verbose_name="状态", null=True)
    # 0是公共参数，1是公共断言
    type = models.SmallIntegerField(verbose_name="公共类型", null=True)

    class Meta:
        db_table = 'ui_public'
        ordering = ['-id']


class UiResult(models.Model):
    team = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    case = models.ForeignKey(to=UiCase, to_field="id", on_delete=models.SET_NULL, null=True)
    test_obj = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)
    case_group = models.ForeignKey(to=UiCaseGroup, to_field="id", on_delete=models.SET_NULL, null=True)
    ele_name = models.CharField(verbose_name="元素名称", max_length=1048, null=True)
    # 1存在元素， 2不存在元素，3存在多个元素
    existence = models.SmallIntegerField(verbose_name="元素执行的情况", null=True)
    picture = models.CharField(verbose_name="图片路径或名称", max_length=1048, null=True)
    msg = models.CharField(verbose_name="失败提示日志", max_length=1048, null=True)
    # 0失败，1成功，2警告
    state = models.SmallIntegerField(verbose_name="结果", null=True)

    class Meta:
        db_table = 'ui_result'
        ordering = ['-id']


class UiConfig(models.Model):
    user_id = models.ForeignKey(to=User, to_field="id", on_delete=models.SET_NULL, null=True)
    local_port = models.CharField(verbose_name="web端口", max_length=64, null=True)
    browser_path = models.CharField(verbose_name="chrome路径", max_length=1024, null=True)
    equipment = models.CharField(verbose_name="安卓设备名称", max_length=64, null=True)
    package = models.CharField(verbose_name="app包名称", max_length=64, null=True)

    class Meta:
        db_table = 'ui_config'
        ordering = ['-id']


class UiMethod(models.Model):
    type = models.SmallIntegerField(verbose_name="设备类型", null=True)
    method = models.CharField(verbose_name="函数名称", max_length=64, null=True)
    introduce = models.CharField(verbose_name="介绍", max_length=64, null=True)
    parameter = models.JSONField(verbose_name="参数", max_length=1024, null=True)
    is_ass = models.SmallIntegerField(verbose_name="是否是断言", null=True)

    class Meta:
        db_table = 'ui_method'
        ordering = ['-id']

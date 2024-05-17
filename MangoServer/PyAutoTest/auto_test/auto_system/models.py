from django.db import models

from PyAutoTest.auto_test.auto_user.models import ProjectProduct, TestObject, Project
from PyAutoTest.auto_test.auto_user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class NoticeConfig(models.Model):
    """通知配置表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    type = models.SmallIntegerField(verbose_name="类型", null=True)
    config = models.CharField(verbose_name="通知配置", max_length=1028, null=True)
    status = models.SmallIntegerField(verbose_name="是否选中发送", null=True)

    class Meta:
        db_table = 'notice_config'
        ordering = ['-id']


class Database(models.Model):
    """数据库表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    test_obj = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="数据库名称", max_length=64)
    user = models.CharField(verbose_name="登录用户名", max_length=64, null=True)
    password = models.CharField(verbose_name="登录密码", max_length=64, null=True)
    host = models.CharField(verbose_name="数据库地址", max_length=64, null=True)
    port = models.IntegerField(verbose_name="端口", null=True)

    class Meta:
        db_table = 'data_base'
        ordering = ['-id']


class TimeTasks(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="定时策略名称", max_length=64, null=True, unique=True)
    trigger_type = models.CharField(verbose_name="触发器类型", max_length=64, null=True)
    month = models.CharField(verbose_name="月", max_length=64, null=True)
    day = models.CharField(verbose_name="天", max_length=64, null=True)
    day_of_week = models.CharField(verbose_name="周", max_length=64, null=True)
    hour = models.CharField(verbose_name="小时", max_length=64, null=True)
    minute = models.CharField(verbose_name="分钟", max_length=64, null=True)

    class Meta:
        db_table = 'time_tasks'
        ordering = ['-id']


class TestSuiteReport(models.Model):
    id = models.BigIntegerField(primary_key=True, editable=False)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    # type=0是UI,=1是接口,=2是性能
    type = models.SmallIntegerField(verbose_name="类型", null=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.SET_NULL, null=True)
    test_object = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)

    error_message = models.TextField(verbose_name="错误提示", null=True)
    # 0是进行中，1是已完成
    run_status = models.SmallIntegerField(verbose_name="执行状态", null=True)
    # null是待测试完成，0是失败，1是成功
    status = models.SmallIntegerField(verbose_name="测试结果", null=True)
    case_list = models.JSONField(verbose_name='测试套包含的用例列表', null=True)
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知", null=True)
    user = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.SET_NULL, null=True)

    class Meta:
        db_table = 'test_suite_report'
        ordering = ['-create_time']


class ScheduledTasks(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_obj = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="任务名称", max_length=64)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.SET_NULL, null=True)
    case_executor = models.JSONField(verbose_name='用例执行人', null=True)
    type = models.SmallIntegerField(verbose_name="任务类型", null=True)
    status = models.SmallIntegerField(verbose_name="任务状态", null=True)
    timing_strategy = models.ForeignKey(to=TimeTasks, to_field="id", on_delete=models.SET_NULL, null=True)
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知", null=True)

    class Meta:
        db_table = 'scheduled_tasks'
        ordering = ['-id']


class TasksRunCaseList(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    task = models.ForeignKey(to=ScheduledTasks, to_field="id", on_delete=models.SET_NULL, null=True)
    case = models.SmallIntegerField(verbose_name="api_case_id", null=True)
    test_object = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)
    sort = models.SmallIntegerField(verbose_name="api_case_id", null=True)

    class Meta:
        db_table = 'tasks_run_case_list'
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

from django.db import models

from src.auto_test.auto_system.models import ProjectProduct, ProductModule
from src.auto_test.auto_user.models import User
from src.exceptions import ToolsError

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class Page(models.Model):
    """页面表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="页面名称", max_length=64)
    url = models.CharField(verbose_name="url", max_length=1048)

    class Meta:
        db_table = 'page'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if PageSteps.objects.filter(page=self).exists():
            raise ToolsError(300, "页面步骤-有关联数据，请先删除绑定的数据后再删除！")
        if PageElement.objects.filter(page=self).exists():
            raise ToolsError(300, "元素-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class PageElement(models.Model):
    """页面元素表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    page = models.ForeignKey(to=Page, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="元素名称", max_length=64)
    exp = models.SmallIntegerField(verbose_name="元素表达式")
    loc = models.TextField(verbose_name="元素定位")
    exp2 = models.SmallIntegerField(verbose_name="元素表达式", null=True)
    loc2 = models.TextField(verbose_name="元素定位", null=True)
    exp3 = models.SmallIntegerField(verbose_name="元素表达式", null=True)
    loc3 = models.TextField(verbose_name="元素定位", null=True)
    sleep = models.SmallIntegerField(verbose_name="等待时间", null=True)
    sub = models.SmallIntegerField(verbose_name="下标", null=True)
    sub2 = models.SmallIntegerField(verbose_name="下标2", null=True)
    sub3 = models.SmallIntegerField(verbose_name="下标3", null=True)
    is_iframe = models.SmallIntegerField(verbose_name="是否在iframe里面", null=True)
    prompt = models.TextField(verbose_name="AI元素定位提示词", null=True)

    class Meta:
        db_table = 'page_element'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if PageStepsDetailed.objects.filter(ele_name=self).exists():
            raise ToolsError(300, "页面步骤详情-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class PageSteps(models.Model):
    """页面步骤表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    page = models.ForeignKey(to=Page, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="步骤名称", max_length=64)
    run_flow = models.TextField(verbose_name="步骤顺序", null=True)
    status = models.SmallIntegerField(verbose_name="状态", default=2)
    result_data = models.JSONField(verbose_name="测试结果", null=True)
    flow_data = models.JSONField(verbose_name="flow_data", default=dict)

    class Meta:
        db_table = 'page_steps'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if PageStepsDetailed.objects.filter(page_step=self).exists():
            raise ToolsError(300, "页面步骤详情-有关联数据，请先删除绑定的数据后再删除！")
        if UiCaseStepsDetailed.objects.filter(page_step=self).exists():
            raise ToolsError(300, "用例步骤详情-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class PageStepsDetailed(models.Model):
    """步骤详情表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    page_step = models.ForeignKey(to=PageSteps, to_field="id", on_delete=models.PROTECT)
    # type==0是进行操作，==1是进行断言
    type = models.SmallIntegerField(verbose_name="操作类型")
    ele_name = models.ForeignKey(to=PageElement, to_field="id", on_delete=models.SET_NULL, null=True)
    step_sort = models.IntegerField(verbose_name="顺序的排序")
    # 操作和断言
    ope_key = models.CharField(verbose_name="对该元素的操作类型", max_length=1048, null=True)
    ope_value = models.JSONField(verbose_name="对该元素的操作类型", null=True)
    # sql
    sql_execute = models.JSONField(verbose_name="sql步骤", null=True)
    key_list = models.JSONField(verbose_name="sql查询结果的key_list", null=True)
    sql = models.CharField(verbose_name="sql", max_length=1048, null=True)
    # 自定义
    custom = models.JSONField(verbose_name="自定义缓存步骤", null=True)
    key = models.CharField(verbose_name="key", max_length=1048, null=True)
    value = models.CharField(verbose_name="value", max_length=1048, null=True)
    # 条件
    condition_value = models.JSONField(verbose_name="条件判断", null=True)
    # func
    func = models.TextField(verbose_name="func", null=True)

    class Meta:
        db_table = 'page_steps_detailed'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)


class UiCase(models.Model):
    """用例表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="用例组名称", max_length=64)
    case_flow = models.TextField(verbose_name="步骤顺序", null=True)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.PROTECT)
    parametrize = models.JSONField(verbose_name="参数化", default=list)
    # 0失败，1成功，2待开始，3，进行中
    status = models.SmallIntegerField(verbose_name="状态", default=2)
    level = models.SmallIntegerField(verbose_name="用例级别", default=0)
    front_custom = models.JSONField(verbose_name="前置自定义", default=list)
    front_sql = models.JSONField(verbose_name="前置sql", default=list)
    posterior_sql = models.JSONField(verbose_name="后置sql", default=list)

    class Meta:
        db_table = 'ui_case'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if UiCaseStepsDetailed.objects.filter(case=self).exists():
            raise ToolsError(300, "页面步骤详情-有关联数据，请先删除绑定的数据后再删除！")
        from src.auto_test.auto_system.models import TasksDetails
        if TasksDetails.objects.filter(ui_case=self).exists():
            raise ToolsError(300, "定时任务详情-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class UiCaseStepsDetailed(models.Model):
    """用例详情表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    case = models.ForeignKey(to=UiCase, to_field="id", on_delete=models.PROTECT)
    page_step = models.ForeignKey(to=PageSteps, to_field="id", on_delete=models.PROTECT)
    case_sort = models.SmallIntegerField(verbose_name="用例排序")
    case_data = models.JSONField(verbose_name="用例步骤数据", null=True)
    switch_step_open_url = models.SmallIntegerField(verbose_name="是否在执行页面的时候切换url", default=0)
    error_retry = models.SmallIntegerField(verbose_name="失败重试", null=True)
    # 0失败，1成功
    status = models.SmallIntegerField(verbose_name="状态", default=2)
    error_message = models.TextField(verbose_name="错误提示", null=True)
    result_data = models.JSONField(verbose_name="最近一次执行结果", null=True)

    class Meta:
        db_table = 'ui_case_steps_detailed'


class UiPublic(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    # 0等于自定义，1等于sql，2等于登录，3等于header
    type = models.SmallIntegerField(verbose_name="自定义变量类型")
    name = models.CharField(verbose_name="名称", max_length=64)
    key = models.CharField(verbose_name="键", max_length=128)
    value = models.TextField(verbose_name="值")
    status = models.SmallIntegerField(verbose_name="状态", default=0)

    class Meta:
        db_table = 'ui_public'
        ordering = ['-id']

#
# class UiConfig(models.Model):
#     create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
#     update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
#     user = models.ForeignKey(to=User, to_field="id", on_delete=models.PROTECT)
#     # 0是web，1是安卓
#     type = models.SmallIntegerField(verbose_name="什么客户端")
#     config = models.JSONField(verbose_name="配置json")
#     # 是否开启
#     status = models.SmallIntegerField(verbose_name="状态", default=0)
#
#     class Meta:
#         db_table = 'ui_config'
#         ordering = ['-id']

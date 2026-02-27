from django.db import models

from src.auto_test.auto_system.models import ProjectProduct, ProductModule
from src.auto_test.auto_user.models import User
from src.enums.tools_enum import StatusEnum
from src.exceptions import ToolsError

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class ApiInfo(models.Model):
    """api用例表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    # 0和空等于录制，1等于本期接口，2是调试完成
    type = models.SmallIntegerField(verbose_name='接口的类型', default=1)
    name = models.CharField(verbose_name="接口名称", max_length=1024)

    url = models.CharField(verbose_name="请求url", max_length=1024)
    method = models.SmallIntegerField(verbose_name="请求方法")
    headers = models.JSONField(verbose_name="请求头", null=True)
    params = models.TextField(verbose_name="参数", null=True)
    is_text_params = models.SmallIntegerField(verbose_name="请求方法", default=StatusEnum.SUCCESS.value)
    data = models.TextField(verbose_name="data", null=True)
    is_text_data = models.SmallIntegerField(verbose_name="请求方法", default=StatusEnum.SUCCESS.value)
    json = models.TextField(verbose_name="json", null=True)
    is_text_json = models.SmallIntegerField(verbose_name="请求方法", default=StatusEnum.SUCCESS.value)
    file = models.JSONField(verbose_name="file", null=True)

    posterior_json_path = models.JSONField(verbose_name="后置jsonpath提取", default=list)
    posterior_re = models.JSONField(verbose_name="后置正则提取", default=list)
    posterior_func = models.TextField(verbose_name='后置自定义', null=True)
    posterior_file = models.CharField(verbose_name="下载文件名称key", max_length=1024, null=True)

    status = models.SmallIntegerField(verbose_name="状态", default=2)
    result_data = models.JSONField(verbose_name="最近一次执行结果", null=True)

    class Meta:
        db_table = 'api_info'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if ApiCaseDetailed.objects.filter(api_info=self).exists():
            raise ToolsError(300, "测试用例详情-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class ApiCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    name = models.CharField(verbose_name="测试用例名称", max_length=64)
    case_flow = models.TextField(verbose_name="步骤顺序", null=True)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.PROTECT)

    parametrize = models.JSONField(verbose_name="参数化", default=list)
    level = models.SmallIntegerField(verbose_name="用例级别", default=1)
    front_custom = models.JSONField(verbose_name="前置方法", default=list)
    front_sql = models.JSONField(verbose_name="前置sql", default=list)
    front_headers = models.JSONField(verbose_name="前置请求头", default=list)
    posterior_sql = models.JSONField(verbose_name="后置sql", default=list)
    status = models.SmallIntegerField(verbose_name="状态", default=2)

    class Meta:
        db_table = 'api_case'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if ApiCaseDetailed.objects.filter(case=self).exists():
            raise ToolsError(300, "测试用例详情-有关联数据，请先删除绑定的数据后再删除！")
        from src.auto_test.auto_system.models import TasksDetails
        if TasksDetails.objects.filter(api_case=self).exists():
            raise ToolsError(300, "定时任务详情-有关联数据，请先删除绑定的数据后再删除！")
        super().delete(*args, **kwargs)


class ApiCaseDetailed(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    case = models.ForeignKey(to=ApiCase, to_field="id", on_delete=models.PROTECT)
    api_info = models.ForeignKey(to=ApiInfo, to_field="id", on_delete=models.PROTECT)
    case_sort = models.IntegerField(verbose_name="用例排序", null=True)
    status = models.SmallIntegerField(verbose_name="状态", default=2)
    error_message = models.TextField(verbose_name="失败提示", null=True)

    class Meta:
        db_table = 'api_case_detailed'

    def delete(self, *args, **kwargs):
        if ApiCaseDetailedParameter.objects.filter(case_detailed=self).exists():
            ApiCaseDetailedParameter.objects.filter(case_detailed=self).delete()
        super().delete(*args, **kwargs)


    # def clean(self):
    #     if self.status not in [StatusEnum.FAIL, StatusEnum.SUCCESS]:
    #         raise ValidationError("状态值只能是 0 或 1")
    #     super().clean()
class ApiCaseDetailedParameter(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    case_detailed = models.ForeignKey(to=ApiCaseDetailed, to_field="id", on_delete=models.PROTECT)
    error_retry = models.SmallIntegerField(verbose_name="失败重试", null=True)
    retry_interval = models.SmallIntegerField(verbose_name="重试间隔", null=True)
    name = models.CharField(verbose_name="步骤名称", max_length=128)
    headers = models.JSONField(verbose_name="请求头", default=list)
    is_case_headers = models.SmallIntegerField(verbose_name="是否使用用例headers", default=StatusEnum.SUCCESS.value)
    params = models.TextField(verbose_name="参数", null=True)
    data = models.TextField(verbose_name="data", null=True)
    json = models.TextField(verbose_name="json", null=True)
    file = models.JSONField(verbose_name="file", null=True)

    # 前置
    front_sql = models.JSONField(verbose_name="前置sql", default=list)
    front_func = models.TextField(verbose_name='前置自定义函数', null=True)
    # 断言
    ass_general = models.JSONField(verbose_name="sql断言", default=list)
    ass_sql = models.JSONField(verbose_name="sql断言", default=list)
    ass_json_all = models.JSONField(verbose_name="响应JSON全匹配断言", null=True)
    ass_text_all = models.TextField(verbose_name="响应文本全匹配断言", null=True)
    ass_jsonpath = models.JSONField(verbose_name="响应jsonpath断言", default=list)
    # 后置
    posterior_sql = models.JSONField(verbose_name="后置sql", default=list)
    posterior_response = models.JSONField(verbose_name="后置响应处理", default=list)
    posterior_response_text = models.JSONField(verbose_name="后置响应文本处理", default=list)
    posterior_sleep = models.SmallIntegerField(verbose_name="强制等待", null=True)
    posterior_file = models.JSONField(verbose_name="文件下载", default=dict)
    posterior_func = models.TextField(verbose_name='后置自定义', null=True)
    status = models.SmallIntegerField(verbose_name="状态", default=2)
    result_data = models.JSONField(verbose_name="最近一次执行结果", null=True)

    class Meta:
        db_table = 'api_case_detailed_parameter'


class ApiHeaders(models.Model):
    """api公共"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    key = models.CharField(verbose_name="键", max_length=128)
    value = models.TextField(verbose_name="值")
    status = models.SmallIntegerField(verbose_name="是否默认开启", default=0)

    class Meta:
        db_table = 'api_headers'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        # if ApiCaseSuiteDetailed.objects.filter(case_suite=self).exists():
        #     raise ToolsError(300, "有关联数据，请先删除绑定的用例套件详情后再删除！")
        super().delete(*args, **kwargs)


class ApiPublic(models.Model):
    """api公共"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    # 0等于自定义，1等于sql，2等于登录
    type = models.SmallIntegerField(verbose_name="自定义变量类型", default=0)
    name = models.CharField(verbose_name="名称", max_length=64)
    key = models.CharField(verbose_name="键", max_length=128)
    value = models.TextField(verbose_name="值")
    status = models.SmallIntegerField(verbose_name="状态", default=0)

    class Meta:
        db_table = 'api_public'
        ordering = ['-id']

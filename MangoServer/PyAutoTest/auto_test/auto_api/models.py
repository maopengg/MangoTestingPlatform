from django.db import models

from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_system.models import TimeTasks
from PyAutoTest.auto_test.auto_user.models import Project

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class ApiCase(models.Model):
    """api用例表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    # 0和空等于调试用例，1等于本期接口，2等于自动化用例，5等于已经被设置为定时执行
    type = models.SmallIntegerField(verbose_name='接口的类型')
    name = models.CharField(verbose_name="用例名称", max_length=64)
    client = models.SmallIntegerField(verbose_name="什么端")
    method = models.SmallIntegerField(verbose_name="请求方法")
    url = models.CharField(verbose_name="请求url", max_length=1024)
    header = models.CharField(verbose_name="请求头", max_length=2048, null=True)
    body = models.TextField(verbose_name="请求数据", null=True)
    body_type = models.SmallIntegerField(verbose_name="请求数据类型", null=True)
    rely = models.CharField(verbose_name="依赖的用例id", max_length=100, null=True)
    ass = models.SmallIntegerField(verbose_name="断言", null=True)
    state = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'api_case'
        ordering = ['-id']


class ApiCaseGroup(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    time_name = models.ForeignKey(to=TimeTasks, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="测试组名称", max_length=64)
    case_id = models.CharField(verbose_name="存放组内所有用例ID", max_length=1048, null=True)
    case_name = models.CharField(verbose_name="存放组内所有用例名称", max_length=1048, null=True)
    # 0失败，1成功，2警告
    state = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'api_case_group'
        ordering = ['-id']


# class ApiRelyOn(models.Model):
#     """api依赖表"""
#     project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
#     case = models.ForeignKey(to=ApiCase, to_field="id", on_delete=models.SET_NULL, null=True)
#     name = models.CharField(verbose_name="前置需要处理的名称", max_length=64)
#     rely_type = models.SmallIntegerField(verbose_name="处理的类型", null=True)
#     value = models.CharField(verbose_name="处理的值", max_length=1048, null=True)
#     # 0是前置，1是后置
#     type = models.SmallIntegerField(verbose_name="前置还是后置", null=True)
#
#     class Meta:
#         db_table = 'api_rely_on'
#         ordering = ['-id']


class ApiPublic(models.Model):
    """api公共"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    # 0是公共参数，1是公共断言
    type = models.SmallIntegerField(verbose_name="公共类型", null=True)
    client = models.SmallIntegerField(verbose_name="什么端", null=True)
    # 0等于自定义，1等于sql，2等于登录，3等于header
    public_type = models.SmallIntegerField(verbose_name="值的类型", null=True)
    name = models.CharField(verbose_name="名称", max_length=64)
    key = models.CharField(verbose_name="键", max_length=128, null=True)
    value = models.CharField(verbose_name="值", max_length=2048, null=True)
    state = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'api_public'
        ordering = ['-id']


class ApiAssertions(models.Model):
    """api断言表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    case = models.ForeignKey(to=ApiCase, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="依赖名称", max_length=64)
    ass_type = models.SmallIntegerField(verbose_name="依赖类型", null=True)
    value = models.CharField(verbose_name="值", max_length=1048, null=True)

    class Meta:
        db_table = 'api_ass'
        ordering = ['-id']


class ApiResult(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    case = models.ForeignKey(to=ApiCase, to_field="id", on_delete=models.SET_NULL, null=True)
    test_obj = models.ForeignKey(to=TestObject, to_field="id", on_delete=models.SET_NULL, null=True)
    case_group = models.ForeignKey(to=ApiCaseGroup, to_field="id", on_delete=models.SET_NULL, null=True)
    request_url = models.CharField(verbose_name="请求的url", max_length=1048, null=True)
    request_header = models.TextField(verbose_name="请求头", null=True)
    request_body = models.TextField(verbose_name="请求体", null=True)
    response_header = models.TextField(verbose_name="响应头", null=True)
    response_body = models.TextField(verbose_name="响应体", null=True)
    code = models.IntegerField(verbose_name='响应的code码', null=True)
    response_time = models.TimeField(verbose_name='响应时间', null=True)
    # 0失败，1成功，2警告
    ass_res = models.SmallIntegerField(verbose_name="断言结果", null=True)

    class Meta:
        db_table = 'api_result'
        ordering = ['-id']
#
#
# class MockModel(models.Model):
#     """
#     mock model
#     """
#     relate_interface = models.CharField(max_length=255, default='', verbose_name='关联接口')
#     mock_data_id = models.IntegerField(default=-1, verbose_name="对应mock数据id")
#     service = models.CharField(max_length=255, default="", verbose_name="服务方")
#     origin_url = models.CharField(max_length=500, default="", verbose_name="正常url地址")
#     create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
#     remark = models.CharField(max_length=500, verbose_name="备注")
#     status = models.CharField(max_length=10, default='notDefault', verbose_name="是否默认状态")
#     update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
#
#     class Meta:
#         db_table = 't_mock'
#         verbose_name = 'mock数据表'
#         verbose_name_plural = verbose_name
#
#
# class MockDataModel(models.Model):
#     """
#     mock data model
#     """
#     # id = models.IntegerField(auto_created=True,unique=True, primary_key=True, verbose_name="id")
#     mockName = models.CharField(max_length=255, null=False, default='', verbose_name="mock名")
#     # interface = models.ForeignKey(to=InterfaceModel, to_field='interface', related_name='related_mock', on_delete=models.SET(''), verbose_name='接口名' )
#     interface_name_id = models.CharField(max_length=255, default='', verbose_name="关联接口")
#     data = models.TextField(verbose_name="mock数据")
#     author = models.CharField(max_length=50, null=False, default='', verbose_name='创建者')
#     thirdpart = models.CharField(max_length=255, default='', verbose_name="三方接口")
#     status = models.CharField(max_length=255, default='undefault', verbose_name="mock状态")
#     status_code = models.IntegerField(default=200, verbose_name='状态码')
#     timeout = models.IntegerField(default=0, verbose_name="超时时长")
#     remarks = models.CharField(max_length=500, verbose_name="备注")
#     create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
#     update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
#
#     class Meta:
#         db_table = 't_mock_data'
#         verbose_name = 'mock表'
#         verbose_name_plural = verbose_name
#
#     def get_object(self):
#         """
#         :return:
#         """
#         return self.mockName
#
#
# # mock服务表
# class MockServiceModel(models.Model):
#     service = models.CharField(max_length=255, null=False, default='', verbose_name="服务名")
#     status = models.CharField(max_length=255, default='1', verbose_name="状态")
#     author = models.CharField(max_length=50, null=False, default='', verbose_name='创建者')
#     remarks = models.CharField(max_length=500, default='', verbose_name="备注")
#     create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
#     update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
#
#     class Meta:
#         db_table = 't_mock_service'
#         verbose_name = 'mock服务名表'
#         verbose_name_plural = verbose_name
#
#     def __unicode__(self):
#         return self.service
#
#
# # interface_mock_map表
# class MockInterfaceMapModel(models.Model):
#     interface = models.ForeignKey(to=InterfaceModel, to_field='interface', on_delete=models.SET(""), verbose_name="接口名")
#     mockIds = models.CharField(max_length=500, default='', verbose_name="关联mockId")
#     remarks = models.CharField(max_length=500, default='', verbose_name="备注")
#     create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
#     update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
#
#     class Meta:
#         db_table = 't_mock_interface_map'
#         verbose_name = 'mock与接口对应关系表'
#         verbose_name_plural = verbose_name

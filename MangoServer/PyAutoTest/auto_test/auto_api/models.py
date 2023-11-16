from django.db import models

from PyAutoTest.auto_test.auto_system.models import TestObject
from PyAutoTest.auto_test.auto_system.models import TimeTasks
from PyAutoTest.auto_test.auto_user.models import Project, User, ProjectModule

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class ApiInfo(models.Model):
    """api用例表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    # 0和空等于调试用例，1等于本期接口，2是调试完成
    type = models.SmallIntegerField(verbose_name='接口的类型')
    module_name = models.ForeignKey(to=ProjectModule, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="接口名称", max_length=64)
    client = models.SmallIntegerField(verbose_name="什么端")
    url = models.CharField(verbose_name="请求url", max_length=1024)
    method = models.SmallIntegerField(verbose_name="请求方法")
    header = models.JSONField(verbose_name="请求头", max_length=2048, null=True)
    params = models.JSONField(verbose_name="参数", null=True)
    data = models.TextField(verbose_name="data", null=True)
    json = models.JSONField(verbose_name="json", null=True)
    ass = models.JSONField(verbose_name="公共断言", null=True)
    # 0失败， 1是成功
    status = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'api_info'
        ordering = ['-id']


class ApiCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project = models.ForeignKey(to=Project, to_field="id", on_delete=models.SET_NULL, null=True)
    name = models.CharField(verbose_name="测试用例名称", max_length=64)
    case_flow = models.CharField(verbose_name="步骤顺序", max_length=2000, null=True)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.SET_NULL, null=True)
    # 0失败，1成功，2警告
    status = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'api_case'
        ordering = ['-id']


class ApiCaseDetailed(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    case = models.ForeignKey(to=ApiCase, to_field="id", on_delete=models.SET_NULL, null=True)
    api_info = models.ForeignKey(to=ApiInfo, to_field="id", on_delete=models.SET_NULL, null=True)
    case_sort = models.IntegerField(verbose_name="用例排序", null=True)
    header = models.JSONField(verbose_name="请求头", max_length=2048, null=True)
    params = models.JSONField(verbose_name="参数", null=True)
    data = models.TextField(verbose_name="data", null=True)
    json = models.JSONField(verbose_name="json", null=True)
    ass = models.JSONField(verbose_name="公共断言", null=True)

    class Meta:
        db_table = 'api_case_detailed'


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
    status = models.SmallIntegerField(verbose_name="状态", null=True)

    class Meta:
        db_table = 'api_public'
        ordering = ['-id']


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

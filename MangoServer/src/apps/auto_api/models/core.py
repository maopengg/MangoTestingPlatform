from django.db import models, transaction
from mangotools.enums import StatusEnum

from src.apps.auto_api.enums import (
    ApiBodyTypeEnum,
    ApiProtocolTypeEnum,
)
from src.apps.auto_api.exceptions import (
    API_VERSION_API_INFO_STEP_DELETE_NOT_ALLOWED,
    AUTO_API_CORE_CASE_RELATION_DELETE_BINDING_INVALID,
    AUTO_API_CORE_TASK_RELATION_DELETE_BINDING_INVALID,
    AutoApiError,
)
from src.apps.test_center.models import ProjectProduct, ProductModule
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class ApiInfo(models.Model):
    """统一调用定义主表；协议专属配置优先存放在 api_info_*_config 扩展表。"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="api_info_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    name = models.CharField(verbose_name="接口名称", max_length=1024)
    url = models.CharField(verbose_name="请求url", max_length=1024)
    protocol_type = models.CharField(verbose_name="协议类型", max_length=32, default=ApiProtocolTypeEnum.HTTP.value)
    posterior_json_path = models.JSONField(verbose_name="后置jsonpath提取", default=list, blank=True)
    posterior_re = models.JSONField(verbose_name="后置正则提取", default=list, blank=True)
    posterior_func = models.TextField(verbose_name='后置自定义', null=True, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=2, db_index=True)

    class Meta:
        db_table = 'api_info'
        ordering = ['-id']
        indexes = [
            models.Index(
                fields=['project_product', 'module', 'status', '-id'],
                name='idx_api_info_product_module',
            ),
        ]

    def delete(self, *args, **kwargs):
        from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
        impact = ApiCaseRevisionService.inspect_api_info_delete_dependencies(self.id)
        if not impact['can_delete']:
            raise AutoApiError(API_VERSION_API_INFO_STEP_DELETE_NOT_ALLOWED,
                               value=('；'.join(impact['blockers']),),
                               )
        super().delete(*args, **kwargs)


class ApiInfoHttpConfig(models.Model):
    """HTTP/SSE 协议配置当前编辑态。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    api_info = models.OneToOneField(
        to="ApiInfo",
        to_field="id",
        related_name="http_config",
        verbose_name="调用定义",
        on_delete=models.CASCADE,
    )
    method = models.SmallIntegerField(verbose_name="HTTP请求方法")
    url = models.CharField(verbose_name="请求路径", max_length=1024)
    headers = models.JSONField(verbose_name="请求头", null=True, blank=True)
    params = models.TextField(verbose_name="参数", null=True, blank=True)
    is_text_params = models.SmallIntegerField(verbose_name="参数是否文本", default=StatusEnum.SUCCESS.value)
    body_type = models.CharField(verbose_name="请求体类型", max_length=32, default=ApiBodyTypeEnum.NONE.value)
    body_config = models.JSONField(verbose_name="请求体配置", null=True, blank=True)
    sse_config = models.JSONField(verbose_name="SSE配置", null=True, blank=True)

    class Meta:
        db_table = "api_info_http_config"
        ordering = ["-id"]


class ApiInfoWebSocketConfig(models.Model):
    """WebSocket 协议配置当前编辑态。"""

    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    api_info = models.OneToOneField(
        to="ApiInfo",
        to_field="id",
        related_name="websocket_config",
        verbose_name="调用定义",
        on_delete=models.CASCADE,
    )
    url = models.CharField(verbose_name="WebSocket路径", max_length=1024)
    headers = models.JSONField(verbose_name="握手请求头", null=True, blank=True)
    params = models.TextField(verbose_name="握手参数", null=True, blank=True)
    is_text_params = models.SmallIntegerField(verbose_name="参数是否文本", default=StatusEnum.SUCCESS.value)
    body_config = models.JSONField(verbose_name="消息脚本配置", null=True, blank=True)

    class Meta:
        db_table = "api_info_websocket_config"
        ordering = ["-id"]


class ApiCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="api_case_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    name = models.CharField(verbose_name="测试用例名称", max_length=64)
    case_flow = models.TextField(verbose_name="步骤顺序", null=True, blank=True)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.PROTECT)
    parametrize = models.JSONField(verbose_name="参数化", default=list, blank=True)
    level = models.SmallIntegerField(verbose_name="用例级别", default=1)
    scenario_layer = models.SmallIntegerField(verbose_name="测试层级", default=0)
    scenario_type = models.SmallIntegerField(verbose_name="验证类型", default=0)
    scenario_tags = models.JSONField(verbose_name="执行场景", default=list, blank=True)
    scenario_description = models.TextField(verbose_name="场景描述", null=True, blank=True)
    front_custom = models.JSONField(verbose_name="前置方法", default=list, blank=True)
    front_sql = models.JSONField(verbose_name="前置sql", default=list, blank=True)
    front_headers = models.JSONField(verbose_name="前置请求头", default=list, blank=True)
    front_public = models.JSONField(verbose_name="用例选择全局变量", default=list, blank=True)
    front_auth_config = models.JSONField(verbose_name="用例选择授权配置", default=list, blank=True)
    resource_cleanup = models.JSONField(verbose_name='API创建资源清理规则', default=list, blank=True,
                                       help_text='ApiResourceCleanupRule[]；仅test/dev，随Case修订冻结')
    callback_checks = models.JSONField(verbose_name="回调验证规则", default=list, blank=True,
                                      help_text='CallbackRule 列表，包含触发步骤、唯一关联条件、观察窗口和检查项')
    posterior_sql = models.JSONField(verbose_name="后置sql", default=list, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=2, db_index=True)

    class Meta:
        db_table = 'api_case'
        ordering = ['-id']
        indexes = [
            models.Index(
                fields=['project_product', 'module', 'status', '-id'],
                name='idx_api_case_product_module',
            ),
        ]

    def delete(self, *args, **kwargs):
        if ApiCaseDetailed.objects.filter(case=self).exists():
            raise AutoApiError(AUTO_API_CORE_CASE_RELATION_DELETE_BINDING_INVALID)
        from src.apps.task_center.models import TasksDetails
        if TasksDetails.objects.filter(api_case=self).exists():
            raise AutoApiError(AUTO_API_CORE_TASK_RELATION_DELETE_BINDING_INVALID)
        from src.apps.data_factory.models import DataFactoryCaseConfig
        from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
        from src.apps.auto_api.services.api_case.version import ApiCaseRevisionService
        with transaction.atomic():
            DataFactoryCaseConfig.objects.filter(
                source_type=DataFactoryCaseSourceTypeEnum.API_CASE.value,
                source_id=self.id,
            ).delete()
            ApiCaseRevisionService.detach_report_references_for_case(self.id)
            super().delete(*args, **kwargs)


class ApiCaseDetailed(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    case = models.ForeignKey(to="ApiCase", to_field="id", on_delete=models.PROTECT)
    api_info = models.ForeignKey(to="ApiInfo", to_field="id", on_delete=models.PROTECT)
    pinned_api_info_revision = models.ForeignKey(
        to='ApiInfoRevision',
        to_field='id',
        related_name='pinned_case_steps',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name='固定接口修订',
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="api_case_detailed_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    case_sort = models.IntegerField(verbose_name="用例排序", null=True, blank=True)
    execution_config = models.JSONField(verbose_name='步骤执行配置', default=dict, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=2, db_index=True)
    error_message = models.TextField(verbose_name="失败提示", null=True, blank=True)

    class Meta:
        db_table = 'api_case_detailed'

    def delete(self, *args, **kwargs):
        if ApiCaseDetailedParameter.objects.filter(case_detailed=self).exists():
            for parameter in ApiCaseDetailedParameter.objects.filter(case_detailed=self):
                parameter.delete()
        super().delete(*args, **kwargs)


class ApiCaseDetailedParameter(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    case_detailed = models.ForeignKey(to="ApiCaseDetailed", to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="api_case_detailed_parameter_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    error_retry = models.SmallIntegerField(verbose_name="失败重试", null=True, blank=True)
    retry_interval = models.SmallIntegerField(verbose_name="重试间隔", null=True, blank=True)
    allow_failure = models.BooleanField(verbose_name="允许失败", default=False)
    name = models.CharField(verbose_name="步骤名称", max_length=128)
    headers = models.JSONField(verbose_name="请求头", default=list, blank=True)
    params = models.TextField(verbose_name="参数", null=True, blank=True)
    body_config = models.JSONField(verbose_name="请求体配置", null=True, blank=True)
    # Deprecated: SSE 场景停止条件后续会并入 body_config，稳定后删除该字段。
    sse_config = models.JSONField(verbose_name="SSE配置", null=True, blank=True)

    # 前置
    front_sql = models.JSONField(verbose_name="前置sql", default=list, blank=True)
    front_func = models.TextField(verbose_name='前置自定义函数', null=True, blank=True)
    # 断言
    ass_general = models.JSONField(verbose_name="通用断言", default=list, blank=True)
    ass_sql = models.JSONField(verbose_name="sql断言", default=list, blank=True)
    ass_json_all = models.JSONField(verbose_name="响应JSON全匹配断言", null=True, blank=True)
    ass_text_all = models.TextField(verbose_name="响应文本全匹配断言", null=True, blank=True)
    ass_jsonpath = models.JSONField(verbose_name="响应jsonpath断言", default=list, blank=True)
    ass_schema = models.JSONField(verbose_name="schema配置", null=True, blank=True)
    # 后置
    posterior_sql = models.JSONField(verbose_name="后置sql", default=list, blank=True)
    posterior_response = models.JSONField(verbose_name="后置响应处理", default=list, blank=True)
    posterior_response_text = models.JSONField(verbose_name="后置响应文本处理", default=list, blank=True)
    posterior_sleep = models.SmallIntegerField(verbose_name="强制等待", null=True, blank=True)
    posterior_file = models.JSONField(verbose_name="文件下载", default=dict, blank=True)
    posterior_func = models.TextField(verbose_name='后置自定义', null=True, blank=True)
    status = models.SmallIntegerField(verbose_name="状态", default=2, db_index=True)

    class Meta:
        db_table = 'api_case_detailed_parameter'

    def delete(self, *args, **kwargs):
        from src.apps.data_factory.models import DataFactoryCaseConfig
        from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
        DataFactoryCaseConfig.objects.filter(
            source_type=DataFactoryCaseSourceTypeEnum.API_CASE_PARAMETER.value,
            source_id=self.id,
        ).delete()
        super().delete(*args, **kwargs)

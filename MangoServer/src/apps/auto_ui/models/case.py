from django.db import models
from src.apps.auto_ui.enums.case import UiCasePublicationStatusEnum

from src.apps.auto_ui.exceptions import (
    AUTO_UI_CASE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID,
    AUTO_UI_CASE_TASK_RELATION_DELETE_BINDING_INVALID,
    AutoUiError,
)
from src.apps.test_center.models import ProjectProduct, ProductModule
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class UiCase(models.Model):
    """用例表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="ui_case_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="用例组名称", max_length=64)
    case_flow = models.TextField(verbose_name="步骤顺序", null=True, blank=True)
    case_people = models.ForeignKey(to=User, to_field="id", verbose_name='用例责任人', on_delete=models.PROTECT)
    parametrize = models.JSONField(verbose_name="参数化", default=list, blank=True)
    scenario_layer = models.SmallIntegerField(verbose_name="测试层级", default=0)
    scenario_type = models.SmallIntegerField(verbose_name="验证类型", default=0)
    scenario_tags = models.JSONField(verbose_name="执行场景", default=list, blank=True)
    scenario_description = models.TextField(verbose_name="场景描述", null=True, blank=True)
    # 0失败，1成功，2待开始，3，进行中
    status = models.SmallIntegerField(verbose_name="状态", default=2, db_index=True)
    publication_status = models.CharField(
        verbose_name="发布状态", max_length=32, choices=UiCasePublicationStatusEnum.choices(),
        default=UiCasePublicationStatusEnum.UNPUBLISHED.value,
        help_text="用例发布审批状态；仅已发布用例可参与定时执行。",
    )
    level = models.SmallIntegerField(verbose_name="用例级别", default=0, db_index=True)
    front_custom = models.JSONField(verbose_name="前置自定义", default=list, blank=True)
    front_sql = models.JSONField(verbose_name="前置sql", default=list, blank=True)
    front_public = models.JSONField(verbose_name="用例选择全局变量", default=list, blank=True)
    front_auth_config = models.JSONField(verbose_name="用例选择授权配置", default=list, blank=True)
    posterior_sql = models.JSONField(verbose_name="后置sql", default=list, blank=True)

    class Meta:
        db_table = 'ui_case'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['project_product', 'publication_status', '-id'], name='idx_ui_case_product_release'),
            models.Index(
                fields=['project_product', 'module', 'status', '-id'],
                name='idx_ui_case_product_module',
            ),
        ]

    def delete(self, *args, **kwargs):
        if UiCaseStepsDetailed.objects.filter(case=self).exists():
            raise AutoUiError(AUTO_UI_CASE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID)
        from src.apps.task_center.models import TasksDetails
        if TasksDetails.objects.filter(ui_case=self).exists():
            raise AutoUiError(AUTO_UI_CASE_TASK_RELATION_DELETE_BINDING_INVALID)
        from src.apps.data_factory.models import DataFactoryCaseConfig
        from src.apps.data_factory.enums import DataFactoryCaseSourceTypeEnum
        DataFactoryCaseConfig.objects.filter(
            source_type=DataFactoryCaseSourceTypeEnum.UI_CASE.value,
            source_id=self.id,
        ).delete()
        super().delete(*args, **kwargs)


class UiCaseStepsDetailed(models.Model):
    """用例详情表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    case = models.ForeignKey(to="UiCase", to_field="id", on_delete=models.PROTECT)
    page_step = models.ForeignKey(to="PageSteps", to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="ui_case_steps_detailed_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    case_sort = models.SmallIntegerField(verbose_name="用例排序")
    case_data = models.JSONField(verbose_name="用例步骤数据", null=True, blank=True)
    switch_step_open_url = models.SmallIntegerField(verbose_name="是否在执行页面的时候切换url", default=0)
    error_retry = models.SmallIntegerField(verbose_name="失败重试", null=True, blank=True)
    # 0失败，1成功
    status = models.SmallIntegerField(verbose_name="状态", default=2)
    error_message = models.TextField(verbose_name="错误提示", null=True, blank=True)

    class Meta:
        db_table = 'ui_case_steps_detailed'

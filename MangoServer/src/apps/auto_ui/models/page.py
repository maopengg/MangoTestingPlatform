from django.db import models

from src.apps.auto_ui.exceptions import (
    AUTO_UI_PAGE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID,
    AUTO_UI_PAGE_ELEMENT_RELATION_DELETE_BINDING_INVALID,
    AUTO_UI_PAGE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID_CODE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID,
    AutoUiError,
)
from src.apps.test_center.models import ProjectProduct, ProductModule
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""

from django.apps import apps


class Page(models.Model):
    """页面表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="page_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="页面名称", max_length=64)
    url = models.CharField(verbose_name="url", max_length=1048)

    class Meta:
        db_table = 'page'
        ordering = ['-id']
        indexes = [
            models.Index(
                fields=['project_product', 'module', '-id'],
                name='idx_page_product_module',
            ),
        ]

    def delete(self, *args, **kwargs):
        if apps.get_model("auto_ui", "PageSteps").objects.filter(page=self).exists():
            raise AutoUiError(AUTO_UI_PAGE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID)
        if PageElement.objects.filter(page=self).exists():
            raise AutoUiError(AUTO_UI_PAGE_ELEMENT_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)


class PageElement(models.Model):
    """页面元素表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    page = models.ForeignKey(to="Page", to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="page_element_update_user",
                                    on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(verbose_name="元素名称", max_length=64)
    category = models.CharField(verbose_name="元素分类", max_length=64, default="未分类", db_index=True)
    exp = models.SmallIntegerField(verbose_name="元素表达式", null=True, blank=True)
    loc = models.TextField(verbose_name="元素定位", null=True, blank=True)
    exp2 = models.SmallIntegerField(verbose_name="元素表达式", null=True, blank=True)
    loc2 = models.TextField(verbose_name="元素定位", null=True, blank=True)
    exp3 = models.SmallIntegerField(verbose_name="元素表达式", null=True, blank=True)
    loc3 = models.TextField(verbose_name="元素定位", null=True, blank=True)
    sleep = models.SmallIntegerField(verbose_name="等待时间", null=True, blank=True)
    sub = models.SmallIntegerField(verbose_name="下标", null=True, blank=True)
    sub2 = models.SmallIntegerField(verbose_name="下标2", null=True, blank=True)
    sub3 = models.SmallIntegerField(verbose_name="下标3", null=True, blank=True)
    is_iframe = models.SmallIntegerField(verbose_name="是否在iframe里面", null=True, blank=True)
    prompt = models.TextField(verbose_name="AI元素定位提示词", null=True, blank=True)
    location_description = models.TextField(verbose_name="元素位置描述", null=True, blank=True)
    surrounding_text = models.TextField(verbose_name="周边文字与排除项", null=True, blank=True)
    ai_heal_status = models.SmallIntegerField(verbose_name="AI自愈状态", default=0)
    ai_last_heal_time = models.DateTimeField(verbose_name="最近AI自愈时间", null=True, blank=True)
    ai_last_snapshot_time = models.DateTimeField(verbose_name="最近基线采集时间", null=True, blank=True)
    ai_stable_pass_count = models.IntegerField(verbose_name="稳定通过次数", default=0)
    latest_match_count = models.IntegerField(verbose_name="最近元素匹配数量", null=True, blank=True)
    latest_element_text = models.TextField(verbose_name="最近元素文本", null=True, blank=True)
    latest_runtime_time = models.DateTimeField(verbose_name="最近运行信息时间", null=True, blank=True)
    latest_runtime_snapshot = models.JSONField(verbose_name="最近运行信息快照", default=dict, blank=True)
    expected_event = models.JSONField(verbose_name="预期事件", default=dict, blank=True)
    locator_version = models.PositiveBigIntegerField(verbose_name="定位配置版本", default=1)
    frame_path = models.JSONField(verbose_name="Frame路径", default=dict, blank=True)

    class Meta:
        db_table = 'page_element'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['page', 'category', 'id']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['page', 'name', 'category'],
                name='page_element_identity_unique',
            ),
            models.CheckConstraint(
                condition=(models.Q(exp__isnull=True, loc__isnull=True)
                           | models.Q(exp__isnull=False, loc__isnull=False)),
                name='page_element_locator_1_pair',
            ),
            models.CheckConstraint(
                condition=(models.Q(exp2__isnull=True, loc2__isnull=True)
                           | models.Q(exp2__isnull=False, loc2__isnull=False)),
                name='page_element_locator_2_pair',
            ),
            models.CheckConstraint(
                condition=(models.Q(exp3__isnull=True, loc3__isnull=True)
                           | models.Q(exp3__isnull=False, loc3__isnull=False)),
                name='page_element_locator_3_pair',
            ),
        ]

    def delete(self, *args, **kwargs):
        if apps.get_model("auto_ui", "PageStepsDetailed").objects.filter(ele_name=self).exists():
            raise AutoUiError(
                AUTO_UI_PAGE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID_CODE_STEP_PAGE_RELATION_DELETE_BINDING_INVALID)
        super().delete(*args, **kwargs)


class UiElementSnapshot(models.Model):
    """UI元素定位基线快照"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    element = models.ForeignKey(to="PageElement", to_field="id", on_delete=models.CASCADE)
    page = models.ForeignKey(to="Page", to_field="id", on_delete=models.PROTECT)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    source = models.SmallIntegerField(verbose_name="采集来源", default=0)
    status = models.SmallIntegerField(verbose_name="状态", default=1)
    url = models.TextField(verbose_name="采集时URL")
    title = models.CharField(verbose_name="页面标题", max_length=512, null=True, blank=True)
    frame_url = models.TextField(verbose_name="iframe URL", null=True, blank=True)
    exp = models.SmallIntegerField(verbose_name="成功表达式类型")
    loc = models.TextField(verbose_name="成功定位表达式")
    sub = models.SmallIntegerField(verbose_name="成功下标", null=True, blank=True)
    match_count = models.IntegerField(verbose_name="匹配数量", default=0)
    element_text = models.TextField(verbose_name="元素文本", null=True, blank=True)
    element_tag = models.CharField(verbose_name="标签名", max_length=64, null=True, blank=True)
    element_role = models.CharField(verbose_name="role", max_length=128, null=True, blank=True)
    element_type = models.CharField(verbose_name="type", max_length=128, null=True, blank=True)
    element_name = models.CharField(verbose_name="可访问名称", max_length=512, null=True, blank=True)
    element_placeholder = models.CharField(verbose_name="placeholder", max_length=512, null=True, blank=True)
    element_value = models.TextField(verbose_name="value", null=True, blank=True)
    element_attributes = models.JSONField(verbose_name="关键属性", default=dict, blank=True)
    element_rect = models.JSONField(verbose_name="元素位置尺寸", default=dict, blank=True)
    element_css = models.JSONField(verbose_name="关键样式", default=dict, blank=True)
    outer_html = models.TextField(verbose_name="元素HTML", null=True, blank=True)
    parent_html = models.TextField(verbose_name="父级HTML", null=True, blank=True)
    nearby_html = models.TextField(verbose_name="邻近HTML", null=True, blank=True)
    page_dom_digest = models.JSONField(verbose_name="页面DOM摘要", default=dict, blank=True)
    accessibility_digest = models.JSONField(verbose_name="可访问性语义摘要", default=dict, blank=True)
    screenshot_path = models.TextField(verbose_name="元素截图", null=True, blank=True)
    html_hash = models.CharField(verbose_name="HTML指纹", max_length=64, db_index=True)
    locator_hash = models.CharField(verbose_name="定位器指纹", max_length=64, db_index=True)
    schema_version = models.PositiveSmallIntegerField(verbose_name="数据协议版本", default=2)
    frame_path = models.JSONField(verbose_name="Frame路径", default=dict, blank=True)
    executor_task = models.ForeignKey(
        to='task_center.ExecutorTask', to_field='id', on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    trace_id = models.UUIDField(verbose_name="链路ID", null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'ui_element_snapshot'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['element', 'test_env', 'status']),
            models.Index(fields=['project_product', 'page']),
            models.Index(fields=['status', 'create_time']),
        ]


class UiElementHealRecord(models.Model):
    """UI元素AI自愈修复记录"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    element = models.ForeignKey(to="PageElement", to_field="id", on_delete=models.CASCADE)
    page = models.ForeignKey(to="Page", to_field="id", on_delete=models.PROTECT)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    snapshot = models.ForeignKey(to="UiElementSnapshot", to_field="id", on_delete=models.SET_NULL, null=True,
                                 blank=True)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    source = models.SmallIntegerField(verbose_name="触发来源", default=0)
    status = models.SmallIntegerField(verbose_name="修复状态", default=0)
    failed_exp = models.SmallIntegerField(verbose_name="失败表达式类型", null=True, blank=True)
    failed_loc = models.TextField(verbose_name="失败定位表达式", null=True, blank=True)
    failed_sub = models.SmallIntegerField(verbose_name="失败下标", null=True, blank=True)
    failed_reason = models.TextField(verbose_name="失败原因", null=True, blank=True)
    page_url = models.TextField(verbose_name="失败时URL")
    current_context = models.JSONField(verbose_name="当前页面上下文摘要", default=dict, blank=True)
    ai_prompt_summary = models.JSONField(verbose_name="AI输入摘要", default=dict, blank=True)
    ai_response = models.JSONField(verbose_name="AI原始响应", default=dict, blank=True)
    candidates = models.JSONField(verbose_name="候选定位器", default=dict, blank=True)
    selected_exp = models.SmallIntegerField(verbose_name="采用表达式类型", null=True, blank=True)
    selected_loc = models.TextField(verbose_name="采用定位表达式", null=True, blank=True)
    selected_sub = models.SmallIntegerField(verbose_name="采用下标", null=True, blank=True)
    confidence = models.FloatField(verbose_name="置信度", default=0)
    applied = models.BooleanField(verbose_name="是否已写回", default=False)
    applied_by = models.ForeignKey(to=User, to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    applied_time = models.DateTimeField(verbose_name="写回时间", null=True, blank=True)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    executor_task = models.ForeignKey(
        to='task_center.ExecutorTask', to_field='id', on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    trace_id = models.UUIDField(verbose_name="链路ID", null=True, blank=True, db_index=True)
    base_locator_version = models.PositiveBigIntegerField(
        verbose_name="定位前版本", null=True, blank=True,
    )
    applied_locator_version = models.PositiveBigIntegerField(
        verbose_name="写回后版本", null=True, blank=True,
    )
    result_screenshot_path = models.TextField(verbose_name="结果截图", null=True, blank=True)

    class Meta:
        db_table = 'ui_element_heal_record'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['element', 'test_env', 'status']),
            models.Index(fields=['project_product', 'page']),
            models.Index(fields=['applied']),
            models.Index(fields=['status', 'create_time']),
        ]

# -*- coding: utf-8 -*-
from django.db import models

from src.apps.auto_api.models import ApiCase
from src.apps.system.models import FileData, ProductModule, ProjectProduct
from src.apps.auto_ui.models import UiCase
from src.apps.user.models import User
from src.common.enums.manual_test_enum import (
    FunctionalTestContextContentTypeEnum,
    FunctionalTestContextKeyEnum,
    FunctionalTestContextParseStatusEnum,
    FunctionalTestContextUrlTypeEnum,
    ManualTestAutomationImpactStatusEnum,
    ManualTestAutomationTypeEnum,
    ManualTestChangeStatusEnum,
    ManualTestOptimizeStatusEnum,
    ManualTestRelationTypeEnum,
    ManualTestSyncStatusEnum,
)
from src.common.enums.tools_enum import CaseLevelEnum, TaskEnum


class ManualTestSuite(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", null=True, blank=True, on_delete=models.PROTECT)
    iteration = models.CharField(verbose_name="所属迭代", max_length=128, null=True, blank=True)
    requirement_name = models.CharField(verbose_name="需求名称", max_length=256, null=True, blank=True)
    owner = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="manual_test_suite_owner",
        on_delete=models.PROTECT,
    )
    last_sync_time = models.DateTimeField(verbose_name="最近同步时间", null=True, blank=True)
    sync_status = models.SmallIntegerField(
        verbose_name="同步状态",
        choices=ManualTestSyncStatusEnum.choices(),
        default=ManualTestSyncStatusEnum.NOT_SYNCED.value,
        db_index=True,
    )
    case_count = models.IntegerField(verbose_name="case数量", default=0)
    automated_case_count = models.IntegerField(verbose_name="自动化覆盖数", default=0)
    automation_coverage_percent = models.DecimalField(verbose_name="自动化完成百分比", max_digits=5, decimal_places=2, default=0)
    need_optimize_count = models.IntegerField(verbose_name="待优化数量", default=0)
    status = models.SmallIntegerField(verbose_name="状态", default=1, db_index=True)
    class Meta:
        db_table = "manual_test_suite"
        ordering = ["-id"]


class ManualTestCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    suite = models.ForeignKey(to=ManualTestSuite, to_field="id", on_delete=models.CASCADE)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    case_no = models.CharField(verbose_name="用例编号", max_length=128)
    title = models.CharField(verbose_name="用例标题", max_length=256)
    priority = models.SmallIntegerField(verbose_name="优先级", choices=CaseLevelEnum.choices(), default=CaseLevelEnum.P1.value)
    test_types = models.JSONField(verbose_name="测试类型", default=list)
    story_refs = models.JSONField(verbose_name="关联用户故事", default=list)
    precondition = models.TextField(verbose_name="前置条件", null=True, blank=True)
    test_point = models.TextField(verbose_name="测试点")
    acceptance_source = models.TextField(verbose_name="验收标准来源", null=True, blank=True)
    test_result = models.SmallIntegerField(verbose_name="测试结果", choices=TaskEnum.choices(), default=TaskEnum.STAY_BEGIN.value)
    owner = models.ForeignKey(to=User, to_field="id", on_delete=models.PROTECT)
    automation_status = models.CharField(verbose_name="自动化状态", max_length=32, default="not_automated")
    change_status = models.SmallIntegerField(
        verbose_name="变更状态",
        choices=ManualTestChangeStatusEnum.choices(),
        default=ManualTestChangeStatusEnum.UNCHANGED.value,
        db_index=True,
    )
    automation_impact_status = models.SmallIntegerField(
        verbose_name="自动化影响状态",
        choices=ManualTestAutomationImpactStatusEnum.choices(),
        default=ManualTestAutomationImpactStatusEnum.NONE.value,
        db_index=True,
    )
    scenario_layer = models.SmallIntegerField(verbose_name="场景层级", default=0)
    scenario_type = models.SmallIntegerField(verbose_name="场景类型", default=0)
    scenario_tags = models.JSONField(verbose_name="场景标签", default=list)
    test_data = models.TextField(verbose_name="测试数据", null=True, blank=True)
    remark = models.TextField(verbose_name="备注", null=True, blank=True)
    source_block_id = models.CharField(verbose_name="来源块ID", max_length=128, null=True, blank=True)
    source_text = models.TextField(verbose_name="来源原文", null=True, blank=True)
    source_hash = models.CharField(verbose_name="来源Hash", max_length=64, null=True, blank=True)
    class Meta:
        db_table = "manual_test_case"
        ordering = ["suite_id", "id"]


class ManualTestAutomationBinding(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    manual_case = models.ForeignKey(to=ManualTestCase, to_field="id", on_delete=models.CASCADE)
    automation_type = models.SmallIntegerField(
        verbose_name="自动化类型",
        choices=ManualTestAutomationTypeEnum.choices(),
        db_index=True,
    )
    automation_case_id = models.IntegerField(verbose_name="自动化CaseID")
    api_case = models.ForeignKey(to=ApiCase, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    ui_case = models.ForeignKey(to=UiCase, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    automation_case_name = models.CharField(verbose_name="自动化Case名称", max_length=256, null=True, blank=True)
    relation_type = models.SmallIntegerField(
        verbose_name="关系类型",
        choices=ManualTestRelationTypeEnum.choices(),
        default=ManualTestRelationTypeEnum.BOUND.value,
    )
    optimize_status = models.SmallIntegerField(
        verbose_name="优化状态",
        choices=ManualTestOptimizeStatusEnum.choices(),
        default=ManualTestOptimizeStatusEnum.NORMAL.value,
    )
    optimize_reason = models.TextField(verbose_name="优化原因", null=True, blank=True)

    class Meta:
        db_table = "manual_test_case_automation_binding"
        ordering = ["-id"]


class FunctionalTestContextResource(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    suite = models.ForeignKey(to=ManualTestSuite, to_field="id", on_delete=models.CASCADE)
    context_key = models.SmallIntegerField(
        verbose_name="上下文分组",
        choices=FunctionalTestContextKeyEnum.choices(),
        db_index=True,
    )
    content_type = models.SmallIntegerField(
        verbose_name="资料类型",
        choices=FunctionalTestContextContentTypeEnum.choices(),
        default=FunctionalTestContextContentTypeEnum.TEXT.value,
        db_index=True,
    )
    url_type = models.SmallIntegerField(
        verbose_name="URL类型",
        choices=FunctionalTestContextUrlTypeEnum.choices(),
        default=FunctionalTestContextUrlTypeEnum.NORMAL.value,
    )
    title = models.CharField(verbose_name="资料标题", max_length=256)
    content = models.TextField(verbose_name="文本或URL内容", null=True, blank=True)
    file = models.ForeignKey(to=FileData, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    file_path = models.CharField(verbose_name="文件路径", max_length=1024, null=True, blank=True)
    file_name = models.CharField(verbose_name="文件名称", max_length=255, null=True, blank=True)
    mime_type = models.CharField(verbose_name="MIME类型", max_length=128, null=True, blank=True)
    file_size = models.IntegerField(verbose_name="文件大小", null=True, blank=True)
    extracted_text = models.TextField(verbose_name="解析文本", null=True, blank=True)
    enabled = models.BooleanField(verbose_name="是否启用", default=True)
    parse_status = models.SmallIntegerField(
        verbose_name="解析状态",
        choices=FunctionalTestContextParseStatusEnum.choices(),
        default=FunctionalTestContextParseStatusEnum.NOT_PARSED.value,
    )
    parse_error = models.TextField(verbose_name="解析失败原因", null=True, blank=True)
    create_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_test_context_resource_create_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_test_context_resource_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "functional_test_context_resource"
        ordering = ["suite_id", "context_key", "id"]
        indexes = [
            models.Index(fields=["suite", "context_key", "enabled"]),
        ]

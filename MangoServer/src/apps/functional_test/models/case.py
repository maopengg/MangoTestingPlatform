# -*- coding: utf-8 -*-
from django.db import models

from src.apps.auto_api.models import ApiCase
from src.apps.auto_ui.models import UiCase
from src.apps.functional_test.enums import (
    ManualTestAutomationImpactStatusEnum,
    ManualTestAutomationTypeEnum,
    ManualTestChangeStatusEnum,
    ManualTestCaseVersionSourceEnum,
    FunctionalCaseStatusEnum,
    ManualTestOptimizeStatusEnum,
    ManualTestRelationTypeEnum,
)
from src.apps.test_center.enums import CaseLevelEnum
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.user.models import User


class ManualTestCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    suite = models.ForeignKey(
        to="ManualTestSuite",
        to_field="id",
        related_name="legacy_cases",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="旧需求版本来源，仅用于兼容和数据追溯",
    )
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", on_delete=models.PROTECT)
    case_no = models.CharField(verbose_name="用例编号", max_length=128)
    title = models.CharField(verbose_name="用例标题", max_length=256)
    category_level_1 = models.CharField(verbose_name="分类一", max_length=128, null=True, blank=True, db_index=True)
    category_level_2 = models.CharField(verbose_name="分类二", max_length=128, null=True, blank=True, db_index=True)
    category_level_3 = models.CharField(verbose_name="分类三", max_length=128, null=True, blank=True, db_index=True)
    priority = models.SmallIntegerField(verbose_name="优先级", choices=CaseLevelEnum.choices(),
                                        default=CaseLevelEnum.P1.value)
    test_types = models.JSONField(verbose_name="测试类型", default=list, blank=True)
    story_refs = models.JSONField(verbose_name="关联用户故事", default=list, blank=True)
    precondition = models.TextField(verbose_name="前置条件", null=True, blank=True)
    test_point = models.TextField(verbose_name="测试点")
    test_steps = models.JSONField(verbose_name="测试步骤", default=list, blank=True)
    expected_result = models.TextField(verbose_name="预期结果", null=True, blank=True)
    acceptance_source = models.TextField(verbose_name="验收标准来源", null=True, blank=True)
    status = models.SmallIntegerField(
        verbose_name="资产状态",
        choices=FunctionalCaseStatusEnum.choices(),
        default=FunctionalCaseStatusEnum.ENABLED.value,
        db_index=True,
    )
    version_no = models.PositiveIntegerField(verbose_name="资产版本", default=1)
    owner = models.ForeignKey(to=User, to_field="id", on_delete=models.PROTECT)
    update_user = models.ForeignKey(to=User, to_field="id", related_name="manual_test_case_update_user",
                                    null=True, blank=True, on_delete=models.SET_NULL)
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
    scenario_layer = models.SmallIntegerField(verbose_name="测试层级", default=0)
    scenario_type = models.SmallIntegerField(verbose_name="验证类型", default=0)
    scenario_tags = models.JSONField(verbose_name="执行场景", default=list, blank=True)
    test_data = models.TextField(verbose_name="测试数据", null=True, blank=True)
    remark = models.TextField(verbose_name="备注", null=True, blank=True)
    source_block_id = models.CharField(verbose_name="来源块ID", max_length=128, null=True, blank=True)
    source_text = models.TextField(verbose_name="来源原文", null=True, blank=True)
    source_hash = models.CharField(verbose_name="来源Hash", max_length=64, null=True, blank=True)

    class Meta:
        db_table = "manual_test_case"
        ordering = ["project_product_id", "module_id", "id"]
        indexes = [
            models.Index(fields=["project_product", "module", "status"]),
            models.Index(fields=["project_product", "case_no"]),
        ]


class ManualTestCaseVersion(models.Model):
    case = models.ForeignKey(
        to="ManualTestCase",
        to_field="id",
        related_name="versions",
        on_delete=models.CASCADE,
    )
    version_no = models.PositiveIntegerField(verbose_name="版本号")
    snapshot = models.JSONField(verbose_name="用例快照", default=dict, blank=True)
    source = models.SmallIntegerField(
        verbose_name="版本来源",
        choices=ManualTestCaseVersionSourceEnum.choices(),
        default=ManualTestCaseVersionSourceEnum.LIBRARY.value,
    )
    changed_by = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="manual_test_case_versions",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)

    class Meta:
        db_table = "manual_test_case_version"
        ordering = ["-version_no", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "version_no"],
                name="manual_test_case_version_unique",
            )
        ]


class ManualTestAutomationBinding(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    manual_case = models.ForeignKey(to="ManualTestCase", to_field="id", on_delete=models.CASCADE)
    automation_type = models.SmallIntegerField(
        verbose_name="自动化类型",
        choices=ManualTestAutomationTypeEnum.choices(),
        db_index=True,
    )
    automation_case_id = models.IntegerField(verbose_name="自动化CaseID")
    api_case = models.ForeignKey(to=ApiCase, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    ui_case = models.ForeignKey(to=UiCase, to_field="id", null=True, blank=True, on_delete=models.SET_NULL)
    automation_case_name = models.CharField(verbose_name="自动化Case名称", max_length=256, null=True, blank=True)
    update_user = models.ForeignKey(to=User, to_field="id",
                                    related_name="manual_test_case_automation_binding_update_user",
                                    null=True, blank=True, on_delete=models.SET_NULL)
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

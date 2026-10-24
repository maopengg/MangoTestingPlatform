# -*- coding: utf-8 -*-
import uuid

from django.db import models
from django.db.models import Q

from src.apps.functional_test.enums import (
    FunctionalTestIterationStatusEnum,
    FunctionalTestRequirementCategoryEnum,
    FunctionalTestRequirementIssueTypeEnum,
    FunctionalTestRequirementStatusEnum,
    ManualTestSuiteStatusEnum,
    ManualTestSyncStatusEnum,
)
from src.apps.test_center.enums import CaseLevelEnum
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.user.models import Department, User


def generate_requirement_key():
    return f"REQ-{uuid.uuid4().hex[:16].upper()}"


class FunctionalTestIteration(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    iteration_no = models.CharField(verbose_name="Sprint编号", max_length=64)
    name = models.CharField(verbose_name="Sprint名称", max_length=128)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    owner = models.ForeignKey(
        to=User, to_field="id", related_name="functional_test_iteration_owner", on_delete=models.PROTECT,
    )
    start_date = models.DateField(verbose_name="开始日期")
    end_date = models.DateField(verbose_name="结束日期")
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=FunctionalTestIterationStatusEnum.choices(),
        default=FunctionalTestIterationStatusEnum.NOT_STARTED.value,
        db_index=True,
    )
    remark = models.TextField(verbose_name="备注", null=True, blank=True)
    update_user = models.ForeignKey(
        to=User, to_field="id", related_name="functional_test_iteration_update_user",
        null=True, blank=True, on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "functional_test_iteration"
        ordering = ["-start_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["project_product", "iteration_no"],
                name="functional_test_iteration_product_no_unique",
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="functional_test_iteration_date_order",
            ),
        ]


class FunctionalTestRequirement(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    requirement_key = models.CharField(
        verbose_name="需求标识",
        max_length=32,
        unique=True,
        default=generate_requirement_key,
    )
    name = models.CharField(verbose_name="需求名称", max_length=256)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    owner = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_test_requirement_owner",
        on_delete=models.PROTECT,
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_test_requirement_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    status = models.SmallIntegerField(
        verbose_name="状态",
        choices=FunctionalTestRequirementStatusEnum.choices(),
        default=FunctionalTestRequirementStatusEnum.ACTIVE.value,
        db_index=True,
    )
    issue_type = models.SmallIntegerField(
        verbose_name="问题类型",
        choices=FunctionalTestRequirementIssueTypeEnum.choices(),
        default=FunctionalTestRequirementIssueTypeEnum.USER_STORY.value,
        db_index=True,
    )
    requirement_category = models.SmallIntegerField(
        verbose_name="需求分类",
        choices=FunctionalTestRequirementCategoryEnum.choices(),
        default=FunctionalTestRequirementCategoryEnum.PRODUCT_ITERATION.value,
        db_index=True,
    )

    class Meta:
        db_table = "functional_test_requirement"
        ordering = ["-id"]


class ManualTestSuite(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    requirement = models.ForeignKey(
        to="FunctionalTestRequirement",
        to_field="id",
        related_name="versions",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    version_no = models.PositiveIntegerField(verbose_name="需求版本号", null=True, blank=True)
    previous_version = models.ForeignKey(
        to="self",
        to_field="id",
        related_name="next_versions",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to=ProductModule, to_field="id", null=True, blank=True, on_delete=models.PROTECT)
    iteration = models.CharField(verbose_name="所属迭代", max_length=128, null=True, blank=True)
    iteration_ref = models.ForeignKey(
        to="FunctionalTestIteration",
        to_field="id",
        related_name="requirement_versions",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    delivery_team = models.ForeignKey(
        to=Department,
        to_field="id",
        related_name="functional_test_requirement_versions",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    sort_order = models.PositiveIntegerField(verbose_name="看板顺序", default=0, db_index=True)
    priority = models.SmallIntegerField(
        verbose_name="优先级", choices=CaseLevelEnum.choices(), default=CaseLevelEnum.P1.value,
    )
    development_owner = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="manual_test_suite_development_owner",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    planned_start_date = models.DateField(verbose_name="计划开始日期", null=True, blank=True)
    planned_submit_date = models.DateField(verbose_name="计划提测日期", null=True, blank=True)
    actual_submit_at = models.DateTimeField(verbose_name="实际提测时间", null=True, blank=True)
    requirement_name = models.CharField(verbose_name="需求名称", max_length=256, null=True, blank=True)
    description = models.TextField(verbose_name="需求描述", null=True, blank=True)
    test_required = models.BooleanField(verbose_name="需要测试", default=True)
    automation_recommended = models.BooleanField(verbose_name="建议自动化", default=False)
    effect_test_required = models.BooleanField(verbose_name="效果测试", default=False)
    planned_release_date = models.DateField(verbose_name="计划上线日期", null=True, blank=True)
    customer_deadline_date = models.DateField(verbose_name="客户要求上线日期", null=True, blank=True)
    committed_release_date = models.DateField(verbose_name="承诺上线日期", null=True, blank=True)
    actual_release_at = models.DateTimeField(verbose_name="实际上线时间", null=True, blank=True)
    customer_ref = models.CharField(verbose_name="关联客户", max_length=128, null=True, blank=True)
    owner = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="manual_test_suite_owner",
        on_delete=models.PROTECT,
    )
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="manual_test_suite_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
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
    automation_coverage_percent = models.DecimalField(verbose_name="自动化完成百分比", max_digits=5, decimal_places=2,
                                                      default=0)
    need_optimize_count = models.IntegerField(verbose_name="待优化数量", default=0)
    status = models.SmallIntegerField(
        verbose_name="交付状态",
        choices=ManualTestSuiteStatusEnum.choices(),
        default=ManualTestSuiteStatusEnum.UNSCHEDULED.value,
        db_index=True,
    )

    class Meta:
        db_table = "manual_test_suite"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["requirement", "version_no"],
                name="manual_test_suite_requirement_version_unique",
            )
        ]

# -*- coding: utf-8 -*-
import uuid

from django.db import models
from django.db.models import Q

from src.apps.functional_test.enums import (
    FunctionalTestDefectPriorityEnum,
    FunctionalTestDefectResolutionEnum,
    FunctionalTestDefectSeverityEnum,
    FunctionalTestDefectSourceEnum,
    FunctionalTestDefectStatusEnum,
    FunctionalTestDefectTypeEnum,
)
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.user.models import User


def generate_defect_no():
    return f"BUG-{uuid.uuid4().hex[:16].upper()}"


class FunctionalTestDefect(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    defect_no = models.CharField(verbose_name="缺陷编号", max_length=32, unique=True, default=generate_defect_no)
    title = models.CharField(verbose_name="缺陷标题", max_length=256)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    requirement_version = models.ForeignKey(
        to="ManualTestSuite",
        to_field="id",
        related_name="defects",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    module = models.ForeignKey(to=ProductModule, to_field="id", null=True, blank=True, on_delete=models.PROTECT)
    source_type = models.SmallIntegerField(
        verbose_name="缺陷来源", choices=FunctionalTestDefectSourceEnum.choices(),
        default=FunctionalTestDefectSourceEnum.EXPLORATORY.value,
    )
    defect_type = models.SmallIntegerField(
        verbose_name="缺陷类型", choices=FunctionalTestDefectTypeEnum.choices(),
        default=FunctionalTestDefectTypeEnum.FUNCTIONAL.value,
    )
    severity = models.SmallIntegerField(
        verbose_name="严重程度", choices=FunctionalTestDefectSeverityEnum.choices(),
        default=FunctionalTestDefectSeverityEnum.NORMAL.value,
    )
    priority = models.SmallIntegerField(
        verbose_name="优先级", choices=FunctionalTestDefectPriorityEnum.choices(),
        default=FunctionalTestDefectPriorityEnum.P1.value,
    )
    status = models.SmallIntegerField(
        verbose_name="状态", choices=FunctionalTestDefectStatusEnum.choices(),
        default=FunctionalTestDefectStatusEnum.NEW.value, db_index=True,
    )
    resolution = models.SmallIntegerField(
        verbose_name="解决方式", choices=FunctionalTestDefectResolutionEnum.choices(), null=True, blank=True,
    )
    description = models.TextField(verbose_name="问题描述", null=True, blank=True)
    precondition = models.TextField(verbose_name="前置条件", null=True, blank=True)
    reproduce_steps = models.JSONField(verbose_name="复现步骤", default=list, blank=True)
    expected_result = models.TextField(verbose_name="预期结果", null=True, blank=True)
    actual_result = models.TextField(verbose_name="实际结果")
    environment = models.TextField(verbose_name="环境信息", null=True, blank=True)
    attachment_file_ids = models.JSONField(verbose_name="附件文件ID", default=list, blank=True)
    reporter = models.ForeignKey(
        to=User, to_field="id", related_name="functional_test_defect_reporter", on_delete=models.PROTECT,
    )
    assignee = models.ForeignKey(
        to=User, to_field="id", related_name="functional_test_defect_assignee",
        null=True, blank=True, on_delete=models.SET_NULL,
    )
    resolved_at = models.DateTimeField(verbose_name="解决时间", null=True, blank=True)
    closed_at = models.DateTimeField(verbose_name="关闭时间", null=True, blank=True)
    resolution_note = models.TextField(verbose_name="解决说明", null=True, blank=True)
    update_user = models.ForeignKey(
        to=User, to_field="id", related_name="functional_test_defect_update_user",
        null=True, blank=True, on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "functional_test_defect"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["project_product", "status", "severity"]),
            models.Index(fields=["project_product", "module", "status"]),
            models.Index(fields=["assignee", "status"]),
            models.Index(fields=["update_time"]),
        ]


class FunctionalTestDefectCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    defect = models.ForeignKey(to="FunctionalTestDefect", related_name="case_relations", on_delete=models.CASCADE)
    case = models.ForeignKey(
        to="ManualTestCase", related_name="defect_relations", null=True, blank=True, on_delete=models.PROTECT,
    )
    plan_case = models.ForeignKey(
        to="FunctionalTestPlanCase", related_name="defect_relations", null=True, blank=True, on_delete=models.PROTECT,
    )

    class Meta:
        db_table = "functional_test_defect_case"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(case__isnull=False, plan_case__isnull=True) | Q(case__isnull=True,
                                                                             plan_case__isnull=False)),
                name="functional_test_defect_case_exactly_one_target",
            ),
            models.UniqueConstraint(
                fields=["defect", "case"], condition=Q(case__isnull=False),
                name="functional_test_defect_case_unique_case",
            ),
            models.UniqueConstraint(
                fields=["defect", "plan_case"], condition=Q(plan_case__isnull=False),
                name="functional_test_defect_case_unique_plan_case",
            ),
        ]

# -*- coding: utf-8 -*-
from django.db import models

from src.apps.functional_test.enums import (
    FunctionalTestPlanScopeTypeEnum,
    FunctionalTestPlanStatusEnum,
    FunctionalTestResultEnum,
)
from src.apps.test_center.models import ProjectProduct
from src.apps.user.models import User


class FunctionalTestPlan(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    name = models.CharField(verbose_name="计划名称", max_length=256)
    project_product = models.ForeignKey(to=ProjectProduct, to_field="id", on_delete=models.PROTECT)
    scope_type = models.SmallIntegerField(
        verbose_name="计划类型",
        choices=FunctionalTestPlanScopeTypeEnum.choices(),
        default=FunctionalTestPlanScopeTypeEnum.REQUIREMENT.value,
        db_index=True,
    )
    requirement = models.ForeignKey(
        to="FunctionalTestRequirement",
        to_field="id",
        related_name="test_plans",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    requirement_version = models.ForeignKey(
        to="ManualTestSuite",
        to_field="id",
        related_name="test_plans",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    iteration = models.ForeignKey(
        to="FunctionalTestIteration",
        to_field="id",
        related_name="test_plans",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    scope_ref = models.CharField(verbose_name="Sprint/发布标识", max_length=128, null=True, blank=True, db_index=True)
    environment = models.CharField(verbose_name="测试环境", max_length=128, null=True, blank=True)
    build_version = models.CharField(verbose_name="构建版本", max_length=128, null=True, blank=True)
    owner = models.ForeignKey(to=User, to_field="id", related_name="functional_test_plan_owner",
                              on_delete=models.PROTECT)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_test_plan_update_user",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    planned_start_time = models.DateTimeField(verbose_name="计划开始时间", null=True, blank=True)
    planned_end_time = models.DateTimeField(verbose_name="计划结束时间", null=True, blank=True)
    status = models.SmallIntegerField(
        verbose_name="计划状态",
        choices=FunctionalTestPlanStatusEnum.choices(),
        default=FunctionalTestPlanStatusEnum.DRAFT.value,
        db_index=True,
    )
    started_at = models.DateTimeField(verbose_name="实际开始时间", null=True, blank=True)
    finished_at = models.DateTimeField(verbose_name="实际完成时间", null=True, blank=True)
    remark = models.TextField(verbose_name="备注", null=True, blank=True)

    class Meta:
        db_table = "functional_test_plan"
        ordering = ["-id"]
        indexes = [models.Index(fields=["project_product", "scope_type", "status"])]


class FunctionalTestPlanCase(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    plan = models.ForeignKey(to="FunctionalTestPlan", related_name="plan_cases", on_delete=models.CASCADE)
    case = models.ForeignKey(to="ManualTestCase", related_name="plan_bindings", on_delete=models.PROTECT)
    case_snapshot = models.JSONField(verbose_name="选例快照", default=dict, blank=True)
    library_case_version = models.PositiveIntegerField(verbose_name="选例时用例库版本", default=1)
    sort = models.PositiveIntegerField(verbose_name="排序", default=0)
    result = models.SmallIntegerField(
        verbose_name="执行结果",
        choices=FunctionalTestResultEnum.choices(),
        default=FunctionalTestResultEnum.UNEXECUTED.value,
        db_index=True,
    )
    executor = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_test_plan_case_executor",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    execute_time = models.DateTimeField(verbose_name="执行时间", null=True, blank=True)
    actual_result = models.TextField(verbose_name="实际结果", null=True, blank=True)
    execution_note = models.TextField(verbose_name="执行备注", null=True, blank=True)

    class Meta:
        db_table = "functional_test_plan_case"
        ordering = ["sort", "id"]
        constraints = [models.UniqueConstraint(fields=["plan", "case"], name="functional_test_plan_case_unique")]
        indexes = [models.Index(fields=["plan", "result"])]

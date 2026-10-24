# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Q

from src.apps.functional_test.enums import (
    FunctionalRequirementSelfTestStatusEnum,
    FunctionalRequirementTaskStatusEnum,
    FunctionalRequirementTaskTypeEnum,
)
from src.apps.user.models import User


class FunctionalRequirementTask(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    requirement_version = models.ForeignKey(
        to="ManualTestSuite",
        to_field="id",
        related_name="requirement_tasks",
        on_delete=models.CASCADE,
    )
    name = models.CharField(verbose_name="任务名称", max_length=256)
    task_type = models.SmallIntegerField(
        verbose_name="任务类型",
        choices=FunctionalRequirementTaskTypeEnum.choices(),
        default=FunctionalRequirementTaskTypeEnum.OTHER.value,
        db_index=True,
    )
    status = models.SmallIntegerField(
        verbose_name="任务状态",
        choices=FunctionalRequirementTaskStatusEnum.choices(),
        default=FunctionalRequirementTaskStatusEnum.PENDING.value,
        db_index=True,
    )
    owner = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_requirement_tasks",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    planned_start_date = models.DateField(verbose_name="计划开始日期", null=True, blank=True)
    planned_end_date = models.DateField(verbose_name="计划结束日期", null=True, blank=True)
    actual_start_at = models.DateTimeField(verbose_name="实际开始时间", null=True, blank=True)
    actual_end_at = models.DateTimeField(verbose_name="实际结束时间", null=True, blank=True)
    sort_order = models.PositiveIntegerField(verbose_name="顺序", default=0)
    estimated_person_days = models.DecimalField(
        verbose_name="预估人天", max_digits=7, decimal_places=2, null=True, blank=True,
    )
    actual_person_days = models.DecimalField(
        verbose_name="实际人天", max_digits=7, decimal_places=2, null=True, blank=True,
    )
    self_test_status = models.SmallIntegerField(
        verbose_name="开发自测",
        choices=FunctionalRequirementSelfTestStatusEnum.choices(),
        default=FunctionalRequirementSelfTestStatusEnum.NOT_STARTED.value,
    )
    remark = models.TextField(verbose_name="备注", null=True, blank=True)
    update_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_requirement_task_updates",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "functional_requirement_task"
        ordering = ["sort_order", "id"]
        indexes = [
            models.Index(fields=["requirement_version", "status"]),
            models.Index(fields=["owner", "planned_start_date", "planned_end_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(planned_end_date__isnull=True) | Q(planned_start_date__isnull=True)
                          | Q(planned_end_date__gte=models.F("planned_start_date")),
                name="functional_requirement_task_date_order",
            ),
        ]


class FunctionalRequirementCase(models.Model):
    create_time = models.DateTimeField(verbose_name="绑定时间", auto_now_add=True)
    requirement_version = models.ForeignKey(
        to="ManualTestSuite",
        to_field="id",
        related_name="case_bindings",
        on_delete=models.CASCADE,
    )
    case = models.ForeignKey(
        to="ManualTestCase",
        to_field="id",
        related_name="requirement_bindings",
        on_delete=models.PROTECT,
    )
    bound_case_version = models.PositiveIntegerField(verbose_name="已确认用例版本", default=1)
    sort_order = models.PositiveIntegerField(verbose_name="需求内顺序", default=0)
    create_user = models.ForeignKey(
        to=User,
        to_field="id",
        related_name="functional_requirement_case_bindings",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        db_table = "functional_requirement_case"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["requirement_version", "case"],
                name="functional_requirement_case_unique",
            ),
        ]

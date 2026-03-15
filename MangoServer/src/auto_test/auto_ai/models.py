# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: AI写用例数据模型
# @Author : 毛鹏
from django.db import models

from src.auto_test.auto_system.models import ProjectProduct, ProductModule
from src.auto_test.auto_user.models import User
from src.enums.ai_enum import (
    AiRequirementInputTypeEnum,
    AiRequirementStatusEnum,
    AiConfirmStatusEnum,
    AiTestPointTypeEnum,
    AiCasePriorityEnum,
    AiCaseTypeEnum,
    AiCaseStatusEnum,
    AiCaseTestResultEnum,
    AiCaseAutoTagEnum,
)
from src.exceptions import ToolsError

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class AiRequirement(models.Model):
    """AI需求主表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(
        to=ProjectProduct, to_field="id", on_delete=models.PROTECT,
        verbose_name="项目产品"
    )
    module = models.ForeignKey(
        to=ProductModule, to_field="id", on_delete=models.SET_NULL,
        verbose_name="产品模块", null=True, blank=True
    )
    name = models.CharField(verbose_name="需求名称", max_length=255)
    input_type = models.SmallIntegerField(
        verbose_name="输入类型",
        default=AiRequirementInputTypeEnum.TEXT.value,
        db_index=True
    )
    input_content = models.TextField(verbose_name="输入内容（文本/URL）", null=True, blank=True)
    input_file = models.FileField(
        verbose_name="上传文件（图片/Word）",
        upload_to='ai_requirement/',
        null=True,
        blank=True
    )
    status = models.SmallIntegerField(
        verbose_name="处理状态",
        default=AiRequirementStatusEnum.PENDING.value,
        db_index=True
    )
    create_user = models.ForeignKey(
        to=User, to_field="id", on_delete=models.PROTECT,
        verbose_name="创建人"
    )
    ai_model = models.CharField(verbose_name="AI模型快照", max_length=64, null=True, blank=True)
    error_msg = models.TextField(verbose_name="失败信息", null=True, blank=True)

    class Meta:
        db_table = 'ai_requirement'
        ordering = ['-id']

    def delete(self, *args, **kwargs):
        if AiRequirementSplit.objects.filter(requirement=self).exists():
            raise ToolsError(300, "需求拆分-有关联数据，请先删除关联数据后再删除！")
        if self.input_file:
            self.input_file.delete(save=False)
        super().delete(*args, **kwargs)


class AiRequirementSplit(models.Model):
    """需求拆分子模块表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(
        to=ProjectProduct, to_field="id", on_delete=models.PROTECT,
        verbose_name="项目产品"
    )
    module = models.ForeignKey(
        to=ProductModule, to_field="id", on_delete=models.SET_NULL,
        verbose_name="产品模块", null=True, blank=True
    )
    requirement = models.ForeignKey(
        to=AiRequirement, to_field="id", on_delete=models.CASCADE,
        verbose_name="所属需求", db_index=True
    )
    name = models.CharField(verbose_name="子模块名称", max_length=255)
    description = models.TextField(verbose_name="子模块功能描述", null=True, blank=True)
    sort = models.SmallIntegerField(verbose_name="排序", default=0)
    is_confirmed = models.SmallIntegerField(
        verbose_name="确认状态",
        default=AiConfirmStatusEnum.PENDING.value,
        db_index=True
    )
    ai_raw = models.TextField(verbose_name="AI原始输出", null=True, blank=True)

    class Meta:
        db_table = 'ai_requirement_split'
        ordering = ['sort', 'id']

    def delete(self, *args, **kwargs):
        if AiTestPoint.objects.filter(requirement_split=self).exists():
            raise ToolsError(300, "测试点-有关联数据，请先删除关联数据后再删除！")
        super().delete(*args, **kwargs)


class AiTestPoint(models.Model):
    """测试点表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(
        to=ProjectProduct, to_field="id", on_delete=models.PROTECT,
        verbose_name="项目产品"
    )
    module = models.ForeignKey(
        to=ProductModule, to_field="id", on_delete=models.SET_NULL,
        verbose_name="产品模块", null=True, blank=True
    )
    # 冗余需求外键，支持直接按需求聚合查询
    requirement = models.ForeignKey(
        to=AiRequirement, to_field="id", on_delete=models.CASCADE,
        verbose_name="所属需求", db_index=True
    )
    # 精确父级：所属拆分子模块
    requirement_split = models.ForeignKey(
        to=AiRequirementSplit, to_field="id", on_delete=models.CASCADE,
        verbose_name="所属子模块", db_index=True
    )
    name = models.CharField(verbose_name="测试点名称", max_length=255)
    test_type = models.SmallIntegerField(
        verbose_name="测试点类型",
        default=AiTestPointTypeEnum.FUNCTIONAL.value,
        db_index=True
    )
    description = models.TextField(verbose_name="测试点描述", null=True, blank=True)
    is_confirmed = models.SmallIntegerField(
        verbose_name="确认状态",
        default=AiConfirmStatusEnum.PENDING.value,
        db_index=True
    )

    class Meta:
        db_table = 'ai_test_point'
        ordering = ['id']

    def delete(self, *args, **kwargs):
        if AiTestCase.objects.filter(test_point=self).exists():
            raise ToolsError(300, "AI测试用例-有关联数据，请先删除关联数据后再删除！")
        super().delete(*args, **kwargs)


class AiTestCase(models.Model):
    """AI生成测试用例表"""
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(
        to=ProjectProduct, to_field="id", on_delete=models.PROTECT,
        verbose_name="项目产品"
    )
    module = models.ForeignKey(
        to=ProductModule, to_field="id", on_delete=models.SET_NULL,
        verbose_name="产品模块", null=True, blank=True
    )
    # 冗余外键，支持高效聚合查询
    requirement = models.ForeignKey(
        to=AiRequirement, to_field="id", on_delete=models.CASCADE,
        verbose_name="所属需求", db_index=True
    )
    requirement_split = models.ForeignKey(
        to=AiRequirementSplit, to_field="id", on_delete=models.CASCADE,
        verbose_name="所属子模块", db_index=True
    )
    # 精确父级：所属测试点
    test_point = models.ForeignKey(
        to=AiTestPoint, to_field="id", on_delete=models.CASCADE,
        verbose_name="所属测试点", db_index=True
    )
    # -------- 用例核心字段 --------
    case_no = models.CharField(verbose_name="用例编号", max_length=64, null=True, blank=True)
    title = models.CharField(verbose_name="用例标题", max_length=512)
    module_name = models.CharField(verbose_name="所属模块名称", max_length=255, null=True, blank=True)
    case_type = models.SmallIntegerField(
        verbose_name="用例类型",
        default=AiCaseTypeEnum.NORMAL.value,
        db_index=True
    )
    priority = models.SmallIntegerField(
        verbose_name="优先级",
        default=AiCasePriorityEnum.MEDIUM.value,
        db_index=True
    )
    version = models.CharField(verbose_name="版本编号", max_length=64, null=True, blank=True)
    precondition = models.TextField(verbose_name="前置条件", null=True, blank=True)
    steps = models.JSONField(verbose_name="测试步骤", default=list)
    expected = models.TextField(verbose_name="预期结果")
    # -------- 测试结果字段 --------
    dev_test_result = models.SmallIntegerField(
        verbose_name="开发自测结果",
        default=AiCaseTestResultEnum.NOT_TESTED.value
    )
    test_result = models.SmallIntegerField(
        verbose_name="测试结果",
        default=AiCaseTestResultEnum.NOT_TESTED.value,
        db_index=True
    )
    pre_release_result = models.SmallIntegerField(
        verbose_name="预发结果",
        default=AiCaseTestResultEnum.NOT_TESTED.value
    )
    # -------- 标识与备注 --------
    auto_tag = models.SmallIntegerField(
        verbose_name="自动化标识",
        default=AiCaseAutoTagEnum.NONE.value
    )
    remark = models.TextField(verbose_name="备注/附件", null=True, blank=True)
    status = models.SmallIntegerField(
        verbose_name="用例状态",
        default=AiCaseStatusEnum.DRAFT.value,
        db_index=True
    )

    class Meta:
        db_table = 'ai_test_case'
        ordering = ['case_no', 'id']

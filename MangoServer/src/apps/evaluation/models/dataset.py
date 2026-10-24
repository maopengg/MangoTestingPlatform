from django.db import models
from src.apps.evaluation.enums import (
    EvaluationStatusEnum,
    EvaluationVersionStatusEnum,
)
from src.apps.evaluation.models.base import EvaluationAuditModel
from src.apps.user.models import User


class EvaluationDataset(EvaluationAuditModel):
    name = models.CharField(verbose_name="数据集名称", max_length=128)
    task_type = models.JSONField(verbose_name="任务类型", default=list, blank=True, help_text="用户自定义 string[]，例如记忆、问答；不使用固定枚举")
    description = models.TextField(verbose_name="说明", null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_evaluation_datasets", verbose_name="负责人")
    status = models.CharField(verbose_name="状态", max_length=16, choices=EvaluationStatusEnum.choices(), default=EvaluationStatusEnum.DRAFT.value, db_index=True)
    update_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_evaluation_datasets", verbose_name="更新人")

    class Meta:
        verbose_name = "评测数据集"
        db_table = "evaluation_dataset"
        ordering = ["-update_time", "-id"]
        constraints = [models.UniqueConstraint(fields=["name"], name="uniq_eval_dataset_name")]


class EvaluationDatasetVersion(EvaluationAuditModel):
    dataset = models.ForeignKey(EvaluationDataset, on_delete=models.PROTECT, related_name="versions", verbose_name="数据集")
    version_no = models.PositiveIntegerField(verbose_name="版本号")
    version_label = models.CharField(verbose_name="版本名称", max_length=64, blank=True, default="")
    status = models.CharField(verbose_name="状态", max_length=16, choices=EvaluationVersionStatusEnum.choices(), default=EvaluationVersionStatusEnum.DRAFT.value, db_index=True)
    content_hash = models.CharField(verbose_name="内容Hash", max_length=64, blank=True, default="", db_index=True)
    schema_snapshot = models.JSONField(verbose_name="Schema快照", default=dict, help_text="EvaluationDatasetSchema v1", blank=True)
    change_summary = models.TextField(verbose_name="版本说明", null=True, blank=True)
    quality_report = models.JSONField(verbose_name="数据质量报告", default=dict, blank=True, help_text="object{valid,item_count,enabled_count,errors:object[],warnings:object[],tag_distribution,label_distribution}")
    quality_warning_acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="acknowledged_evaluation_dataset_versions", verbose_name="质量警告确认人")
    quality_warning_acknowledged_at = models.DateTimeField(verbose_name="质量警告确认时间", null=True, blank=True)
    published_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="published_evaluation_dataset_versions", verbose_name="发布人")
    published_at = models.DateTimeField(verbose_name="发布时间", null=True, blank=True)

    class Meta:
        verbose_name = "评测数据集版本"
        db_table = "evaluation_dataset_version"
        ordering = ["dataset_id", "-version_no", "-id"]
        constraints = [models.UniqueConstraint(fields=["dataset", "version_no"], name="uniq_eval_dataset_version")]
        indexes = [models.Index(fields=["dataset", "status", "version_no"], name="idx_eval_dataset_version")]


class EvaluationDatasetItem(EvaluationAuditModel):
    dataset_version = models.ForeignKey(EvaluationDatasetVersion, on_delete=models.CASCADE, related_name="items", verbose_name="数据集版本")
    input_data = models.JSONField(verbose_name="输入", default=dict, help_text="受数据集版本Schema约束", blank=True)
    expected_output = models.JSONField(verbose_name="期望", default=dict, help_text="受数据集版本Schema约束", blank=True)
    context = models.JSONField(verbose_name="参考上下文", default=dict, help_text="受数据集版本Schema约束", blank=True)
    metadata = models.JSONField(verbose_name="元数据", default=dict, help_text="受数据集版本Schema约束", blank=True)
    tags = models.JSONField(verbose_name="标签", default=list, help_text="string[]", blank=True)
    priority = models.CharField(verbose_name="优先级", max_length=4, default="P1")
    weight = models.DecimalField(verbose_name="权重", max_digits=8, decimal_places=3, default=1)
    enabled = models.BooleanField(verbose_name="启用", default=True)
    content_hash = models.CharField(verbose_name="内容Hash", max_length=64, blank=True, default="", db_index=True)

    grading_config = models.JSONField(verbose_name="评分覆盖", default=dict, blank=True, help_text="EvaluationItemGrading v1：mode=inherit|replace、graders")
    scenario = models.JSONField(verbose_name="会话与时序", default=dict, blank=True, help_text="EvaluationItemScenario：group_key、order、turns[{name,input_data,expected_output,context,score}]")
    data_source = models.JSONField(verbose_name="条目数据来源", default=dict, blank=True, help_text="EvaluationItemDataSource：kind、binding、query、parameters、timeout_seconds")

    class Meta:
        verbose_name = "评测数据条目"
        db_table = "evaluation_dataset_item"
        ordering = ["dataset_version_id", "id"]
        constraints = [
            models.CheckConstraint(check=models.Q(weight__gt=0), name="eval_item_weight_positive"),
        ]
        indexes = [models.Index(fields=["dataset_version", "enabled", "id"], name="idx_eval_item_active")]

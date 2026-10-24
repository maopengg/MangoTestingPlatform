from django.db import models
from src.apps.evaluation.enums import EvaluationStatusEnum
from src.apps.evaluation.models.base import EvaluationAuditModel
from src.apps.test_center.models import ProductModule, ProjectProduct
from src.apps.user.models import User


class EvaluationCase(EvaluationAuditModel):
    project_product = models.ForeignKey(ProjectProduct, on_delete=models.PROTECT, related_name="evaluation_cases", verbose_name="项目产品")
    module = models.ForeignKey(ProductModule, on_delete=models.PROTECT, null=True, blank=True, related_name="evaluation_cases", verbose_name="产品模块")
    dataset_version = models.ForeignKey("EvaluationDatasetVersion", on_delete=models.PROTECT, null=True, blank=True, related_name="cases", verbose_name="数据集版本")
    config = models.JSONField(verbose_name="用例配置", default=dict, blank=True, help_text="未配置草稿为空对象；已配置使用 EvaluationCaseConfig v1：target、data_selection、mapping、grading、execution")
    name = models.CharField(verbose_name="用例名称", max_length=128)
    description = models.TextField(verbose_name="说明", null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="owned_evaluation_cases", verbose_name="负责人")
    status = models.CharField(verbose_name="状态", max_length=16, choices=EvaluationStatusEnum.choices(), default=EvaluationStatusEnum.DRAFT.value, db_index=True)
    update_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_evaluation_cases", verbose_name="更新人")

    class Meta:
        verbose_name = "评测用例"
        db_table = "evaluation_case"
        ordering = ["-update_time", "-id"]
        constraints = [models.UniqueConstraint(fields=["project_product", "name"], name="uniq_evaluation_case_product_name")]
        indexes = [models.Index(fields=["project_product", "status", "update_time"], name="idx_eval_case_list")]

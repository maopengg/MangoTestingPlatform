import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from src.apps.evaluation.enums import (
    EvaluationExecutionStatusEnum,
    EvaluationGradeStatusEnum,
    EvaluationCaseExecutionStatusEnum,
    EvaluationTriggerTypeEnum,
    EvaluationVerdictEnum,
)
from src.apps.evaluation.models.base import EvaluationAuditModel
from src.apps.user.models import User


def generate_evaluation_execution_no():
    return f"EV-{uuid.uuid4().hex[:16].upper()}"


class EvaluationCaseExecution(EvaluationAuditModel):
    report_detail = models.OneToOneField(
        "test_center.TestSuiteDetails", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="evaluation_execution", verbose_name="统一执行报告明细",
    )
    execution_no = models.CharField(verbose_name="执行编号", max_length=40, unique=True, default=generate_evaluation_execution_no)
    case = models.ForeignKey("EvaluationCase", on_delete=models.PROTECT, related_name="executions", verbose_name="评测用例")
    dataset_version = models.ForeignKey("EvaluationDatasetVersion", on_delete=models.PROTECT, related_name="executions", verbose_name="数据集版本")
    retry_of = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="retries", verbose_name="重试来源")
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    trigger_type = models.CharField(verbose_name="触发类型", max_length=16, choices=EvaluationTriggerTypeEnum.choices(), default=EvaluationTriggerTypeEnum.MANUAL.value)
    idempotency_key = models.CharField(verbose_name="幂等键", max_length=160, unique=True, null=True, blank=True)
    status = models.CharField(verbose_name="执行状态", max_length=24, choices=EvaluationCaseExecutionStatusEnum.choices(), default=EvaluationCaseExecutionStatusEnum.PENDING.value, db_index=False)
    verdict = models.CharField(verbose_name="效果结论", max_length=24, choices=EvaluationVerdictEnum.choices(), default=EvaluationVerdictEnum.NOT_EVALUATED.value, db_index=False)
    progress = models.PositiveSmallIntegerField(verbose_name="进度", default=0, validators=[MaxValueValidator(100)])
    snapshot = models.JSONField(verbose_name="配置快照", default=dict, help_text="EvaluationExecutionSnapshot v1：case、dataset、selection、target、mapping、grader_bindings、grading、execution、environment、request、signatures", blank=True)
    summary = models.JSONField(verbose_name="结果汇总", default=dict, help_text="EvaluationCaseExecutionSummary v1", blank=True)
    details = models.JSONField(verbose_name="执行详情", default=dict, blank=True, help_text="EvaluationExecutionDetails v1：error_category、error_message、diagnostic_ref")
    stop_requested = models.BooleanField(verbose_name="请求停止", default=False)
    lease_owner = models.CharField(verbose_name="执行租约持有者", max_length=128, null=True, blank=True, db_index=False)
    lease_expires_at = models.DateTimeField(verbose_name="执行租约到期时间", null=True, blank=True, db_index=False)
    started_at = models.DateTimeField(verbose_name="开始时间", null=True, blank=True)
    finished_at = models.DateTimeField(verbose_name="完成时间", null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_evaluation_executions", verbose_name="创建人")

    class Meta:
        verbose_name = "Case 执行"
        db_table = "evaluation_case_execution"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["case", "test_env", "id"], name="idx_eval_exec_history"),
            models.Index(fields=["status", "lease_expires_at", "id"], name="idx_eval_exec_claim"),
        ]


class EvaluationItemResult(EvaluationAuditModel):
    execution = models.ForeignKey(EvaluationCaseExecution, on_delete=models.CASCADE, related_name="item_results", verbose_name="Case 执行")
    dataset_item = models.ForeignKey("EvaluationDatasetItem", on_delete=models.PROTECT, related_name="execution_results", verbose_name="评测数据条目")
    repeat_index = models.PositiveSmallIntegerField(verbose_name="重复序号", default=1)
    item_snapshot = models.JSONField(verbose_name="数据条目快照", default=dict, help_text="EvaluationDatasetItemSnapshot v1", blank=True)
    execution_status = models.CharField(verbose_name="执行状态", max_length=24, choices=EvaluationExecutionStatusEnum.choices(), default=EvaluationExecutionStatusEnum.PENDING.value, db_index=False)
    grade_status = models.CharField(verbose_name="评测状态", max_length=24, choices=EvaluationGradeStatusEnum.choices(), default=EvaluationGradeStatusEnum.PENDING.value, db_index=False)
    verdict = models.CharField(verbose_name="效果结论", max_length=24, choices=EvaluationVerdictEnum.choices(), default=EvaluationVerdictEnum.NOT_EVALUATED.value, db_index=False)
    score = models.DecimalField(verbose_name="得分", max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    actual_output = models.JSONField(verbose_name="标准化输出", default=dict, blank=True, help_text="由用例 output_mapping 生成的评分器输入对象")
    resolved_expected_output = models.JSONField(verbose_name="运行时解析真值", default=dict, blank=True, help_text="expected_output 与 Oracle output_mapping 输出合并后的金标准对象")
    details = models.JSONField(verbose_name="执行详情", default=dict, blank=True, help_text="EvaluationItemDetails v1：references:{oracle,fixture,raw_output,execution}、timing:{execution_ms,grade_ms}、error_message")
    attempts = models.JSONField(verbose_name="执行尝试记录", default=list, blank=True, help_text="EvaluationAttemptRecord[]；按尝试顺序追加，禁止覆盖或截断历史")
    error_category = models.CharField(verbose_name="错误分类", max_length=64, null=True, blank=True, db_index=False)

    def save(self, *args, **kwargs):
        output = self.actual_output
        if output is None:
            # An extracted JSON null is a value, not SQL NULL in this non-null JSON column.
            self.actual_output = models.Value(None, output_field=models.JSONField())
        try:
            return super().save(*args, **kwargs)
        finally:
            self.actual_output = output

    class Meta:
        verbose_name = "数据条目执行结果"
        db_table = "evaluation_item_result"
        ordering = ["execution_id", "dataset_item_id", "repeat_index"]
        constraints = [models.UniqueConstraint(fields=["execution", "dataset_item", "repeat_index"], name="uniq_eval_item_repeat")]
        indexes = [
            models.Index(fields=["execution", "verdict", "id"], name="idx_eval_item_verdict"),
            models.Index(fields=["execution", "grade_status", "id"], name="idx_eval_item_grade"),
        ]


class EvaluationGradeResult(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    item_result = models.ForeignKey(EvaluationItemResult, on_delete=models.CASCADE, related_name="grade_results", verbose_name="数据条目运行")
    grader_key = models.CharField(verbose_name="评分器编码", max_length=64)
    grader_version = models.PositiveIntegerField(verbose_name="评分器版本", default=1)
    score = models.DecimalField(verbose_name="标准化分数", max_digits=6, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    raw_value = models.JSONField(verbose_name="原始值", null=True, blank=True, help_text="GraderMetric.raw_value；取值类型及对象字段由对应评分器定义")
    passed = models.BooleanField(verbose_name="是否通过", default=False, db_index=False)
    grading_snapshot = models.JSONField(verbose_name="评分配置快照", default=dict, blank=True, help_text="EvaluationGradeSnapshot v1：binding_hash、metric、threshold、weight")
    hard_gate = models.BooleanField(verbose_name="硬门禁", default=False)
    evidence = models.JSONField(verbose_name="证据", default=dict, blank=True, help_text="注册评分器约定的证据对象")
    reason = models.TextField(verbose_name="结论", null=True, blank=True)
    confidence = models.DecimalField(verbose_name="置信度", max_digits=5, decimal_places=4, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])

    class Meta:
        verbose_name = "评测指标结果"
        db_table = "evaluation_grade_result"
        ordering = ["item_result_id", "id"]

from django.db import models, transaction

from src.apps.task_center.enums.execution import AutomationExecutionScopeEnum, ReportRetentionPolicyEnum
from src.apps.test_center.enums.case import ReportFailureReasonEnum
from src.apps.user.models import User

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class TestSuite(models.Model):
    report_retained = models.BooleanField(verbose_name="保留完整报告", default=True)
    report_retention_policy = models.CharField(verbose_name="报告保留策略快照", max_length=32,
        choices=ReportRetentionPolicyEnum.choices(), default=ReportRetentionPolicyEnum.ALL.value)
    retained_summary = models.JSONField(verbose_name="已清理报告的轻量摘要", null=True, blank=True,
        help_text="v1: version、counter_data（报告计数）、execution_summary（状态计数）；不保存用例或请求响应")
    id = models.BigIntegerField(primary_key=True, editable=False)
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    project_product = models.ForeignKey(to="ProjectProduct", to_field="id", on_delete=models.PROTECT)
    module = models.ForeignKey(to="ProductModule", to_field="id", on_delete=models.SET_NULL, null=True, blank=True)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    execution_scenes = models.JSONField(verbose_name="执行场景快照", default=list, blank=True)
    execution_scope = models.CharField(
        verbose_name="执行范围快照",
        max_length=32,
        choices=AutomationExecutionScopeEnum.choices(),
        default=AutomationExecutionScopeEnum.UNCLASSIFIED.value,
        db_index=True,
    )
    user = models.ForeignKey(to=User, to_field="id", verbose_name='用例执行人', on_delete=models.PROTECT)
    tasks = models.ForeignKey(to="task_center.Tasks", to_field="id", on_delete=models.SET_NULL, null=True)
    execution_name = models.CharField(verbose_name="执行名称", max_length=128, null=True, blank=True)
    api_concurrency_limit = models.PositiveIntegerField(
        verbose_name="API执行并发快照",
        null=True,
        blank=True,
    )
    diagnostic_file_path = models.CharField(
        verbose_name="排查报告文件路径",
        max_length=500,
        null=True,
        blank=True,
    )

    status = models.SmallIntegerField(verbose_name="测试结果", db_index=True)
    is_notice = models.SmallIntegerField(verbose_name="是否发送通知", db_index=True)

    class Meta:
        db_table = 'test_suite'
        ordering = ['-create_time']
        indexes = [models.Index(fields=['report_retained', '-create_time', '-id'], name='idx_suite_retained_time')]

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            TestSuiteDetails.objects.filter(test_suite=self).delete()
            super().delete(*args, **kwargs)


class TestSuiteDetails(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    test_suite = models.ForeignKey(to="TestSuite", to_field="id", on_delete=models.CASCADE)
    # 取值来自共享 TestCaseTypeEnum，已有类型值不得重排。
    type = models.SmallIntegerField(verbose_name="类型", db_index=True)
    project_product = models.ForeignKey(to="ProjectProduct", to_field="id", on_delete=models.PROTECT)
    test_env = models.SmallIntegerField(verbose_name="测试环境")
    case_id = models.BigIntegerField(verbose_name="用例ID")
    case_name = models.CharField(verbose_name="key", max_length=528, null=True, blank=True)
    parametrize = models.JSONField(verbose_name="参数化", default=list, blank=True)
    api_case_revision = models.ForeignKey(
        to='auto_api.ApiCaseRevision',
        to_field="id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    api_case_release = models.ForeignKey(
        to='auto_api.ApiCaseRelease',
        to_field="id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    config_checksum = models.CharField(verbose_name="执行配置哈希", max_length=64, null=True, blank=True)
    # 0失败，1成功，2待开始，3进行中，4警告，5已停止
    status = models.SmallIntegerField(verbose_name="测试结果", db_index=True)
    error_message = models.TextField(verbose_name="错误提示", null=True, blank=True)
    retry = models.SmallIntegerField(verbose_name="重试次数")
    push_time = models.DateTimeField(verbose_name="修改时间", null=True, blank=True)
    case_sum = models.SmallIntegerField(verbose_name="用例数", default=0)
    success = models.SmallIntegerField(verbose_name="成功数", default=0)
    fail = models.SmallIntegerField(verbose_name="失败数", default=0)
    warning = models.SmallIntegerField(verbose_name="警告数", default=0)
    summary_data = models.JSONField(verbose_name="轻量测试结果摘要", null=True, blank=True)
    is_excluded = models.BooleanField(verbose_name="排除报告统计", default=False)
    failure_reason = models.CharField(verbose_name="失败原因分类", max_length=32, choices=ReportFailureReasonEnum.choices(), blank=True, default='')
    failure_description = models.TextField(verbose_name="失败排查说明", max_length=1000, blank=True, default='')

    class Meta:
        db_table = 'test_suite_details'
        ordering = ['-create_time']
        indexes = [
            models.Index(fields=['case_id', 'type'], name='idx_detail_case_type'),
            models.Index(
                fields=['type', 'status', 'retry', 'test_suite_id', 'id'],
                name='idx_detail_pending_claim',
            ),
            models.Index(
                fields=['type', 'status', 'push_time', 'retry', 'test_suite_id', 'id'],
                name='idx_detail_timeout_claim',
            ),
            models.Index(fields=['test_suite_id', 'type', '-id'], name='idx_suite_type_id_desc'),
            models.Index(fields=['test_suite_id', 'type', 'status', '-id'], name='idx_suite_type_status_id_desc'),
        ]


class ExecutionResult(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    source_type = models.CharField(verbose_name="执行来源", max_length=32, db_index=True)
    target_type = models.CharField(verbose_name="执行对象类型", max_length=32, db_index=True)
    target_id = models.BigIntegerField(verbose_name="执行对象ID", db_index=True)
    test_suite = models.ForeignKey(
        to="TestSuite",
        to_field="id",
        related_name="execution_results",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    test_suite_detail = models.ForeignKey(
        to="TestSuiteDetails",
        to_field="id",
        related_name="execution_results",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    revision_id = models.BigIntegerField(verbose_name="修订ID", null=True, blank=True, db_index=True)
    release_id = models.BigIntegerField(verbose_name="发布ID", null=True, blank=True, db_index=True)
    test_env = models.SmallIntegerField(verbose_name="测试环境", null=True, blank=True, db_index=True)
    status = models.SmallIntegerField(verbose_name="执行状态", null=True, blank=True, db_index=True)
    error_message = models.TextField(verbose_name="错误信息", null=True, blank=True)
    duration = models.FloatField(verbose_name="执行耗时", null=True, blank=True)
    attempt_no = models.PositiveIntegerField(verbose_name="执行次数", default=1)
    is_latest = models.BooleanField(verbose_name="是否最新结果", default=True, db_index=True)
    result_data = models.JSONField(verbose_name="完整执行结果", null=True, blank=True)
    result_object_key = models.CharField(verbose_name="结果文件对象Key", max_length=1024, null=True, blank=True)
    result_file_name = models.CharField(verbose_name="结果文件名", max_length=255, null=True, blank=True)
    result_size = models.BigIntegerField(verbose_name="结果大小", default=0)
    result_checksum = models.CharField(verbose_name="结果校验值", max_length=64, null=True, blank=True)
    result_cleaned = models.BooleanField(verbose_name="结果是否已清理", default=False, db_index=True)
    result_cleaned_at = models.DateTimeField(verbose_name="结果清理时间", null=True, blank=True)
    trigger_user = models.ForeignKey(
        to=User,
        to_field="id",
        verbose_name="触发人",
        related_name="execution_result_trigger_user",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    trace_id = models.CharField(verbose_name="执行链路ID", max_length=64, null=True, blank=True, db_index=True)
    task_id = models.CharField(verbose_name="异步任务ID", max_length=64, null=True, blank=True, db_index=True)
    source_snapshot = models.JSONField(
        verbose_name="执行来源快照",
        null=True,
        blank=True,
        help_text="ExecutionSourceSnapshot v1; credentials forbidden",
    )

    class Meta:
        db_table = 'execution_result'
        ordering = ['-create_time']
        indexes = [
            models.Index(
                fields=['target_type', 'target_id', 'revision_id', 'test_env', 'is_latest'],
                name='idx_exec_result_target_latest',
            ),
            models.Index(
                fields=['target_type', 'target_id', 'create_time'],
                name='idx_exec_result_target_time',
            ),
            models.Index(
                fields=['test_suite_detail', 'is_latest'],
                name='idx_exec_result_detail_latest',
            ),
        ]

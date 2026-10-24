from django.db import models

"""
     1.python manage.py makemigrations
     2.python manage.py migrate
"""


class ApiCaseExecutionTrace(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    trace_id = models.CharField(verbose_name="链路ID", max_length=64, unique=True)
    source_type = models.SmallIntegerField(verbose_name="来源类型", db_index=True)
    test_suite_id = models.BigIntegerField(verbose_name="测试套ID", null=True, blank=True, db_index=True)
    test_suite_detail_id = models.BigIntegerField(verbose_name="测试套明细ID", null=True, blank=True, db_index=True)
    case_id = models.IntegerField(verbose_name="API用例ID", db_index=True)
    case_name = models.CharField(verbose_name="API用例名称快照", max_length=512, null=True, blank=True)
    user_id = models.IntegerField(verbose_name="执行用户ID", null=True, blank=True, db_index=True)
    test_env = models.SmallIntegerField(verbose_name="测试环境", null=True, blank=True, db_index=True)
    status = models.SmallIntegerField(verbose_name="执行状态", default=2, db_index=True)
    worker_name = models.CharField(verbose_name="执行节点", max_length=128, null=True, blank=True)
    started_at = models.DateTimeField(verbose_name="开始时间", null=True, blank=True)
    finished_at = models.DateTimeField(verbose_name="结束时间", null=True, blank=True)
    duration_ms = models.IntegerField(verbose_name="总耗时毫秒", default=0)
    error_message = models.TextField(verbose_name="错误摘要", null=True, blank=True)
    summary = models.JSONField(verbose_name="执行摘要", default=dict, blank=True)

    class Meta:
        db_table = 'api_case_execution_trace'
        indexes = [
            models.Index(fields=['test_suite_detail_id', 'create_time']),
            models.Index(fields=['case_id', 'create_time']),
        ]


class ApiCaseExecutionStep(models.Model):
    create_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    update_time = models.DateTimeField(verbose_name="修改时间", auto_now=True)
    trace = models.ForeignKey(to="ApiCaseExecutionTrace", to_field="id", on_delete=models.CASCADE)
    parent_step_id = models.BigIntegerField(verbose_name="父步骤ID", null=True, blank=True)
    step_key = models.CharField(verbose_name="步骤唯一key", max_length=128)
    step_type = models.CharField(verbose_name="步骤类型", max_length=64, db_index=True)
    step_name = models.CharField(verbose_name="步骤名称", max_length=128)
    status = models.SmallIntegerField(verbose_name="步骤状态", default=2, db_index=True)
    sort = models.IntegerField(verbose_name="排序", default=0)
    started_at = models.DateTimeField(verbose_name="开始时间", null=True, blank=True)
    finished_at = models.DateTimeField(verbose_name="结束时间", null=True, blank=True)
    duration_ms = models.IntegerField(verbose_name="耗时毫秒", default=0)
    input_summary = models.JSONField(verbose_name="输入摘要", default=dict, blank=True)
    output_summary = models.JSONField(verbose_name="输出摘要", default=dict, blank=True)
    error_message = models.TextField(verbose_name="错误摘要", null=True, blank=True)
    detail_ref_type = models.CharField(verbose_name="详情引用类型", max_length=64, null=True, blank=True)
    detail_ref_id = models.CharField(verbose_name="详情引用ID", max_length=128, null=True, blank=True)

    class Meta:
        db_table = 'api_case_execution_step'
        indexes = [
            models.Index(fields=['trace', 'sort']),
            models.Index(fields=['trace', 'step_type']),
        ]

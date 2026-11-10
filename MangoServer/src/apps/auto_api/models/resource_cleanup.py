from django.db import models

from src.apps.auto_api.enums.resource_cleanup import ApiResourceCleanupStatus


class ApiCaseExecutionResource(models.Model):
    create_time = models.DateTimeField('登记时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now=True)
    case = models.ForeignKey('auto_api.ApiCase', on_delete=models.PROTECT, verbose_name='API用例', db_index=False)
    trace = models.ForeignKey('auto_api.ApiCaseExecutionTrace', on_delete=models.PROTECT,
                             verbose_name='原执行链路', db_index=False)
    step_id = models.BigIntegerField('原步骤ID')
    parameter_id = models.BigIntegerField('原场景ID')
    test_env = models.SmallIntegerField('被测环境')
    rule_key = models.CharField('清理规则键', max_length=64)
    rule = models.JSONField('清理规则快照', help_text='ApiResourceCleanupRule；冻结后不得修改')
    proof = models.JSONField('资源所有权证据', help_text='ApiResourceProof；不保存密码、授权或完整业务响应')
    status = models.CharField('清理状态', max_length=16, default=ApiResourceCleanupStatus.PREPARED.value,
                              choices=ApiResourceCleanupStatus.choices())
    error_message = models.TextField('失败原因', default='', blank=True)
    cleanup_token = models.CharField('清理持有者', max_length=32, default='', blank=True)

    class Meta:
        db_table = 'api_case_execution_resource'
        verbose_name = 'API执行资源清理台账'
        indexes = [models.Index(fields=['case', '-id'], name='idx_api_resource_case_id')]
        constraints = [models.UniqueConstraint(fields=['trace', 'rule_key'], name='uniq_api_resource_trace_rule')]

from django.db import models

from src.apps.auto_api.enums.callback import CallbackRunStatus


class ApiCaseCallbackRun(models.Model):
    execution_key = models.CharField('执行身份', max_length=64)
    rule_key = models.CharField('规则键', max_length=64, db_collation='utf8mb4_bin')
    case = models.ForeignKey('ApiCase', verbose_name='所属用例', on_delete=models.PROTECT)
    mock_config = models.ForeignKey('ApiMockConfig', verbose_name='回调接口', on_delete=models.PROTECT, db_index=False)
    test_env = models.IntegerField('执行环境')
    trace = models.ForeignKey('ApiCaseExecutionTrace', verbose_name='执行链路', on_delete=models.CASCADE,
                              null=True, blank=True)
    rule = models.JSONField('规则快照', default=dict, blank=True)
    mock_snapshot = models.JSONField('响应及断言快照', default=dict, blank=True,
                                     help_text='Mock runtime payload，不含 request_decryption 密钥')
    dependency_digest = models.CharField('依赖摘要', max_length=64)
    correlation_value = models.CharField('关联值', max_length=256, db_collation='utf8mb4_bin')
    correlation_key = models.CharField('关联唯一摘要', max_length=64, unique=True)
    active_key = models.CharField('活动关联占位', max_length=64, null=True, blank=True)
    status = models.CharField('验证状态', max_length=16, default=CallbackRunStatus.WAITING.value)
    started_at = models.DateTimeField('注册时间', auto_now_add=True)
    deadline = models.DateTimeField('等待截止时间')
    observation_deadline = models.DateTimeField('观察截止时间', null=True, blank=True)
    finished_at = models.DateTimeField('完成时间', null=True, blank=True)
    error_message = models.CharField('失败原因', max_length=500, blank=True, default='')
    evidence_bytes = models.PositiveIntegerField('累计证据字节', default=0)

    class Meta:
        db_table = 'api_case_callback_run'
        verbose_name = 'API用例回调验证'
        constraints = [models.UniqueConstraint(fields=['execution_key', 'rule_key'], name='uniq_callback_execution_rule')]
        indexes = [models.Index(fields=['mock_config', 'deadline'], name='idx_callback_mock_deadline'),
                   models.Index(fields=['status', 'deadline'], name='idx_callback_status_deadline'),
                   models.Index(fields=['finished_at', 'id'], name='idx_callback_retention')]

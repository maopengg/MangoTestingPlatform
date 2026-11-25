from src.common.enums.base import BaseEnum


class ReportExecutionPhaseEnum(BaseEnum):
    INFRASTRUCTURE_BLOCKED = ('infrastructure_blocked', '平台受阻')
    AUTOMATIC_RECOVERY = ('automatic_recovery', '自动恢复中')
    RECOVERY_FAILED = ('recovery_failed', '自动恢复已结束')


class ReportRecoveryCauseEnum(BaseEnum):
    WORKER_REPLACED = ('worker_replaced', '执行进程已替换')
    TASK_UNREPORTED = ('task_unreported', '执行结束但结果未收口')
    LEASE_EXPIRED = ('lease_expired', '执行租约超时')
    EXECUTION_TIMEOUT = ('execution_timeout', '执行超时')
    DATASOURCE = ('datasource', '数据源或清理异常')
    CODE_BUG = ('code_bug', '平台内部代码异常')
    RESULT_UNAVAILABLE = ('result_unavailable', '原执行结果待恢复')


class ReportRecoveryActionEnum(BaseEnum):
    RETRY = ('retry', '重新执行')
    RECOVER = ('recover', '恢复原执行')
    FAIL = ('fail', '结束失败')


class ReportRecoveryReasonEnum(BaseEnum):
    NON_RETRYABLE = ('non_retryable_failure', '不允许自动重试的故障')
    DEADLINE_EXHAUSTED = ('recovery_deadline_exhausted', '恢复时限已耗尽')
    RETRY_EXHAUSTED = ('retry_budget_exhausted', '重试次数已耗尽')
    CODE_BUG = ('execution_code_bug', '执行代码异常')
    INTERNAL_ERROR = ('internal_recovery_error', '恢复流程代码异常')
    INVALID_CONTROL = ('invalid_recovery_control', '恢复证据格式不合法')
    RESULT_UNAVAILABLE = ('result_unavailable', '原执行结果待恢复')


class ReportRecoveryOutcomeEnum(BaseEnum):
    RESULT_RESTORED = ('result_restored', '原执行结果已恢复')
    RETRY_QUEUED = ('retry_queued', '已进入原队列等待重试')

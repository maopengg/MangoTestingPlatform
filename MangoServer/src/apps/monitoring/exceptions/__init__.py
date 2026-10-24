"""Business exceptions owned by this Django app."""

from src.common.exceptions.base import MangoServerError
from src.common.exceptions.definitions import ErrorDefinition


class MonitoringError(MangoServerError):
    pass


MONITORING_SERVICE_EXECUTION_MONITORING_INVALID = ErrorDefinition(code=37000,
                                                                  message='监控执行服务未启动或心跳已中断，请启动 monitoring-service 后重试。')
MONITORING_TASK_EXECUTION_MONITORING_DUPLICATED = ErrorDefinition(code=37001,
                                                                  message='监控任务正在启动或运行中，请勿重复执行。')
MONITORING_SCRIPT_CONTENT_REQUIRED = ErrorDefinition(code=37002, message='任务代码内容不能为空')

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
MONITORING_TASK_NOT_ACCESSIBLE = ErrorDefinition(code=37003, message='监控任务不存在或不在当前项目产品范围内')
MONITORING_PRODUCT_NOT_ACCESSIBLE = ErrorDefinition(code=37004, message='项目产品不存在或无权访问')
MONITORING_NOTICE_GROUP_INVALID = ErrorDefinition(code=37005, message='通知组不存在或不属于任务所在项目')
MONITORING_TASK_INPUT_INVALID = ErrorDefinition(code=37006, message='监控任务配置不完整或字段无效')

import re

from src.apps.monitoring.constants import TASK_DIAGNOSTIC_MESSAGE
from src.apps.monitoring.enums import MonitoringLogStatusEnum
from src.apps.monitoring.models import MonitoringReport
from src.common.logging import log


class MonitoringTaskDiagnosticService:
    @staticmethod
    def record(task, reason):
        text = str(reason)[:32000]
        text = re.sub(r'(?i)Bearer\s+[^\s"<>]+', 'Bearer [已脱敏]', text)
        text = re.sub(r'''(?i)(["']?(?:authorization|cookie|password|passwd|secret|token|api[-_]?key|signature|credential)["']?\s*[=:]\s*)(?:"[^"]*"|'[^']*'|[^,\s&<>}]+)''', r'\1[已脱敏]', text)
        try:
            MonitoringReport.objects.create(task_id=task.id, status=MonitoringLogStatusEnum.ERROR.value,
                                            msg=TASK_DIAGNOSTIC_MESSAGE, send_text=text, is_notice=0)
        except Exception:
            log.monitoring.exception(f'保存监控任务失败原因失败：task={task.id}')

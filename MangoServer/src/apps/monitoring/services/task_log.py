from pathlib import Path

from django.conf import settings

from src.apps.monitoring.exceptions import MonitoringError, MONITORING_TASK_NOT_ACCESSIBLE
from src.apps.monitoring.enums import MonitoringTaskStatusEnum
from src.apps.monitoring.selectors.task import MonitoringTaskSelector
from src.apps.monitoring.services.runner import MonitoringTaskRunner


class MonitoringTaskLogService:
    @staticmethod
    def result(task, lines, truncated=False, unavailable=None):
        if task.status == MonitoringTaskStatusEnum.FAILED.value:
            reason = MonitoringTaskSelector.failure_reason(task)
            if reason and reason not in '\n'.join(lines):
                lines = [*lines, '[ERROR] ' + reason]
            elif not reason and not lines:
                lines = [f'[ERROR] 任务执行失败（退出码：{task.exit_code}）；历史记录未保存具体原因，请查看 monitoring-service 系统日志。']
        if unavailable and not lines:
            lines = [unavailable]
        return {'task_id': task.id, 'lines': lines, 'truncated': truncated}

    @staticmethod
    def tail(user, task_id, limit=200):
        task = MonitoringTaskSelector.get(user, task_id)
        return MonitoringTaskLogService.read_task(task, limit)

    @staticmethod
    def read_task(task, limit=200):
        limit = min(max(int(limit), 1), 1000)
        if not task.log_path:
            return MonitoringTaskLogService.result(task, [], unavailable='[INFO] 当前任务尚未生成文件日志。')
        path = Path(MonitoringTaskRunner._get_absolute_path(task.log_path)).resolve()
        if not path.is_relative_to(Path(settings.MONITORING_LOG_DIR).resolve()):
            raise MonitoringError(MONITORING_TASK_NOT_ACCESSIBLE)
        try:
            with path.open('rb') as stream:
                size = stream.seek(0, 2)
                offset = max(size - 64 * 1024, 0)
                stream.seek(offset)
                content = stream.read(64 * 1024)
                if offset:
                    content = content.partition(b'\n')[2]
                lines = content.decode('utf-8', errors='replace').splitlines()
        except FileNotFoundError:
            return MonitoringTaskLogService.result(task, [], unavailable='[INFO] 当前服务器未找到任务日志；多实例部署请确认监控服务与后端共享日志目录。')
        except OSError as error:
            return MonitoringTaskLogService.result(task, [], unavailable=f'[ERROR] 当前服务器无法读取任务日志（{type(error).__name__}）。')
        return MonitoringTaskLogService.result(task, lines[-limit:], bool(offset or len(lines) > limit))

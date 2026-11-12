from django.core.management.base import BaseCommand, CommandError

from src.apps.task_center.services.execution.worker_readiness import ApiWorkerReadinessService


class Command(BaseCommand):
    help = 'Read-only readiness check for this API Worker pod and execution loop'

    def handle(self, *args, **options):
        try:
            ready = ApiWorkerReadinessService.ready()
        except Exception:
            raise CommandError('无法确认 API Worker 状态，请检查平台数据库和 Worker 日志') from None
        if not ready:
            raise CommandError('当前 Pod 缺少新鲜的执行循环健康心跳，API Worker 尚未就绪')
        self.stdout.write('API Worker 执行循环已就绪')

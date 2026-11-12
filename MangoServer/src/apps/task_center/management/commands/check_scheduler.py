from django.core.management.base import BaseCommand, CommandError

from src.apps.task_center.services.scheduling.scheduler_readiness import SchedulerReadinessService


class Command(BaseCommand):
    help = 'Read-only readiness check for this scheduler container and its cleanup consumers'

    def handle(self, *args, **options):
        try:
            ready = SchedulerReadinessService.ready()
        except Exception:
            raise CommandError('无法确认清理消费者状态，请检查平台数据库和 scheduler 日志') from None
        if not ready:
            raise CommandError('当前容器缺少新鲜的清理消费者健康心跳，不能确认清理服务已就绪')
        self.stdout.write('scheduler 清理消费者已就绪')

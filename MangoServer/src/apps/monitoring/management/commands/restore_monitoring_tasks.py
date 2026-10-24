from django.core.management.base import BaseCommand

from src.apps.monitoring.services.runner import MonitoringTaskRunner


class Command(BaseCommand):
    help = '显式恢复运行中的监控任务，不在 Web 进程 ready() 中执行'

    def handle(self, *args, **options):
        MonitoringTaskRunner().restore_running_tasks()
        self.stdout.write(self.style.SUCCESS('监控任务恢复完成'))

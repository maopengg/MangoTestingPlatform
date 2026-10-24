import signal

from django.core.management.base import BaseCommand

from src.processes.monitoring import MonitoringRuntimeService


class Command(BaseCommand):
    help = '启动单实例 monitoring-service，统一托管监控脚本子进程'

    def add_arguments(self, parser):
        parser.add_argument('--instance-name', default='monitoring-1')
        parser.add_argument('--poll-interval', type=float, default=2.0)

    def handle(self, *args, **options):
        service = MonitoringRuntimeService(
            instance_name=options['instance_name'],
            poll_interval=options['poll_interval'],
        )
        signal.signal(signal.SIGTERM, lambda *_: service.stop())
        signal.signal(signal.SIGINT, lambda *_: service.stop())
        service.run_forever()

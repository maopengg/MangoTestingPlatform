from django.core.management.base import BaseCommand
import signal

from src.processes.scheduler.runner import ScheduleRunner


class Command(BaseCommand):
    help = 'Run Mango scheduler service'

    def add_arguments(self, parser):
        parser.add_argument('--node-name', default=None)
        parser.add_argument('--poll-interval', type=int, default=30)
        parser.add_argument('--lookback-minutes', type=int, default=1)
        parser.add_argument('--dispatch-batch-size', type=int, default=50)
        parser.add_argument('--cleanup-only', action='store_true', help='仅消费数据工厂清理任务，不触发或分发定时业务任务')

    def handle(self, *args, **options):
        previous = signal.getsignal(signal.SIGTERM)
        try:
            runner = ScheduleRunner(
                node_name=options['node_name'],
                poll_interval=options['poll_interval'],
                lookback_minutes=options['lookback_minutes'],
                dispatch_batch_size=options['dispatch_batch_size'],
                cleanup_only=options['cleanup_only'],
            )
            signal.signal(signal.SIGTERM, lambda *_: runner.request_stop())
            runner.run_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('scheduler-service 已停止'))
        finally:
            signal.signal(signal.SIGTERM, previous)

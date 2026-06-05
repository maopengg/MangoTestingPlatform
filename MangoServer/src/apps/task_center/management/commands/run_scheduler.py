from django.core.management.base import BaseCommand

from src.services.runtime.scheduler.runner import ScheduleRunner


class Command(BaseCommand):
    help = 'Run Mango scheduler service'

    def add_arguments(self, parser):
        parser.add_argument('--node-name', default=None)
        parser.add_argument('--poll-interval', type=int, default=30)
        parser.add_argument('--lookback-minutes', type=int, default=1)

    def handle(self, *args, **options):
        try:
            ScheduleRunner(
                node_name=options['node_name'],
                poll_interval=options['poll_interval'],
                lookback_minutes=options['lookback_minutes'],
            ).run_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('scheduler-service 已停止'))

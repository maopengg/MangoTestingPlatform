from django.core.management.base import BaseCommand

from src.services.runtime.dispatcher.runner import DispatchRunner


class Command(BaseCommand):
    help = 'Run Mango task dispatcher service'

    def add_arguments(self, parser):
        parser.add_argument('--node-name', default=None)
        parser.add_argument('--poll-interval', type=int, default=5)

    def handle(self, *args, **options):
        try:
            DispatchRunner(
                node_name=options['node_name'],
                poll_interval=options['poll_interval'],
            ).run_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('task-dispatcher 已停止'))

from django.core.management.base import BaseCommand

from src.services.runtime.api_worker.runner import ApiWorkerRunner


class Command(BaseCommand):
    help = 'Run Mango API worker service'

    def add_arguments(self, parser):
        parser.add_argument('--worker-name', default=None)
        parser.add_argument('--concurrency', type=int, default=5)
        parser.add_argument('--lease-seconds', type=int, default=1800)
        parser.add_argument('--poll-interval', type=int, default=3)
        parser.add_argument('--db-idle-seconds', type=int, default=1800)

    def handle(self, *args, **options):
        try:
            ApiWorkerRunner(
                worker_name=options['worker_name'],
                concurrency=options['concurrency'],
                lease_seconds=options['lease_seconds'],
                poll_interval=options['poll_interval'],
                db_idle_seconds=options['db_idle_seconds'],
            ).run_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('api-worker 已停止'))

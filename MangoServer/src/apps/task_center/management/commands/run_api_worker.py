from django.core.management.base import BaseCommand

from src.processes.api_worker.runner import ApiWorkerRunner


class Command(BaseCommand):
    help = 'Run Mango API worker service'

    def add_arguments(self, parser):
        parser.add_argument('--worker-name', default=None)
        parser.add_argument('--thread-pool-size', type=int, default=5)
        parser.add_argument('--concurrency', type=int, default=None)
        parser.add_argument(
            '--lease-seconds',
            type=int,
            default=None,
            help='覆盖配置管理中的 API 最大执行时间（秒）',
        )
        parser.add_argument('--poll-interval', type=int, default=3)
        parser.add_argument('--db-idle-seconds', type=int, default=1800)
        parser.add_argument('--config-refresh-interval', type=int, default=10)

    def handle(self, *args, **options):
        thread_pool_size = options['concurrency'] or options['thread_pool_size']
        try:
            ApiWorkerRunner(
                worker_name=options['worker_name'],
                thread_pool_size=thread_pool_size,
                lease_seconds=options['lease_seconds'],
                poll_interval=options['poll_interval'],
                db_idle_seconds=options['db_idle_seconds'],
                config_refresh_interval=options['config_refresh_interval'],
            ).run_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('api-worker 已停止'))

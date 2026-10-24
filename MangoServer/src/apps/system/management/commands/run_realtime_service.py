from django.core.management.base import BaseCommand, CommandError

from src.processes.realtime.runner import run_realtime_service


class Command(BaseCommand):
    help = "启动独立 realtime-service，承载 Web 与执行器 WebSocket 长连接"

    def add_arguments(self, parser):
        parser.add_argument("--host", default="0.0.0.0")
        parser.add_argument("--port", type=int, default=8011)
        parser.add_argument("--workers", type=int, default=1)

    def handle(self, *args, **options):
        if options["workers"] != 1:
            raise CommandError("realtime-service 当前只允许 workers=1")
        run_realtime_service(options["host"], options["port"], options["workers"])

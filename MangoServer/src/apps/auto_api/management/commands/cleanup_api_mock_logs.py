from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from src.apps.auto_api.services.mock.mock_log_cleanup import MockRequestLogCleanupService


class Command(BaseCommand):
    help = "清理超过保留期的 Mock 调用记录"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="保留天数，默认 7 天")
        parser.add_argument("--batch-size", type=int, default=1000, help="单批删除数量，默认 1000")

    def handle(self, *args, **options):
        days = options["days"]
        batch_size = options["batch_size"]
        if days < 1:
            raise CommandError("保留天数必须大于 0")
        if batch_size < 1 or batch_size > 10_000:
            raise CommandError("单批删除数量必须在 1 到 10000 之间")

        cutoff_time = timezone.now() - timedelta(days=days)
        deleted_count = MockRequestLogCleanupService.cleanup_before(
            cutoff_time,
            batch_size=batch_size,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Mock 调用记录清理完成：保留 {days} 天，删除 {deleted_count} 条"
            )
        )

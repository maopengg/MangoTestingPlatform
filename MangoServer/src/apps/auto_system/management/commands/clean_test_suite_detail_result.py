from django.core.management.base import BaseCommand

from src.apps.auto_system.service.test_suite.detail_result import TestSuiteDetailResultService


class Command(BaseCommand):
    help = 'Clean expired test_suite_detail_result records'

    def add_arguments(self, parser):
        parser.add_argument('--retention-days', type=int, default=TestSuiteDetailResultService.DEFAULT_RETENTION_DAYS)

    def handle(self, *args, **options):
        deleted = TestSuiteDetailResultService.clean_expired_results(
            retention_days=options['retention_days'],
        )
        self.stdout.write(self.style.SUCCESS(f'清理完成：{deleted} 条'))

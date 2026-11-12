import json

from django.core.management.base import BaseCommand, CommandError
from pydantic import ValidationError

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.recovery.limit_retirement import DatasourceLimitRetirementService


class Command(BaseCommand):
    help = '预览或在旧进程排空后退役操作限流配置；保留全部历史占用和审计，不执行业务SQL'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        try:
            result = DatasourceLimitRetirementService.run(apply=options['apply'])
        except DataFactoryError as error:
            raise CommandError(error.msg) from error
        except (ValidationError, KeyError, TypeError) as error:
            raise CommandError('配置或运行态结构不合法，未退役、未清空占用，请先核查') from error
        self.stdout.write(json.dumps(result, ensure_ascii=False))

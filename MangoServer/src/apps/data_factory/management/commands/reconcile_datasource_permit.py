import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from pydantic import ValidationError

from src.apps.data_factory.exceptions import DataFactoryError
from src.apps.data_factory.services.recovery.permit_reconciliation import DatasourcePermitReconciliationService


class Command(BaseCommand):
    help = '精确核查历史未知配额；默认仅预检。证据须来自独立核查，不接受按过期批量释放。'

    def add_arguments(self, parser):
        parser.add_argument('--group')
        parser.add_argument('--monitor', action='store_true', help='分页检查实例配额；不执行业务SQL、不核销占用')
        parser.add_argument('--recover-confirmed', action='store_true', help='与 --monitor 配合，只核销有可信终结证据的操作占用')
        parser.add_argument('--after-id', type=int, default=0, help='监控分页游标')
        parser.add_argument('--review-file', help='已核查的单项占用及证据摘要 JSON；不得包含凭据或业务数据')
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        import re
        group = options['group']
        if options.get('monitor', False):
            if group or options['apply'] or options['review_file'] or options['after_id'] < 0:
                raise CommandError('监控不能与单项核销参数混用，分页游标必须非负')
            result = DatasourcePermitReconciliationService.monitor(
                after_id=options['after_id'], recover=options['recover_confirmed'])
            self.stdout.write(json.dumps(result, ensure_ascii=False))
            return
        if options.get('recover_confirmed', False):
            raise CommandError('--recover-confirmed 必须与 --monitor 配合，不能代替单项人工核查')
        if not group or not re.fullmatch(r'[a-f0-9]{32}', group):
            raise CommandError('实例组必须为32位小写十六进制标识')
        if options['apply'] and not options['review_file']:
            raise CommandError('执行核销必须提供已核查的单项 review-file，不能批量清空配额')
        try:
            if options['review_file']:
                path = Path(options['review_file'])
                if path.stat().st_size > 16384:
                    raise CommandError('核查文件不得超过16KB')
                review = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(review, dict) or review.get('instance_group') != group:
                    raise CommandError('核查文件的实例组不匹配')
                result = DatasourcePermitReconciliationService.reconcile(review, apply=options['apply'])
            else:
                result = DatasourcePermitReconciliationService.inspect(group)
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
            raise CommandError('核查文件无法读取或结构不符合要求，未核销占用') from error
        except DataFactoryError as error:
            raise CommandError(error.msg) from error
        self.stdout.write(json.dumps(result, ensure_ascii=False))

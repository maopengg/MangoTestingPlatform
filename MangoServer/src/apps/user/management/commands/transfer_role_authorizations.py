import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from src.apps.user.exceptions import UserError
from src.apps.user.services.authorization.role_authorization_transfer import RoleAuthorizationTransferService


class Command(BaseCommand):
    help = '迁移前导出旧角色权限，迁移后校验或导入角色 JSON；不会生成/执行迁移或删除旧表。'

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument('--export', dest='export_path')
        mode.add_argument('--import', dest='import_path')
        parser.add_argument('--apply', action='store_true', help='显式执行导入；不传则仅校验。')

    def handle(self, *args, **options):
        try:
            if options['export_path']:
                if options['apply']:
                    raise CommandError('--apply 仅用于导入。')
                data = RoleAuthorizationTransferService.export_legacy()
                path = Path(options['export_path']).expanduser()
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
                    json.dump(data, output, ensure_ascii=False, indent=2)
                self.stdout.write(f'已导出 {len(data["roles"])} 个角色；请保管备份，确认导出成功后再执行表结构迁移。')
            else:
                with Path(options['import_path']).expanduser().open(encoding='utf-8') as source:
                    data = json.load(source)
                result = RoleAuthorizationTransferService.import_backup(data, apply=options['apply'])
                self.stdout.write(f'{"已导入" if options["apply"] else "仅校验"} {result["roles"]} 个角色，待变更 {result["pending"]} 个。')
        except UserError as error:
            raise CommandError(str(error)) from error
        except (OSError, json.JSONDecodeError) as error:
            raise CommandError('备份文件读写失败或 JSON 无效；导出文件不得覆盖已有文件，请检查路径。') from error

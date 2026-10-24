"""Convert existing user password hashes from single MD5 to double MD5.

Usage:
    python scripts/maintenance/migrate_user_password_to_double_md5.py --env dev
    python scripts/maintenance/migrate_user_password_to_double_md5.py --env dev --execute

The script must run exactly once per database. It cannot infer the hash layer for
arbitrary passwords. Execute mode writes a permission-restricted CSV backup
before updating rows in one transaction.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

def find_server_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "manage.py").exists():
            return parent
    raise RuntimeError("无法定位 MangoServer 目录")



def setup_django(env: str) -> None:
    os.environ['DJANGO_ENV'] = env
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
    server_dir = find_server_dir()
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))
    import django

    django.setup()


def md5(value: str) -> str:
    return hashlib.md5(value.encode('utf-8')).hexdigest()


def backup_path(env: str) -> Path:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return Path(__file__).resolve().parent / 'backups' / f'user_password_{env}_{timestamp}.csv'


def export_backup(users, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'username', 'password'])
        writer.writerows((user.id, user.username, user.password) for user in users)
    path.chmod(0o600)


def migrate(env: str, execute: bool) -> None:
    from django.db import transaction
    from src.apps.user.models import User

    users = list(User.objects.exclude(password='').order_by('id'))
    print(f'env={env}')
    print(f'affected_users={len(users)}')
    print(f'mode={"execute" if execute else "dry-run"}')
    if not execute:
        print('No data changed. Add --execute to apply this one-time migration.')
        return

    path = backup_path(env)
    export_backup(users, path)
    with transaction.atomic():
        locked_users = list(User.objects.select_for_update().exclude(password='').order_by('id'))
        for user in locked_users:
            user.password = md5(user.password)
        User.objects.bulk_update(locked_users, ['password'], batch_size=500)
    print(f'backup={path}')
    print(f'updated_users={len(locked_users)}')


def main() -> None:
    parser = argparse.ArgumentParser(description='用户密码单MD5升级为双MD5的一次性迁移脚本')
    parser.add_argument('--env', required=True, choices=('dev', 'test'))
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    setup_django(args.env)
    migrate(args.env, args.execute)


if __name__ == '__main__':
    main()

"""
Migrate FileData object keys from auto_test_report/test/ to mango-testing-platform/master/.

Usage:
    cd MangoServer
    python scripts/maintenance/migrate_filedata_test_to_master.py --env master
    python scripts/maintenance/migrate_filedata_test_to_master.py --env master --execute

The default mode is dry-run. When --execute is provided, the script:
1. Exports all affected rows to a CSV backup file.
2. Updates file_data.test_file and file_data.failed_screenshot in one transaction.

This script only updates database paths. It does not copy objects between buckets.
Make sure the same object keys exist in the target bucket before or after this step.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_OLD_PREFIX = "auto_test_report/test/"
DEFAULT_NEW_PREFIX = "mango-testing-platform/master/"
FIELDS = ("test_file", "failed_screenshot")

def find_server_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "manage.py").exists():
            return parent
    raise RuntimeError("无法定位 MangoServer 目录")



def setup_django(env: str) -> None:
    os.environ.setdefault("DJANGO_ENV", env)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings")

    server_dir = find_server_dir()
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    import django

    django.setup()


def make_backup_path(output_dir: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"file_data_path_backup_{timestamp}.csv"


def collect_rows(old_prefix: str):
    from src.apps.system.models import FileData

    query = FileData.objects.none()
    for field in FIELDS:
        query = query | FileData.objects.filter(**{f"{field}__startswith": old_prefix})
    return query.order_by("id")


def export_backup(rows, backup_path: Path) -> None:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with backup_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "test_file", "failed_screenshot"])
        for row in rows:
            writer.writerow([row.id, row.name, row.test_file.name, row.failed_screenshot.name])


def replace_prefix(value: str, old_prefix: str, new_prefix: str) -> str:
    if value.startswith(old_prefix):
        return f"{new_prefix}{value[len(old_prefix):]}"
    return value


def preview(rows, old_prefix: str, new_prefix: str) -> None:
    print(f"old_prefix={old_prefix}")
    print(f"new_prefix={new_prefix}")
    print(f"affected_rows={len(rows)}")

    field_counts = {field: 0 for field in FIELDS}
    for row in rows:
        for field in FIELDS:
            if getattr(row, field).name.startswith(old_prefix):
                field_counts[field] += 1
    for field, count in field_counts.items():
        print(f"{field}_affected={count}")

    print("\n-- sample --")
    for row in rows[:30]:
        before_after = {}
        for field in FIELDS:
            before = getattr(row, field).name
            after = replace_prefix(before, old_prefix, new_prefix)
            before_after[field] = (before, after)
        print(f"id={row.id}, name={row.name}")
        for field, (before, after) in before_after.items():
            if before != after:
                print(f"  {field}: {before} -> {after}")


def execute(rows, backup_dir: Path, old_prefix: str, new_prefix: str) -> None:
    from django.db import transaction

    backup_path = make_backup_path(backup_dir)
    export_backup(rows, backup_path)
    print(f"backup={backup_path}")

    updated_rows = 0
    updated_fields = 0
    with transaction.atomic():
        for row in rows:
            changed_fields = []
            for field in FIELDS:
                file_field = getattr(row, field)
                before = file_field.name
                after = replace_prefix(before, old_prefix, new_prefix)
                if before != after:
                    file_field.name = after
                    changed_fields.append(field)
            if changed_fields:
                row.save(update_fields=changed_fields)
                updated_rows += 1
                updated_fields += len(changed_fields)

    print(f"updated_rows={updated_rows}")
    print(f"updated_fields={updated_fields}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default="master", help="Django env, default: master")
    parser.add_argument("--execute", action="store_true", help="Apply database changes")
    parser.add_argument("--old-prefix", default=DEFAULT_OLD_PREFIX, help=f"Old object key prefix, default: {DEFAULT_OLD_PREFIX}")
    parser.add_argument("--new-prefix", default=DEFAULT_NEW_PREFIX, help=f"New object key prefix, default: {DEFAULT_NEW_PREFIX}")
    parser.add_argument(
        "--backup-dir",
        default=str(Path(__file__).resolve().parent / "backups"),
        help="CSV backup directory",
    )
    args = parser.parse_args()

    setup_django(args.env)
    old_prefix = args.old_prefix.strip("/")
    new_prefix = args.new_prefix.strip("/")
    old_prefix = f"{old_prefix}/" if old_prefix else ""
    new_prefix = f"{new_prefix}/" if new_prefix else ""
    rows = list(collect_rows(old_prefix))
    preview(rows, old_prefix, new_prefix)

    if not args.execute:
        print("\ndry_run=true")
        print("Run again with --execute to update database rows.")
        return

    execute(rows, Path(args.backup_dir), old_prefix, new_prefix)


if __name__ == "__main__":
    main()

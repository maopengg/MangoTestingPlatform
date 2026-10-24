"""Repair legacy datasource hierarchy data after the 7.1.1 model upgrade.

The default mode is dry-run. A real execution requires a unique backup prefix:

    python version_migration_scripts/v_7_1_1_2026_08_06_datasource_hierarchy_repair.py \
        --env test --backup-prefix datasource_hierarchy_backup_20260806 --execute

The repair performs four operations:
1. Move binding scope and permissions from TestObject to environment bindings.
2. Convert test-object-owned database rows into global datasource connections.
3. Merge byte-for-byte equivalent connection configurations.
4. Repoint historical references without changing execution result content.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


TARGET_VERSION = "7.1.1"
BACKUP_SOURCE_TABLES = (
    "data_base",
    "test_object",
    "data_factory_datasource_alias",
    "data_factory_datasource_binding",
    "data_factory_entity",
    "data_factory_execution_item",
    "gray_feature",
    "gray_execution_log",
)


def setup_django(env: str) -> None:
    os.environ["DJANGO_ENV"] = env
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings")
    server_dir = Path(__file__).resolve().parents[1]
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    import django

    django.setup()


def validate_backup_prefix(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,47}", value or ""):
        raise RuntimeError("--backup-prefix 只允许字母、数字和下划线，且必须以字母开头")
    return value


class DatasourceHierarchyRepair:
    def __init__(self, args) -> None:
        from django.conf import settings
        from src.apps.data_factory.models import (
            DataFactoryDatasourceBinding,
            DataFactoryExecutionItem,
        )
        from src.apps.gray_config.models import GrayExecutionLog, GrayFeature
        from src.apps.system.models import Database

        if settings.VERSION != TARGET_VERSION:
            raise RuntimeError(
                f"当前系统版本是 {settings.VERSION}，该脚本只允许在 {TARGET_VERSION} 执行"
            )
        self.args = args
        self.Database = Database
        self.Binding = DataFactoryDatasourceBinding
        self.ExecutionItem = DataFactoryExecutionItem
        self.GrayFeature = GrayFeature
        self.GrayExecutionLog = GrayExecutionLog

    @staticmethod
    def connection_identity(row) -> tuple:
        return (
            row.source_category,
            row.db_type,
            row.name,
            row.user,
            row.password,
            row.host,
            row.port,
            json.dumps(row.extra_config or {}, sort_keys=True, ensure_ascii=False),
        )

    def connection_groups(self) -> list[list]:
        groups = defaultdict(list)
        for row in self.Database.objects.select_related("test_object").order_by("id"):
            groups[self.connection_identity(row)].append(row)
        return list(groups.values())

    def build_plan(self) -> dict:
        binding_updates = []
        effective_scopes = set()
        for binding in self.Binding.objects.select_related("test_object", "datasource_alias"):
            environment = binding.environment
            read_status = binding.db_c_status
            write_status = binding.db_rud_status
            if environment is None:
                if not binding.test_object_id:
                    raise RuntimeError(f"绑定 {binding.id} 同时缺少 environment 和 test_object")
                if binding.test_object.project_product_id != binding.datasource_alias.project_product_id:
                    raise RuntimeError(f"绑定 {binding.id} 的测试对象与逻辑数据源不属于同一产品")
                environment = binding.test_object.environment
                read_status = binding.test_object.db_c_status
                write_status = binding.test_object.db_rud_status
            scope = (binding.datasource_alias_id, environment)
            if scope in effective_scopes:
                raise RuntimeError(
                    f"逻辑数据源 {binding.datasource_alias_id} 存在重复环境 {environment}，请人工确认"
                )
            effective_scopes.add(scope)
            binding_updates.append(
                {
                    "id": binding.id,
                    "environment": environment,
                    "db_c_status": read_status,
                    "db_rud_status": write_status,
                }
            )

        merge_map = {}
        for rows in self.connection_groups():
            canonical_id = rows[0].id
            for duplicate in rows[1:]:
                merge_map[duplicate.id] = canonical_id

        duplicate_ids = list(merge_map)
        return {
            "connections_before": self.Database.objects.count(),
            "connections_after": self.Database.objects.count() - len(duplicate_ids),
            "legacy_connections": self.Database.objects.filter(test_object__isnull=False).count(),
            "bindings": self.Binding.objects.count(),
            "legacy_bindings": self.Binding.objects.filter(environment__isnull=True).count(),
            "binding_updates": binding_updates,
            "merge_map": merge_map,
            "execution_item_references": self.ExecutionItem.objects.filter(
                database_id__in=duplicate_ids
            ).count(),
            "gray_feature_references": self.GrayFeature.objects.filter(
                database_id__in=duplicate_ids
            ).count(),
            "gray_log_references": self.GrayExecutionLog.objects.filter(
                database_id__in=duplicate_ids
            ).count(),
        }

    @staticmethod
    def print_plan(plan: dict) -> None:
        print(
            "[plan] "
            f"connections={plan['connections_before']}->{plan['connections_after']} "
            f"legacy_connections={plan['legacy_connections']} "
            f"bindings={plan['bindings']} legacy_bindings={plan['legacy_bindings']} "
            f"duplicate_connections={len(plan['merge_map'])} "
            f"execution_item_refs={plan['execution_item_references']} "
            f"gray_feature_refs={plan['gray_feature_references']} "
            f"gray_log_refs={plan['gray_log_references']}",
            flush=True,
        )
        permission_summary = defaultdict(int)
        for row in plan["binding_updates"]:
            permission_summary[(row["db_c_status"], row["db_rud_status"])] += 1
        print(f"[plan] binding_permissions={dict(permission_summary)}", flush=True)
        print(f"[plan] merge_map={plan['merge_map']}", flush=True)

    def create_backups(self, prefix: str) -> list[str]:
        from django.db import connection

        prefix = validate_backup_prefix(prefix)
        backup_tables = [f"{prefix}_{table}" for table in BACKUP_SOURCE_TABLES]
        if any(len(table) > 64 for table in backup_tables):
            raise RuntimeError("备份表名超过 MySQL 64 字符限制，请缩短 --backup-prefix")
        existing_tables = set(connection.introspection.table_names())
        conflicts = [table for table in backup_tables if table in existing_tables]
        if conflicts:
            raise RuntimeError(f"备份表已存在，拒绝覆盖：{conflicts}")

        with connection.cursor() as cursor:
            for source, target in zip(BACKUP_SOURCE_TABLES, backup_tables):
                cursor.execute(f"CREATE TABLE `{target}` LIKE `{source}`")
                cursor.execute(f"INSERT INTO `{target}` SELECT * FROM `{source}`")
                cursor.execute(f"SELECT COUNT(*) FROM `{target}`")
                count = cursor.fetchone()[0]
                print(f"[backup] {source} -> {target}, rows={count}", flush=True)
        return backup_tables

    def execute(self, plan: dict) -> None:
        from django.db import transaction

        with transaction.atomic():
            for row in plan["binding_updates"]:
                self.Binding.objects.filter(id=row["id"]).update(
                    environment=row["environment"],
                    test_object_id=None,
                    db_c_status=row["db_c_status"],
                    db_rud_status=row["db_rud_status"],
                )

            for duplicate_id, canonical_id in plan["merge_map"].items():
                self.Binding.objects.filter(database_id=duplicate_id).update(database_id=canonical_id)
                self.ExecutionItem.objects.filter(database_id=duplicate_id).update(
                    database_id=canonical_id
                )
                self.GrayFeature.objects.filter(database_id=duplicate_id).update(
                    database_id=canonical_id
                )
                self.GrayExecutionLog.objects.filter(database_id=duplicate_id).update(
                    database_id=canonical_id
                )

            for connection in self.Database.objects.filter(display_name="").only(
                "id", "name", "host", "port"
            ):
                connection.display_name = connection.name or f"{connection.host}:{connection.port}"
                connection.save(update_fields=["display_name"])

            self.Database.objects.update(test_object_id=None)
            self.Database.objects.filter(id__in=plan["merge_map"].keys()).delete()

        self.verify(plan)

    def verify(self, plan: dict) -> None:
        remaining_duplicates = [rows for rows in self.connection_groups() if len(rows) > 1]
        checks = {
            "connection_count": self.Database.objects.count() == plan["connections_after"],
            "legacy_connections": not self.Database.objects.filter(test_object__isnull=False).exists(),
            "legacy_bindings": not self.Binding.objects.filter(
                environment__isnull=True
            ).exists(),
            "binding_test_objects": not self.Binding.objects.filter(
                test_object__isnull=False
            ).exists(),
            "blank_display_names": not self.Database.objects.filter(display_name="").exists(),
            "duplicate_connections": not remaining_duplicates,
            "dangling_duplicate_references": not self.ExecutionItem.objects.filter(
                database_id__in=plan["merge_map"].keys()
            ).exists(),
        }
        print(f"[verify] {checks}", flush=True)
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise RuntimeError(f"修复后校验失败：{failed}")

    def run(self) -> None:
        plan = self.build_plan()
        self.print_plan(plan)
        if not self.args.execute:
            print("[dry-run] 未写入数据库；添加 --execute 后执行", flush=True)
            return
        if not self.args.backup_prefix:
            raise RuntimeError("正式执行必须提供 --backup-prefix")
        self.create_backups(self.args.backup_prefix)
        self.execute(plan)
        print("[done] 数据源层级历史数据修复完成", flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description="7.1.1 数据源层级历史数据修复")
    parser.add_argument("--env", default="dev")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--backup-prefix", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_django(args.env)
    DatasourceHierarchyRepair(args).run()


if __name__ == "__main__":
    main()

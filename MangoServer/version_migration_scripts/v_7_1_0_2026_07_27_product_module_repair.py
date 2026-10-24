"""
7.1.0 产品模块三级树修复。

常规用法必须显式提供修复前备份表：

    cd MangoServer
    python version_migration_scripts/v_7_1_0_2026_07_27_product_module_repair.py \
        --env test \
        --backup-table product_module_backup_yyyymmdd

确认 dry-run 输出后追加 --execute 才会写库。

2026-07-27 测试环境首次修复允许以 master 为旧模块数据源，但仍必须提供
测试库安全备份表：

    python version_migration_scripts/v_7_1_0_2026_07_27_product_module_repair.py \
        --env test \
        --master-source-once \
        --safety-backup-table product_module_backup_20260727_before_master_repair \
        --execute

master 特殊模式只允许修复尚未完成树迁移的数据；修复完成后再次执行必须改为
显式提供 --backup-table。

已经完成树迁移、但仍存在一级或二级叶子模块时，使用短路径修复模式：

    python version_migration_scripts/v_7_1_0_2026_07_27_product_module_repair.py \
        --env test \
        --backup-table product_module_backup_yyyymmdd_before_short_path_repair \
        --normalize-short-paths

确认 dry-run 后追加 --execute。该模式只修改 product_module：原模块 ID 保持不变，
一级叶子修复为“- / - / 原名称”，二级叶子修复为“原一级 / - / 原名称”。
脚本会在同一事务内校验所有外部业务引用快照完全不变。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any


TARGET_VERSION = "7.1.0"
TARGET_TABLE = "product_module"
MASTER_ALIAS = "product_module_repair_master"
IDENTIFIER_PATTERN = re.compile(r"[A-Za-z0-9_]+")
REQUIRED_SOURCE_COLUMNS = {
    "id",
    "create_time",
    "update_time",
    "project_product_id",
    "update_user_id",
    "name",
    "superior_module_1",
    "superior_module_2",
}
SNAPSHOT_COLUMNS = (
    "id",
    "create_time",
    "update_time",
    "project_product_id",
    "parent_id",
    "update_user_id",
    "name",
    "level",
    "sort",
    "superior_module_1",
    "superior_module_2",
)
PLACEHOLDER_NAME = "-"


def setup_django(env: str) -> None:
    os.environ["DJANGO_ENV"] = env
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.settings")

    server_dir = Path(__file__).resolve().parents[1]
    if str(server_dir) not in sys.path:
        sys.path.insert(0, str(server_dir))

    import django

    django.setup()


def normalized_name(value: Any) -> str:
    return str(value or "").strip()


def validate_table_name(value: str, option_name: str) -> str:
    value = normalized_name(value)
    if not value or not IDENTIFIER_PATTERN.fullmatch(value):
        raise RuntimeError(f"{option_name} 只允许字母、数字和下划线")
    if value == TARGET_TABLE:
        raise RuntimeError(f"{option_name} 不能直接指向 {TARGET_TABLE}")
    return value


def row_identity(row: dict[str, Any]) -> tuple:
    level_one = normalized_name(row.get("superior_module_1"))
    level_two = normalized_name(row.get("superior_module_2"))
    name = normalized_name(row.get("name"))
    product_id = row["project_product_id"]
    if not level_one and not level_two:
        return product_id, None, name
    if level_one and not level_two:
        return product_id, level_one, name
    return product_id, level_one, level_two, name


class ProductModuleRepair:
    def __init__(self, args):
        self.args = args

        from django.conf import settings

        self.settings = settings
        if settings.VERSION != TARGET_VERSION:
            raise RuntimeError(
                f"当前系统版本是 {settings.VERSION}，该脚本只允许在 {TARGET_VERSION} 执行"
            )
        self._assert_target_schema()

    @staticmethod
    def _quote(connection, name: str) -> str:
        return connection.ops.quote_name(name)

    @classmethod
    def _table_columns(cls, connection, table_name: str) -> list[str]:
        quoted = cls._quote(connection, table_name)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {quoted} LIMIT 0")
            return [item[0] for item in cursor.description]

    @classmethod
    def _read_rows(cls, connection, table_name: str) -> list[dict[str, Any]]:
        columns = cls._table_columns(connection, table_name)
        quoted_table = cls._quote(connection, table_name)
        selected = ", ".join(cls._quote(connection, column) for column in columns)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT {selected} FROM {quoted_table} ORDER BY id")
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _assert_target_schema(self) -> None:
        from django.db import connection

        columns = set(self._table_columns(connection, TARGET_TABLE))
        required = REQUIRED_SOURCE_COLUMNS | {"level", "parent_id", "sort"}
        missing = sorted(required - columns)
        if missing:
            raise RuntimeError(
                f"目标表 {TARGET_TABLE} 尚未完成结构迁移，缺少字段：{', '.join(missing)}"
            )

    def _master_connection(self):
        if self.args.env == "master":
            raise RuntimeError("目标环境为 master 时不能使用 --master-source-once")

        from django.db import connections
        from src.settings import master as master_settings

        if MASTER_ALIAS not in connections.databases:
            config = deepcopy(self.settings.DATABASES["default"])
            config.update(
                {
                    "NAME": master_settings.MYSQL_DB_NAME,
                    "USER": master_settings.MYSQL_USER,
                    "PASSWORD": master_settings.MYSQL_PASSWORD,
                    "HOST": master_settings.MYSQL_IP,
                    "PORT": master_settings.MYSQL_PORT,
                }
            )
            connections.databases[MASTER_ALIAS] = config
        return connections[MASTER_ALIAS]

    @staticmethod
    def _database_identity(connection) -> tuple[str, ...]:
        with connection.cursor() as cursor:
            try:
                cursor.execute("SELECT @@server_uuid, DATABASE()")
            except Exception:
                cursor.execute("SELECT @@hostname, @@port, DATABASE()")
            return tuple(normalized_name(value).lower() for value in cursor.fetchone())

    def _assert_distinct_master(self, master_connection) -> None:
        from django.db import connection

        if self._database_identity(connection) == self._database_identity(master_connection):
            raise RuntimeError("master 数据源与目标数据库相同，已拒绝执行")

    def _load_source_rows(self) -> tuple[list[dict[str, Any]], str]:
        from django.db import connection

        if self.args.master_source_once:
            master_connection = self._master_connection()
            self._assert_distinct_master(master_connection)
            rows = self._read_rows(master_connection, TARGET_TABLE)
            source_name = "master.product_module"
        else:
            table_name = validate_table_name(self.args.backup_table, "--backup-table")
            rows = self._read_rows(connection, table_name)
            source_name = table_name

        if not rows:
            raise RuntimeError(f"修复数据源 {source_name} 为空")
        missing = sorted(REQUIRED_SOURCE_COLUMNS - set(rows[0]))
        if missing:
            raise RuntimeError(
                f"修复数据源 {source_name} 缺少字段：{', '.join(missing)}"
            )
        ids = [row["id"] for row in rows]
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"修复数据源 {source_name} 存在重复主键")
        return rows, source_name

    def _assert_safety_backup(self, target_rows: list[dict[str, Any]]) -> None:
        if not self.args.master_source_once:
            return

        from django.db import connection

        table_name = validate_table_name(
            self.args.safety_backup_table,
            "--safety-backup-table",
        )
        backup_rows = self._read_rows(connection, table_name)
        if set(backup_rows[0]) != set(target_rows[0]):
            raise RuntimeError("安全备份表结构与当前 product_module 不一致")

        def snapshot(rows):
            return [
                tuple(row.get(column) for column in SNAPSHOT_COLUMNS)
                for row in rows
            ]

        if snapshot(backup_rows) != snapshot(target_rows):
            raise RuntimeError(
                "安全备份表与当前 product_module 内容不一致，"
                "请重新创建备份后再使用 master 特殊模式"
            )

    def _assert_backup_matches_target(
        self,
        backup_table: str,
        target_rows: list[dict[str, Any]],
    ) -> str:
        from django.db import connection

        table_name = validate_table_name(backup_table, "--backup-table")
        backup_rows = self._read_rows(connection, table_name)
        if not backup_rows:
            raise RuntimeError(f"备份表 {table_name} 为空")
        if set(backup_rows[0]) != set(target_rows[0]):
            raise RuntimeError("备份表结构与当前 product_module 不一致")
        if backup_rows != target_rows:
            raise RuntimeError(
                "备份表与当前 product_module 内容不一致，"
                "请重新备份当前模块表后再执行短路径修复"
            )
        return table_name

    @classmethod
    def _external_reference_snapshot(cls) -> list[tuple]:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT TABLE_NAME, COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = DATABASE()
                  AND REFERENCED_TABLE_NAME = %s
                  AND REFERENCED_COLUMN_NAME = 'id'
                  AND TABLE_NAME <> %s
                ORDER BY TABLE_NAME, COLUMN_NAME
                """,
                [TARGET_TABLE, TARGET_TABLE],
            )
            references = cursor.fetchall()

        snapshot = []
        for table_name, column_name in references:
            quoted_table = cls._quote(connection, table_name)
            quoted_column = cls._quote(connection, column_name)
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT {quoted_column}, COUNT(*)
                    FROM {quoted_table}
                    WHERE {quoted_column} IS NOT NULL
                    GROUP BY {quoted_column}
                    ORDER BY {quoted_column}
                    """
                )
                snapshot.extend(
                    (table_name, column_name, module_id, row_count)
                    for module_id, row_count in cursor.fetchall()
                )
        return snapshot

    @staticmethod
    def _tree_validation(
        rows: list[dict[str, Any]],
        require_complete_leaf_paths: bool,
        validate_superior_names: bool = True,
    ) -> dict[str, Any]:
        row_map = {row["id"]: row for row in rows}
        children = defaultdict(list)
        findings = []
        superior_name_mismatch_ids = []
        for row in rows:
            children[row.get("parent_id")].append(row)

        sibling_counts = Counter(
            (
                row["project_product_id"],
                row.get("parent_id"),
                normalized_name(row.get("name")),
            )
            for row in rows
        )
        for row in rows:
            module_id = row["id"]
            level = row.get("level")
            parent = row_map.get(row.get("parent_id"))
            name = normalized_name(row.get("name"))
            superior_one = normalized_name(row.get("superior_module_1"))
            superior_two = normalized_name(row.get("superior_module_2"))

            if not name:
                findings.append(f"模块 {module_id} 名称为空")
            if level not in (1, 2, 3):
                findings.append(f"模块 {module_id} 层级非法：{level}")
                continue
            if level == 1:
                if row.get("parent_id") is not None:
                    findings.append(f"一级模块 {module_id} 存在父节点")
                if superior_one or superior_two:
                    superior_name_mismatch_ids.append(module_id)
                    if validate_superior_names:
                        findings.append(f"一级模块 {module_id} 的上级名称字段不为空")
            else:
                if parent is None:
                    findings.append(f"模块 {module_id} 缺少父节点")
                elif parent["project_product_id"] != row["project_product_id"]:
                    findings.append(f"模块 {module_id} 与父节点不属于同一产品")
                elif parent.get("level") != level - 1:
                    findings.append(f"模块 {module_id} 与父节点层级不连续")
                elif level == 2:
                    if superior_one != normalized_name(parent.get("name")) or superior_two:
                        superior_name_mismatch_ids.append(module_id)
                        if validate_superior_names:
                            findings.append(f"二级模块 {module_id} 的上级名称字段不正确")
                else:
                    grandparent = row_map.get(parent.get("parent_id"))
                    if grandparent is None:
                        findings.append(f"三级模块 {module_id} 缺少一级祖先")
                    elif (
                        superior_one != normalized_name(grandparent.get("name"))
                        or superior_two != normalized_name(parent.get("name"))
                    ):
                        superior_name_mismatch_ids.append(module_id)
                        if validate_superior_names:
                            findings.append(f"三级模块 {module_id} 的上级名称字段不正确")

            if level == 3 and children.get(module_id):
                findings.append(f"三级模块 {module_id} 仍存在子节点")
            if sibling_counts[
                (
                    row["project_product_id"],
                    row.get("parent_id"),
                    name,
                )
            ] > 1:
                findings.append(f"模块 {module_id} 与同级节点重名")

        short_level_one_ids = sorted(
            row["id"]
            for row in rows
            if row.get("level") == 1 and not children.get(row["id"])
        )
        short_level_two_ids = sorted(
            row["id"]
            for row in rows
            if row.get("level") == 2 and not children.get(row["id"])
        )
        if require_complete_leaf_paths and (
            short_level_one_ids or short_level_two_ids
        ):
            findings.append(
                "仍存在非三级叶子模块："
                + ", ".join(
                    map(str, (short_level_one_ids + short_level_two_ids)[:30])
                )
            )

        return {
            "passed": not findings,
            "findings": findings,
            "short_level_one_ids": short_level_one_ids,
            "short_level_two_ids": short_level_two_ids,
            "superior_name_mismatch_ids": sorted(
                set(superior_name_mismatch_ids)
            ),
            "level_counts": dict(Counter(row.get("level") for row in rows)),
        }

    def build_short_path_plan(self) -> dict[str, Any]:
        from django.db import connection

        target_rows = self._read_rows(connection, TARGET_TABLE)
        backup_table = self._assert_backup_matches_target(
            self.args.backup_table,
            target_rows,
        )
        validation = self._tree_validation(
            target_rows,
            require_complete_leaf_paths=False,
            validate_superior_names=False,
        )
        if not validation["passed"]:
            raise RuntimeError(
                "当前模块树结构预检失败：" + "；".join(validation["findings"][:20])
            )

        row_map = {row["id"]: row for row in target_rows}
        short_level_one = [
            row_map[module_id] for module_id in validation["short_level_one_ids"]
        ]
        short_level_two = [
            row_map[module_id] for module_id in validation["short_level_two_ids"]
        ]
        placeholder_leaf_ids = sorted(
            row["id"]
            for row in short_level_one + short_level_two
            if normalized_name(row.get("name")) == PLACEHOLDER_NAME
        )
        if placeholder_leaf_ids:
            raise RuntimeError(
                "现有“-”模块本身是短路径叶子，需人工确认后再修复："
                + ", ".join(map(str, placeholder_leaf_ids))
            )

        sibling_map = defaultdict(list)
        for row in target_rows:
            sibling_map[
                (
                    row["project_product_id"],
                    row.get("parent_id"),
                    normalized_name(row.get("name")),
                )
            ].append(row)

        level_one_products = sorted(
            {row["project_product_id"] for row in short_level_one}
        )
        level_two_parent_ids = sorted(
            {row["parent_id"] for row in short_level_two}
        )
        new_root_count = 0
        new_level_two_count = 0
        planned_parent_keys = {}

        for product_id in level_one_products:
            roots = sibling_map[(product_id, None, PLACEHOLDER_NAME)]
            if len(roots) > 1:
                raise RuntimeError(f"项目产品 {product_id} 存在多个“-”一级模块")
            if roots:
                root = roots[0]
                level_two_nodes = sibling_map[
                    (product_id, root["id"], PLACEHOLDER_NAME)
                ]
                if len(level_two_nodes) > 1:
                    raise RuntimeError(
                        f"项目产品 {product_id} 的“-”一级下存在多个“-”二级模块"
                    )
                if level_two_nodes:
                    planned_parent_keys[("level_one", product_id)] = (
                        "existing",
                        level_two_nodes[0]["id"],
                    )
                else:
                    new_level_two_count += 1
                    planned_parent_keys[("level_one", product_id)] = (
                        "new",
                        f"product:{product_id}:dash-level-two",
                    )
            else:
                new_root_count += 1
                new_level_two_count += 1
                planned_parent_keys[("level_one", product_id)] = (
                    "new",
                    f"product:{product_id}:dash-level-two",
                )

        for parent_id in level_two_parent_ids:
            parent = row_map[parent_id]
            level_two_nodes = sibling_map[
                (
                    parent["project_product_id"],
                    parent_id,
                    PLACEHOLDER_NAME,
                )
            ]
            if len(level_two_nodes) > 1:
                raise RuntimeError(f"一级模块 {parent_id} 下存在多个“-”二级模块")
            if level_two_nodes:
                planned_parent_keys[("level_two", parent_id)] = (
                    "existing",
                    level_two_nodes[0]["id"],
                )
            else:
                new_level_two_count += 1
                planned_parent_keys[("level_two", parent_id)] = (
                    "new",
                    f"parent:{parent_id}:dash-level-two",
                )

        target_names = Counter()
        for row in short_level_one:
            target_names[
                (
                    row["project_product_id"],
                    planned_parent_keys[
                        ("level_one", row["project_product_id"])
                    ],
                    normalized_name(row["name"]),
                )
            ] += 1
        for row in short_level_two:
            target_names[
                (
                    row["project_product_id"],
                    planned_parent_keys[("level_two", row["parent_id"])],
                    normalized_name(row["name"]),
                )
            ] += 1
        duplicate_targets = [key for key, count in target_names.items() if count > 1]
        if duplicate_targets:
            raise RuntimeError("短路径下沉后存在同级重名冲突")

        candidate_ids = {
            row["id"] for row in short_level_one + short_level_two
        }
        reference_snapshot = self._external_reference_snapshot()
        reference_total = sum(
            row_count
            for _, _, module_id, row_count in reference_snapshot
            if module_id in candidate_ids
        )
        affected_product_ids = sorted(
            {row["project_product_id"] for row in short_level_one + short_level_two}
        )
        return {
            "backup_table": backup_table,
            "target_rows": target_rows,
            "before_validation": validation,
            "short_level_one_ids": validation["short_level_one_ids"],
            "short_level_two_ids": validation["short_level_two_ids"],
            "candidate_ids": sorted(candidate_ids),
            "affected_product_ids": affected_product_ids,
            "new_root_count": new_root_count,
            "new_level_two_count": new_level_two_count,
            "expected_final_count": (
                len(target_rows) + new_root_count + new_level_two_count
            ),
            "reference_snapshot": reference_snapshot,
            "candidate_reference_total": reference_total,
            "superior_name_mismatch_ids": validation[
                "superior_name_mismatch_ids"
            ],
        }

    @staticmethod
    def _print_short_path_plan(plan: dict[str, Any], execute: bool) -> None:
        before_counts = plan["before_validation"]["level_counts"]
        output = {
            "mode": "execute" if execute else "dry-run",
            "operation": "normalize-short-paths",
            "backup_table": plan["backup_table"],
            "current_count": len(plan["target_rows"]),
            "current_level_counts": {
                "level_1": before_counts.get(1, 0),
                "level_2": before_counts.get(2, 0),
                "level_3": before_counts.get(3, 0),
            },
            "short_level_one_count": len(plan["short_level_one_ids"]),
            "short_level_two_count": len(plan["short_level_two_ids"]),
            "candidate_count": len(plan["candidate_ids"]),
            "candidate_reference_total": plan["candidate_reference_total"],
            "superior_name_mismatch_count": len(
                plan["superior_name_mismatch_ids"]
            ),
            "new_root_placeholder_count": plan["new_root_count"],
            "new_level_two_placeholder_count": plan["new_level_two_count"],
            "expected_final_count": plan["expected_final_count"],
            "affected_product_ids": plan["affected_product_ids"],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2), flush=True)

    @staticmethod
    def _execute_short_path_plan(plan: dict[str, Any]) -> dict[str, Any]:
        from src.apps.test_center.models import ProductModule

        modules = {
            item.id: item
            for item in ProductModule.objects.select_related("parent").all()
        }
        created_root_ids = []
        created_level_two_ids = []
        level_one_parent_by_product = {}
        level_two_parent_by_root = {}

        for module_id in plan["short_level_one_ids"]:
            item = modules[module_id]
            product_id = item.project_product_id
            if product_id in level_one_parent_by_product:
                continue
            roots = list(
                ProductModule.objects.filter(
                    project_product_id=product_id,
                    parent_id__isnull=True,
                    name=PLACEHOLDER_NAME,
                )
            )
            if len(roots) > 1:
                raise RuntimeError(f"项目产品 {product_id} 存在多个“-”一级模块")
            if roots:
                root = roots[0]
            else:
                root = ProductModule.objects.create(
                    project_product_id=product_id,
                    parent_id=None,
                    name=PLACEHOLDER_NAME,
                    level=1,
                    sort=0,
                    superior_module_1=None,
                    superior_module_2=None,
                )
                created_root_ids.append(root.id)

            level_two_nodes = list(
                ProductModule.objects.filter(
                    project_product_id=product_id,
                    parent_id=root.id,
                    name=PLACEHOLDER_NAME,
                )
            )
            if len(level_two_nodes) > 1:
                raise RuntimeError(
                    f"项目产品 {product_id} 的“-”一级下存在多个“-”二级模块"
                )
            if level_two_nodes:
                level_two = level_two_nodes[0]
            else:
                level_two = ProductModule.objects.create(
                    project_product_id=product_id,
                    parent_id=root.id,
                    name=PLACEHOLDER_NAME,
                    level=2,
                    sort=0,
                    superior_module_1=PLACEHOLDER_NAME,
                    superior_module_2=None,
                )
                created_level_two_ids.append(level_two.id)
            level_one_parent_by_product[product_id] = level_two

        for module_id in plan["short_level_two_ids"]:
            item = modules[module_id]
            root = modules[item.parent_id]
            if root.id in level_two_parent_by_root:
                continue
            level_two_nodes = list(
                ProductModule.objects.filter(
                    project_product_id=item.project_product_id,
                    parent_id=root.id,
                    name=PLACEHOLDER_NAME,
                )
            )
            if len(level_two_nodes) > 1:
                raise RuntimeError(f"一级模块 {root.id} 下存在多个“-”二级模块")
            if level_two_nodes:
                level_two = level_two_nodes[0]
            else:
                level_two = ProductModule.objects.create(
                    project_product_id=item.project_product_id,
                    parent_id=root.id,
                    name=PLACEHOLDER_NAME,
                    level=2,
                    sort=0,
                    superior_module_1=root.name,
                    superior_module_2=None,
                )
                created_level_two_ids.append(level_two.id)
            level_two_parent_by_root[root.id] = level_two

        for module_id in plan["short_level_one_ids"]:
            item = modules[module_id]
            parent = level_one_parent_by_product[item.project_product_id]
            ProductModule.objects.filter(id=module_id).update(
                parent_id=parent.id,
                level=3,
                superior_module_1=PLACEHOLDER_NAME,
                superior_module_2=PLACEHOLDER_NAME,
            )

        for module_id in plan["short_level_two_ids"]:
            item = modules[module_id]
            root = modules[item.parent_id]
            parent = level_two_parent_by_root[root.id]
            ProductModule.objects.filter(id=module_id).update(
                parent_id=parent.id,
                level=3,
                superior_module_1=root.name,
                superior_module_2=PLACEHOLDER_NAME,
            )

        synced_superior_name_ids = ProductModuleRepair._sync_superior_names()
        return {
            "updated_module_ids": plan["candidate_ids"],
            "created_root_ids": created_root_ids,
            "created_level_two_ids": created_level_two_ids,
            "synced_superior_name_ids": synced_superior_name_ids,
        }

    @staticmethod
    def _sync_superior_names() -> list[int]:
        from src.apps.test_center.models import ProductModule

        changed_ids = []
        modules = list(
            ProductModule.objects.select_related("parent__parent").order_by("id")
        )
        for item in modules:
            if item.level == 1:
                superior_one = None
                superior_two = None
            elif item.level == 2:
                if item.parent is None:
                    raise RuntimeError(f"二级模块 {item.id} 缺少父节点")
                superior_one = item.parent.name
                superior_two = None
            elif item.level == 3:
                if item.parent is None or item.parent.parent is None:
                    raise RuntimeError(f"三级模块 {item.id} 缺少完整父节点")
                superior_one = item.parent.parent.name
                superior_two = item.parent.name
            else:
                raise RuntimeError(f"模块 {item.id} 层级非法：{item.level}")

            if (
                normalized_name(item.superior_module_1)
                == normalized_name(superior_one)
                and normalized_name(item.superior_module_2)
                == normalized_name(superior_two)
            ):
                continue
            ProductModule.objects.filter(id=item.id).update(
                superior_module_1=superior_one,
                superior_module_2=superior_two,
            )
            changed_ids.append(item.id)
        return changed_ids

    def _verify_short_path_repair(
        self,
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        from django.db import connection

        final_rows = self._read_rows(connection, TARGET_TABLE)
        final_validation = self._tree_validation(
            final_rows,
            require_complete_leaf_paths=True,
        )
        if not final_validation["passed"]:
            raise RuntimeError(
                "短路径修复后结构校验失败："
                + "；".join(final_validation["findings"][:20])
            )
        if len(final_rows) != plan["expected_final_count"]:
            raise RuntimeError(
                f"修复后模块总数异常：expected={plan['expected_final_count']}, "
                f"actual={len(final_rows)}"
            )

        final_ids = {row["id"] for row in final_rows}
        missing_original_ids = sorted(
            set(plan["candidate_ids"]) - final_ids
        )
        if missing_original_ids:
            raise RuntimeError(
                "修复后缺少原模块ID：" + ", ".join(map(str, missing_original_ids))
            )

        final_reference_snapshot = self._external_reference_snapshot()
        if final_reference_snapshot != plan["reference_snapshot"]:
            raise RuntimeError("修复前后业务引用快照不一致，事务已回滚")

        final_counts = final_validation["level_counts"]
        return {
            "final_count": len(final_rows),
            "level_1_count": final_counts.get(1, 0),
            "level_2_count": final_counts.get(2, 0),
            "level_3_count": final_counts.get(3, 0),
            "short_level_one_count": len(
                final_validation["short_level_one_ids"]
            ),
            "short_level_two_count": len(
                final_validation["short_level_two_ids"]
            ),
            "preserved_original_module_count": len(plan["candidate_ids"]),
            "preserved_external_reference_count": plan[
                "candidate_reference_total"
            ],
        }

    @staticmethod
    def _overlay_source(
        source_rows: list[dict[str, Any]],
        target_rows: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        source_map = {row["id"]: row for row in source_rows}
        target_map = {row["id"]: row for row in target_rows}
        common_ids = sorted(source_map.keys() & target_map.keys())
        source_only_ids = sorted(source_map.keys() - target_map.keys())
        target_only_ids = sorted(target_map.keys() - source_map.keys())
        copied_columns = (
            "create_time",
            "update_time",
            "project_product_id",
            "update_user_id",
            "name",
            "superior_module_1",
            "superior_module_2",
        )
        compared_columns = (
            "project_product_id",
            "name",
            "superior_module_1",
            "superior_module_2",
        )
        changed_ids = []
        effective_map = deepcopy(target_map)

        for module_id in common_ids:
            source = source_map[module_id]
            target = effective_map[module_id]
            if any(target.get(column) != source.get(column) for column in compared_columns):
                changed_ids.append(module_id)
            for column in copied_columns:
                target[column] = source.get(column)
            if "sort" in source:
                target["sort"] = source.get("sort") or 0

        for module_id in source_only_ids:
            source = source_map[module_id]
            effective_map[module_id] = {
                **source,
                "parent_id": None,
                "level": None,
                "sort": source.get("sort") or 0,
            }

        return [effective_map[module_id] for module_id in sorted(effective_map)], {
            "source_count": len(source_rows),
            "target_count": len(target_rows),
            "common_count": len(common_ids),
            "common_ids": common_ids,
            "source_only_ids": source_only_ids,
            "target_only_ids": target_only_ids,
            "changed_ids": changed_ids,
        }

    @staticmethod
    def _validate_effective_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
        findings = []
        invalid_path_ids = [
            row["id"]
            for row in rows
            if not normalized_name(row.get("superior_module_1"))
            and normalized_name(row.get("superior_module_2"))
        ]
        if invalid_path_ids:
            findings.append(
                "存在只有二级旧路径的模块："
                + ", ".join(map(str, invalid_path_ids[:20]))
            )

        identities = Counter(row_identity(row) for row in rows)
        duplicates = [identity for identity, count in identities.items() if count > 1]
        if duplicates:
            findings.append(
                "迁移后同一父节点下存在重名模块："
                + "；".join(
                    " / ".join(str(part) for part in identity if part is not None)
                    for identity in duplicates[:20]
                )
            )

        root_candidates = {}
        level_two_candidates = {}
        required_roots = set()
        required_level_two = set()
        for row in rows:
            product_id = row["project_product_id"]
            name = normalized_name(row.get("name"))
            level_one = normalized_name(row.get("superior_module_1"))
            level_two = normalized_name(row.get("superior_module_2"))
            if not name:
                findings.append(f"模块 {row['id']} 名称为空")
                continue
            if not level_one and not level_two:
                root_candidates[(product_id, name)] = row["id"]
            elif level_one and not level_two:
                level_two_candidates[(product_id, level_one, name)] = row["id"]
            if level_one:
                required_roots.add((product_id, level_one))
            if level_one and level_two:
                required_level_two.add((product_id, level_one, level_two))

        return {
            "passed": not findings,
            "findings": findings,
            "root_candidates": root_candidates,
            "level_two_candidates": level_two_candidates,
            "required_roots": required_roots,
            "required_level_two": required_level_two,
            "new_parent_estimate": (
                len(required_roots - set(root_candidates))
                + len(required_level_two - set(level_two_candidates))
            ),
        }

    @staticmethod
    def _validate_target_foreign_keys(rows: list[dict[str, Any]]) -> None:
        from src.apps.system.models import ProjectProduct
        from src.apps.user.models import User

        product_ids = {row["project_product_id"] for row in rows}
        existing_products = set(
            ProjectProduct.objects.filter(id__in=product_ids).values_list("id", flat=True)
        )
        missing_products = sorted(product_ids - existing_products)
        if missing_products:
            raise RuntimeError(
                "目标库缺少修复数据引用的项目产品："
                + ", ".join(map(str, missing_products))
            )

        user_ids = {row.get("update_user_id") for row in rows if row.get("update_user_id")}
        existing_users = set(
            User.objects.filter(id__in=user_ids).values_list("id", flat=True)
        )
        missing_users = sorted(user_ids - existing_users)
        if missing_users:
            raise RuntimeError(
                "目标库缺少修复数据引用的更新人："
                + ", ".join(map(str, missing_users))
            )

    def build_plan(self) -> dict[str, Any]:
        from django.db import connection

        target_rows = self._read_rows(connection, TARGET_TABLE)
        self._assert_safety_backup(target_rows)
        source_rows, source_name = self._load_source_rows()
        effective_rows, diff = self._overlay_source(source_rows, target_rows)
        validation = self._validate_effective_rows(effective_rows)
        self._validate_target_foreign_keys(effective_rows)

        null_level_count = sum(row.get("level") is None for row in target_rows)
        parent_count = sum(row.get("parent_id") is not None for row in target_rows)
        if not null_level_count or parent_count:
            raise RuntimeError(
                "目标表不再是可安全自动修复的初始/部分迁移状态。"
                "本脚本不会拆除已有模块树；请提供修复前备份并另行核对。"
            )
        if not validation["passed"]:
            raise RuntimeError("产品模块修复预检失败：" + "；".join(validation["findings"]))

        return {
            "source": source_name,
            "source_rows": source_rows,
            "effective_rows": effective_rows,
            "diff": diff,
            "validation": validation,
            "target_null_level_count": null_level_count,
            "target_parent_count": parent_count,
        }

    @staticmethod
    def _print_plan(plan: dict[str, Any], execute: bool) -> None:
        diff = plan["diff"]
        validation = plan["validation"]
        output = {
            "mode": "execute" if execute else "dry-run",
            "source": plan["source"],
            "source_count": diff["source_count"],
            "target_count": diff["target_count"],
            "common_count": diff["common_count"],
            "source_only_ids": diff["source_only_ids"],
            "target_only_ids_preserved": diff["target_only_ids"],
            "source_changed_ids": diff["changed_ids"],
            "current_null_level_count": plan["target_null_level_count"],
            "current_parent_count": plan["target_parent_count"],
            "required_root_count": len(validation["required_roots"]),
            "required_level_two_count": len(validation["required_level_two"]),
            "new_parent_estimate": validation["new_parent_estimate"],
            "expected_final_count": (
                len(plan["effective_rows"]) + validation["new_parent_estimate"]
            ),
        }
        print(json.dumps(output, ensure_ascii=False, default=str, indent=2), flush=True)

    @staticmethod
    def _insert_missing_source_rows(plan: dict[str, Any]) -> None:
        from django.db import connection

        source_map = {row["id"]: row for row in plan["source_rows"]}
        missing_ids = plan["diff"]["source_only_ids"]
        if not missing_ids:
            return
        sql = (
            "INSERT INTO product_module "
            "(id, create_time, update_time, project_product_id, parent_id, "
            "update_user_id, name, level, sort, superior_module_1, superior_module_2) "
            "VALUES (%s, %s, %s, %s, NULL, %s, %s, NULL, %s, %s, %s)"
        )
        with connection.cursor() as cursor:
            cursor.executemany(
                sql,
                [
                    (
                        row["id"],
                        row["create_time"],
                        row["update_time"],
                        row["project_product_id"],
                        row.get("update_user_id"),
                        row["name"],
                        row.get("sort") or 0,
                        row.get("superior_module_1"),
                        row.get("superior_module_2"),
                    )
                    for row in (source_map[module_id] for module_id in missing_ids)
                ],
            )

    @staticmethod
    def _restore_source_columns(plan: dict[str, Any]) -> None:
        from src.apps.test_center.models import ProductModule

        source_map = {row["id"]: row for row in plan["source_rows"]}
        for module_id in plan["diff"]["common_ids"]:
            row = source_map[module_id]
            values = {
                "create_time": row["create_time"],
                "update_time": row["update_time"],
                "project_product_id": row["project_product_id"],
                "update_user_id": row.get("update_user_id"),
                "name": row["name"],
                "superior_module_1": row.get("superior_module_1"),
                "superior_module_2": row.get("superior_module_2"),
                "parent_id": None,
                "level": None,
            }
            if "sort" in row:
                values["sort"] = row.get("sort") or 0
            ProductModule.objects.filter(id=module_id).update(**values)

    @staticmethod
    def _build_hierarchy() -> dict[str, int]:
        from src.apps.test_center.models import ProductModule

        modules = list(ProductModule.objects.order_by("project_product_id", "id"))
        validation = ProductModuleRepair._validate_effective_rows(
            [
                {
                    "id": item.id,
                    "project_product_id": item.project_product_id,
                    "name": item.name,
                    "superior_module_1": item.superior_module_1,
                    "superior_module_2": item.superior_module_2,
                }
                for item in modules
            ]
        )
        if not validation["passed"]:
            raise RuntimeError("写入前二次预检失败：" + "；".join(validation["findings"]))

        module_map = {item.id: item for item in modules}
        roots = {
            key: module_map[module_id]
            for key, module_id in validation["root_candidates"].items()
        }
        created_roots = 0
        for product_id, name in sorted(validation["required_roots"]):
            key = (product_id, name)
            if key not in roots:
                roots[key] = ProductModule.objects.create(
                    project_product_id=product_id,
                    parent=None,
                    name=name,
                    level=1,
                    sort=0,
                )
                created_roots += 1

        level_two_nodes = {
            key: module_map[module_id]
            for key, module_id in validation["level_two_candidates"].items()
        }
        created_level_two = 0
        for product_id, level_one, level_two in sorted(
            validation["required_level_two"]
        ):
            key = (product_id, level_one, level_two)
            if key not in level_two_nodes:
                level_two_nodes[key] = ProductModule.objects.create(
                    project_product_id=product_id,
                    parent=roots[(product_id, level_one)],
                    name=level_two,
                    level=2,
                    sort=0,
                )
                created_level_two += 1

        for item in modules:
            level_one = normalized_name(item.superior_module_1)
            level_two = normalized_name(item.superior_module_2)
            if not level_one:
                parent_id, level = None, 1
            elif not level_two:
                parent_id, level = roots[(item.project_product_id, level_one)].id, 2
            else:
                parent_id = level_two_nodes[
                    (item.project_product_id, level_one, level_two)
                ].id
                level = 3
            if parent_id == item.id:
                raise RuntimeError(f"模块 {item.id} 修复后会成为自己的父节点")
            ProductModule.objects.filter(id=item.id).update(
                parent_id=parent_id,
                level=level,
            )

        return {
            "original_module_count": len(modules),
            "created_root_count": created_roots,
            "created_level_two_count": created_level_two,
            "updated_module_count": len(modules),
        }

    @staticmethod
    def _verify() -> dict[str, int]:
        from django.db.models import F, Q
        from src.apps.test_center.models import ProductModule

        null_level_count = ProductModule.objects.filter(level__isnull=True).count()
        invalid_root_count = ProductModule.objects.filter(
            Q(level=1, parent_id__isnull=False)
            | Q(level__in=(2, 3), parent_id__isnull=True)
        ).count()
        invalid_parent_count = ProductModule.objects.filter(
            parent_id__isnull=False
        ).exclude(
            project_product_id=F("parent__project_product_id"),
            level=F("parent__level") + 1,
        ).count()
        if null_level_count or invalid_root_count or invalid_parent_count:
            raise RuntimeError(
                "修复后校验失败："
                f"null_level={null_level_count}, "
                f"invalid_root={invalid_root_count}, "
                f"invalid_parent={invalid_parent_count}"
            )
        return {
            "final_count": ProductModule.objects.count(),
            "null_level_count": null_level_count,
            "invalid_root_count": invalid_root_count,
            "invalid_parent_count": invalid_parent_count,
        }

    def run(self) -> None:
        if self.args.normalize_short_paths:
            plan = self.build_short_path_plan()
            self._print_short_path_plan(plan, self.args.execute)
            if not self.args.execute:
                print("No data changed. Add --execute to write data.", flush=True)
                return

            from django.db import transaction
            from src.apps.test_center.services.product_module_cache import (
                ProductModuleCacheService,
            )

            with transaction.atomic():
                stats = self._execute_short_path_plan(plan)
                verification = self._verify_short_path_repair(plan)
            ProductModuleCacheService.invalidate_many(
                plan["affected_product_ids"]
            )
            print(
                json.dumps(
                    {
                        "repair": stats,
                        "verification": verification,
                        "invalidated_product_module_cache_ids": plan[
                            "affected_product_ids"
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                flush=True,
            )
            return

        plan = self.build_plan()
        self._print_plan(plan, self.args.execute)
        if not self.args.execute:
            print("No data changed. Add --execute to write data.", flush=True)
            return

        from django.db import transaction
        from src.apps.test_center.models import ProductModule

        with transaction.atomic():
            ProductModule.objects.update(parent_id=None, level=None)
            self._insert_missing_source_rows(plan)
            self._restore_source_columns(plan)
            stats = self._build_hierarchy()
            verification = self._verify()
        print(
            json.dumps(
                {"repair": stats, "verification": verification},
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )


def parse_args():
    parser = argparse.ArgumentParser(description="7.1.0 产品模块三级树修复")
    parser.add_argument("--env", required=True, choices=("dev", "test", "master"))
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--backup-table",
        help="常规修复的数据源备份表；必须由用户显式提供表名。",
    )
    source_group.add_argument(
        "--master-source-once",
        action="store_true",
        help="仅用于本次测试环境特殊修复，从 master 读取旧模块数据。",
    )
    parser.add_argument(
        "--safety-backup-table",
        help="master 特殊模式必填，必须与执行前目标 product_module 完全一致。",
    )
    parser.add_argument(
        "--normalize-short-paths",
        action="store_true",
        help=(
            "只修复当前 product_module 中的一级/二级叶子模块；"
            "必须通过 --backup-table 提供与当前表完全一致的安全备份。"
        ),
    )
    parser.add_argument("--execute", action="store_true", help="实际写入数据库。")
    args = parser.parse_args()
    if args.master_source_once and not args.safety_backup_table:
        parser.error("--master-source-once 必须同时提供 --safety-backup-table")
    if not args.master_source_once and args.safety_backup_table:
        parser.error("--safety-backup-table 仅与 --master-source-once 配合使用")
    if args.normalize_short_paths and args.master_source_once:
        parser.error("--normalize-short-paths 只能与 --backup-table 配合使用")
    return args


def main() -> None:
    args = parse_args()
    setup_django(args.env)
    ProductModuleRepair(args).run()


if __name__ == "__main__":
    main()

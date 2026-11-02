"""清理 master 数据库中未绑定 API case 的重复接口定义。

重复键：项目产品、模块、URL、请求方法、协议类型、端类型。

本脚本不导入 Django。它通过 AST 读取 ``src/settings/master.py`` 中的
MySQL 配置，并使用 PyMySQL 直接访问数据库。

右键运行：
    直接运行本文件，检查预览后按提示输入确认词。

命令行：
    python scripts/maintenance/cleanup_duplicate_api_info.py --dry-run
    python scripts/maintenance/cleanup_duplicate_api_info.py --yes

删除前会将全部候选及处理结果写入 ``scripts/maintenance/backups``。存在 API case 绑定的
接口会跳过；其他外键关联导致的删除失败会记录并继续处理下一条。
"""

from __future__ import annotations

import argparse
import ast
import csv
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pymysql
from pymysql.cursors import DictCursor


def find_server_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "manage.py").exists():
            return parent
    raise RuntimeError("无法定位 MangoServer 目录")


SERVER_DIR = find_server_dir()
MASTER_SETTINGS_PATH = SERVER_DIR / "src" / "settings" / "master.py"
BACKUP_DIR = Path(__file__).resolve().parent / "backups"
CONFIG_NAMES = {
    "MYSQL_DB_NAME",
    "MYSQL_USER",
    "MYSQL_PASSWORD",
    "MYSQL_IP",
    "MYSQL_PORT",
}
CONFIRM_PREFIX = "DELETE"

DUPLICATE_QUERY = """
SELECT
    ai.id,
    ai.project_product_id,
    CONCAT(p.name, '/', pp.name) AS project_product_name,
    ai.module_id,
    CONCAT_WS('/',
        NULLIF(pm.superior_module_1, ''),
        CASE
            WHEN NULLIF(pm.superior_module_2, '') IS NOT NULL
                 AND NOT (pm.superior_module_2 <=> pm.superior_module_1)
            THEN pm.superior_module_2
            ELSE NULL
        END,
        pm.name
    ) AS module_name,
    ai.url,
    ai.method,
    ai.protocol_type,
    ai.type,
    ai.name,
    ai.status,
    duplicates.duplicate_count,
    COUNT(acd.id) AS bound_step_count,
    GROUP_CONCAT(DISTINCT acd.case_id ORDER BY acd.case_id SEPARATOR ',') AS bound_case_ids
FROM api_info AS ai
INNER JOIN (
    SELECT
        project_product_id,
        module_id,
        url,
        method,
        protocol_type,
        type,
        COUNT(*) AS duplicate_count
    FROM api_info
    GROUP BY project_product_id, module_id, url, method, protocol_type, type
    HAVING COUNT(*) > 1
) AS duplicates
    ON duplicates.project_product_id = ai.project_product_id
   AND duplicates.module_id = ai.module_id
   AND duplicates.url <=> ai.url
   AND duplicates.method = ai.method
   AND duplicates.protocol_type <=> ai.protocol_type
   AND duplicates.type = ai.type
INNER JOIN project_product AS pp ON pp.id = ai.project_product_id
INNER JOIN project AS p ON p.id = pp.project_id
INNER JOIN product_module AS pm ON pm.id = ai.module_id
LEFT JOIN api_case_detailed AS acd ON acd.api_info_id = ai.id
GROUP BY
    ai.id,
    ai.project_product_id,
    p.name,
    pp.name,
    ai.module_id,
    pm.superior_module_1,
    pm.superior_module_2,
    pm.name,
    ai.url,
    ai.method,
    ai.protocol_type,
    ai.type,
    ai.name,
    ai.status,
    duplicates.duplicate_count
ORDER BY
    ai.project_product_id,
    ai.module_id,
    ai.url,
    ai.method,
    ai.protocol_type,
    ai.type,
    ai.id
"""

DELETE_QUERY = """
DELETE FROM api_info
WHERE id = %s
  AND NOT EXISTS (
      SELECT 1
      FROM api_case_detailed
      WHERE api_case_detailed.api_info_id = api_info.id
  )
"""

RESULT_FIELDS = (
    "id",
    "project_product_id",
    "project_product_name",
    "module_id",
    "module_name",
    "url",
    "method",
    "protocol_type",
    "type",
    "name",
    "status",
    "duplicate_count",
    "bound_step_count",
    "bound_case_ids",
    "action",
    "message",
)


@dataclass(frozen=True)
class DatabaseConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


def parse_literal_assignments(path: Path) -> dict[str, Any]:
    """只读取目标配置文件中的字面量赋值，不执行配置文件代码。"""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        for target in targets:
            if not isinstance(target, ast.Name) or target.id not in CONFIG_NAMES:
                continue
            try:
                values[target.id] = ast.literal_eval(value_node)
            except (ValueError, TypeError, SyntaxError) as exc:
                raise RuntimeError(f"配置 {target.id} 不是可安全读取的字面量") from exc
    return values


def load_master_database_config() -> DatabaseConfig:
    if not MASTER_SETTINGS_PATH.exists():
        raise FileNotFoundError(f"找不到 master 配置：{MASTER_SETTINGS_PATH}")
    values = parse_literal_assignments(MASTER_SETTINGS_PATH)
    missing = CONFIG_NAMES.difference(values)
    if missing:
        raise RuntimeError(f"master 配置缺少：{', '.join(sorted(missing))}")
    return DatabaseConfig(
        host=str(values["MYSQL_IP"]),
        port=int(values["MYSQL_PORT"]),
        database=str(values["MYSQL_DB_NAME"]),
        user=str(values["MYSQL_USER"]),
        password=str(values["MYSQL_PASSWORD"]),
    )


def connect(config: DatabaseConfig):
    return pymysql.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset="utf8mb4",
        connect_timeout=20,
        read_timeout=60,
        write_timeout=60,
        autocommit=False,
        cursorclass=DictCursor,
    )


def fetch_duplicate_rows(connection) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(DUPLICATE_QUERY)
        return list(cursor.fetchall())


def group_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["project_product_id"],
        row["module_id"],
        row["url"],
        row["method"],
        row["protocol_type"],
        row["type"],
    )


def print_preview(rows: list[dict[str, Any]]) -> tuple[int, int, int]:
    group_count = len({group_key(row) for row in rows})
    unbound_count = sum(int(row["bound_step_count"]) == 0 for row in rows)
    bound_count = len(rows) - unbound_count
    print("\n=== 重复 API 清理预览 ===")
    print(f"重复组数: {group_count}")
    print(f"重复接口数: {len(rows)}")
    print(f"可删除（未绑定 case）: {unbound_count}")
    print(f"跳过（已绑定 case）: {bound_count}")
    print("\n重复数量最多的接口组:")
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(group_key(row), []).append(row)
    for group_rows in sorted(groups.values(), key=lambda item: (-len(item), item[0]["id"]))[:15]:
        first = group_rows[0]
        ids = ",".join(str(row["id"]) for row in group_rows)
        print(
            f"  {len(group_rows):>2} 条 | {first['project_product_name']} | "
            f"{first['module_name']} | {first['method']} {first['url']!r} | "
            f"{first['protocol_type']} | type={first['type']} | ids={ids}"
        )
    return group_count, unbound_count, bound_count


def make_report_path() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return BACKUP_DIR / f"duplicate_api_info_cleanup_{timestamp}.csv"


def write_report(rows: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def confirm_delete(unbound_count: int) -> bool:
    expected = f"{CONFIRM_PREFIX} {unbound_count}"
    print("\n该操作会直接修改 master 数据库，且不会删除任何 API case。")
    try:
        actual = input(f"确认删除请输入 {expected!r}，其他输入取消：").strip()
    except EOFError:
        print("当前运行环境无法读取确认输入，已取消。可使用 --yes 明确执行。")
        return False
    if actual != expected:
        print("确认词不匹配，已取消。")
        return False
    return True


def cleanup(connection, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, source_row in enumerate(rows, start=1):
        row = dict(source_row)
        if int(row["bound_step_count"]) > 0:
            row["action"] = "skipped_bound_case"
            row["message"] = f"绑定步骤 {row['bound_step_count']} 个，case_ids={row['bound_case_ids']}"
            results.append(row)
            continue

        savepoint = f"api_info_{row['id']}"
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SAVEPOINT {savepoint}")
                cursor.execute(DELETE_QUERY, (row["id"],))
                if cursor.rowcount == 1:
                    cursor.execute(f"RELEASE SAVEPOINT {savepoint}")
                    connection.commit()
                    row["action"] = "deleted"
                    row["message"] = "删除成功"
                else:
                    cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    connection.rollback()
                    row["action"] = "skipped_binding_changed"
                    row["message"] = "删除时发现 case 绑定已变化，未删除"
        except Exception as exc:  # 每条失败必须继续，具体数据库异常写入报告。
            connection.rollback()
            row["action"] = "failed"
            row["message"] = f"{type(exc).__name__}: {exc}"
        results.append(row)
        if index % 25 == 0 or index == len(rows):
            deleted = sum(item.get("action") == "deleted" for item in results)
            failed = sum(item.get("action") == "failed" for item in results)
            print(f"处理进度 {index}/{len(rows)}，已删除 {deleted}，失败 {failed}")
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="只预览并生成报告，不删除")
    parser.add_argument("--yes", action="store_true", help="确认执行，不等待交互输入")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_master_database_config()
    print(f"配置来源: {MASTER_SETTINGS_PATH}")
    print(f"目标数据库: {config.user}@{config.host}:{config.port}/{config.database}")

    connection = connect(config)
    try:
        rows = fetch_duplicate_rows(connection)
        _, unbound_count, _ = print_preview(rows)
        preview_path = make_report_path()
        preview_rows = [
            {
                **row,
                "action": "candidate_unbound" if int(row["bound_step_count"]) == 0 else "candidate_bound",
                "message": "待确认" if int(row["bound_step_count"]) == 0 else "存在 case 绑定，删除时跳过",
            }
            for row in rows
        ]
        write_report(preview_rows, preview_path)
        print(f"预览报告: {preview_path}")

        if not rows:
            print("没有发现六字段重复的 API。")
            return 0
        if unbound_count == 0:
            print("所有重复 API 都已绑定 case，没有可删除记录。")
            return 0
        if args.dry_run:
            print("dry_run=true，未修改数据库。")
            return 0
        if not args.yes and not confirm_delete(unbound_count):
            return 0

        results = cleanup(connection, rows)
        result_path = make_report_path()
        write_report(results, result_path)
        deleted = sum(row["action"] == "deleted" for row in results)
        skipped = sum(row["action"].startswith("skipped") for row in results)
        failed = sum(row["action"] == "failed" for row in results)
        remaining_rows = fetch_duplicate_rows(connection)
        remaining_groups = len({group_key(row) for row in remaining_rows})
        print("\n=== 清理结果 ===")
        print(f"删除成功: {deleted}")
        print(f"跳过: {skipped}")
        print(f"失败: {failed}")
        print(f"剩余重复组: {remaining_groups}")
        print(f"结果报告: {result_path}")
        return 1 if failed else 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())

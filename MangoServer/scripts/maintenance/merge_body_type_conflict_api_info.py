"""迁移 body_type 冲突的重复 API；默认仅生成计划，不使用 Django。

保留规则：multipart > json > form > raw > none；同类型优先 case 步骤引用最多，
再按 ID 从小到大。apply 只迁移外键，不删除旧接口，便于复测后回滚。
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from cleanup_duplicate_api_info import BACKUP_DIR, connect, load_master_database_config
from merge_duplicate_api_info import (
    PARAMETER_QUERY_TEMPLATE,
    STEP_QUERY_TEMPLATE,
    canonical_json,
    duplicate_key,
    fetch_by_ids,
    fetch_duplicate_rows,
    json_safe,
    parameter_fingerprints,
    runtime_config,
    sha256_json,
)


PLAN_VERSION = 1
BODY_TYPE_PRIORITY = {"multipart": 0, "json": 1, "form": 2, "raw": 3, "none": 4, None: 5}
METHOD_TITLES = {0: "GET", 1: "POST", 2: "PUT", 3: "DELETE", 6: "PATCH"}


def api_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "key": json_safe(duplicate_key(row)),
        "name": row["name"],
        "body_type": row["body_type"],
        "body_config": json.loads(canonical_json(row["body_config"])),
        "runtime_config": json_safe(runtime_config(row)),
        "case_step_count": int(row["case_step_count"]),
        "auth_config_count": int(row["auth_config_count"]),
    }


def choose_keep(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        rows,
        key=lambda row: (
            BODY_TYPE_PRIORITY.get(row["body_type"], 99),
            -int(row["case_step_count"]),
            int(row["id"]),
        ),
    )


def build_plan(connection, config) -> dict[str, Any]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in fetch_duplicate_rows(connection):
        grouped[duplicate_key(row)].append(row)
    conflict_groups = [rows for rows in grouped.values() if len({row["body_type"] for row in rows}) > 1]
    api_ids = sorted(int(row["id"]) for rows in conflict_groups for row in rows)
    steps = fetch_by_ids(connection, STEP_QUERY_TEMPLATE, api_ids)
    step_ids = [int(step["step_id"]) for step in steps]
    parameters = fetch_by_ids(connection, PARAMETER_QUERY_TEMPLATE, step_ids) if step_ids else []
    fingerprints = parameter_fingerprints(parameters)
    steps_by_api: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for step in steps:
        item = json_safe(dict(step))
        item["parameter_snapshot"] = fingerprints.get(int(step["step_id"]), {"count": 0, "sha256": sha256_json([])})
        steps_by_api[int(step["api_info_id"])].append(item)

    groups = []
    cases: dict[int, dict[str, Any]] = {}
    for number, rows in enumerate(conflict_groups, start=1):
        keep = choose_keep(rows)
        group_steps = []
        for row in rows:
            group_steps.extend(steps_by_api.get(int(row["id"]), []))
        group = {
            "group_no": number,
            "key": json_safe(duplicate_key(keep)),
            "project_product_name": keep["project_product_name"],
            "module_name": keep["module_name"],
            "method_title": METHOD_TITLES.get(keep["method"], str(keep["method"])),
            "keep_api_info_id": int(keep["id"]),
            "keep_body_type": keep["body_type"],
            "replace_api_info_ids": sorted(int(row["id"]) for row in rows if row["id"] != keep["id"]),
            "api_snapshots": [api_snapshot(row) for row in rows],
            "steps": sorted(group_steps, key=lambda item: (item["case_id"], item["case_sort"] or 0, item["step_id"])),
            "case_ids": sorted({int(step["case_id"]) for step in group_steps}),
        }
        groups.append(group)
        for step in group_steps:
            case_id = int(step["case_id"])
            cases.setdefault(case_id, {
                "case_id": case_id,
                "case_name": step["case_name"],
                "project_product_id": step["case_project_product_id"],
                "affected_step_ids": [],
            })["affected_step_ids"].append(int(step["step_id"]))
    for case in cases.values():
        case["affected_step_ids"].sort()

    plan = {
        "plan_version": PLAN_VERSION,
        "created_at": datetime.now().astimezone().isoformat(),
        "database": {"host": config.host, "port": config.port, "name": config.database, "user": config.user},
        "keep_rule": "multipart > json > form > raw > none; then case_step_count desc; then id asc",
        "summary": {
            "groups": len(groups),
            "api_records": len(api_ids),
            "replace_api_records": sum(len(group["replace_api_info_ids"]) for group in groups),
            "affected_cases": len(cases),
            "affected_steps": len(steps),
        },
        "groups": groups,
        "retest_cases": sorted(cases.values(), key=lambda item: item["case_id"]),
    }
    plan["plan_sha256"] = sha256_json(plan)
    return plan


def write_plan(plan: dict[str, Any]) -> tuple[Path, Path, Path]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = BACKUP_DIR / f"body_type_conflict_merge_plan_{stamp}.json"
    csv_path = BACKUP_DIR / f"body_type_conflict_merge_plan_{stamp}.csv"
    retest_path = BACKUP_DIR / f"body_type_conflict_retest_cases_{stamp}.csv"
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        fields = ["group_no", "project_product", "module", "method", "url", "keep_id", "keep_body_type", "replace_ids", "case_ids"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for group in plan["groups"]:
            writer.writerow({
                "group_no": group["group_no"], "project_product": group["project_product_name"],
                "module": group["module_name"], "method": group["method_title"], "url": group["key"][2],
                "keep_id": group["keep_api_info_id"], "keep_body_type": group["keep_body_type"],
                "replace_ids": ",".join(map(str, group["replace_api_info_ids"])),
                "case_ids": ",".join(map(str, group["case_ids"])),
            })
    with retest_path.open("w", newline="", encoding="utf-8-sig") as file:
        fields = ["case_id", "case_name", "project_product_id", "affected_step_ids"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for case in plan["retest_cases"]:
            writer.writerow({**case, "affected_step_ids": ",".join(map(str, case["affected_step_ids"]))})
    return json_path, csv_path, retest_path


def verify_plan(plan: dict[str, Any], config) -> None:
    payload = dict(plan)
    expected = payload.pop("plan_sha256", None)
    if plan.get("plan_version") != PLAN_VERSION or sha256_json(payload) != expected:
        raise RuntimeError("计划版本或哈希校验失败")
    if plan["database"]["host"] != config.host or plan["database"]["name"] != config.database:
        raise RuntimeError("计划数据库与 master 配置不一致")


def validate_group(connection, group: dict[str, Any]) -> None:
    api_ids = [snapshot["id"] for snapshot in group["api_snapshots"]]
    placeholders = ",".join(["%s"] * len(api_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT ai.*, "
            f"(SELECT COUNT(*) FROM api_case_detailed d WHERE d.api_info_id=ai.id) case_step_count, "
            f"(SELECT COUNT(*) FROM api_auth_config a WHERE a.api_info_id=ai.id) auth_config_count "
            f"FROM api_info ai WHERE ai.id IN ({placeholders}) FOR UPDATE",
            api_ids,
        )
        rows = list(cursor.fetchall())
        cursor.execute(
            f"SELECT id step_id, api_info_id, case_id FROM api_case_detailed "
            f"WHERE api_info_id IN ({placeholders}) ORDER BY id FOR UPDATE",
            api_ids,
        )
        steps = list(cursor.fetchall())
    if sorted(row["id"] for row in rows) != sorted(api_ids):
        raise RuntimeError("接口集合已变化")
    expected_snapshots = {item["id"]: item for item in group["api_snapshots"]}
    for row in rows:
        if api_snapshot(row) != expected_snapshots[int(row["id"])]:
            raise RuntimeError(f"接口 {row['id']} 配置或引用数量已变化")
    expected_steps = sorted((int(s["step_id"]), int(s["api_info_id"]), int(s["case_id"])) for s in group["steps"])
    actual_steps = sorted((int(s["step_id"]), int(s["api_info_id"]), int(s["case_id"])) for s in steps)
    if expected_steps != actual_steps:
        raise RuntimeError("case 步骤绑定已变化")
    current_parameters = fetch_by_ids(connection, PARAMETER_QUERY_TEMPLATE, [item[0] for item in expected_steps])
    current_fingerprints = parameter_fingerprints(current_parameters)
    for step in group["steps"]:
        actual = current_fingerprints.get(int(step["step_id"]), {"count": 0, "sha256": sha256_json([])})
        if actual != step["parameter_snapshot"]:
            raise RuntimeError(f"步骤 {step['step_id']} 场景参数已变化")


def apply_plan(connection, plan: dict[str, Any]) -> None:
    for group in plan["groups"]:
        try:
            connection.begin()
            validate_group(connection, group)
            replace_ids = group["replace_api_info_ids"]
            placeholders = ",".join(["%s"] * len(replace_ids))
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE api_case_detailed SET api_info_id=%s WHERE api_info_id IN ({placeholders})",
                    [group["keep_api_info_id"], *replace_ids],
                )
                cursor.execute(
                    f"UPDATE api_auth_config SET api_info_id=%s WHERE api_info_id IN ({placeholders})",
                    [group["keep_api_info_id"], *replace_ids],
                )
            connection.commit()
        except Exception as exc:
            connection.rollback()
            raise RuntimeError(f"第 {group['group_no']} 组迁移失败并已回滚：{exc}") from exc
    print(f"已迁移 {len(plan['groups'])} 组引用；未删除旧接口。")


def rollback_plan(connection, plan: dict[str, Any]) -> None:
    restored = 0
    for group in plan["groups"]:
        connection.begin()
        try:
            with connection.cursor() as cursor:
                for step in group["steps"]:
                    cursor.execute(
                        "UPDATE api_case_detailed SET api_info_id=%s WHERE id=%s AND api_info_id=%s",
                        (step["api_info_id"], step["step_id"], group["keep_api_info_id"]),
                    )
                    restored += cursor.rowcount
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    print(f"已恢复 {restored} 个步骤原接口 ID。")


def finalize_passed_groups(connection, plan: dict[str, Any], test_suite_ids: list[int]) -> None:
    if not test_suite_ids:
        raise RuntimeError("必须提供 --test-suite-ids")
    placeholders = ",".join(["%s"] * len(test_suite_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT id, case_id, status FROM test_suite_details "
            f"WHERE type=1 AND test_suite_id IN ({placeholders}) ORDER BY id",
            test_suite_ids,
        )
        report_rows = list(cursor.fetchall())
    case_status = {int(row["case_id"]): int(row["status"]) for row in report_rows}
    passed = [
        group for group in plan["groups"]
        if group["case_ids"] and all(case_status.get(int(case_id)) == 1 for case_id in group["case_ids"])
    ]
    print(f"全部复测通过组: {len(passed)}；其余组保留旧接口。")
    deleted = 0
    for group in passed:
        replace_ids = group["replace_api_info_ids"]
        ph = ",".join(["%s"] * len(replace_ids))
        try:
            connection.begin()
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT id FROM api_info WHERE id IN ({ph}) FOR UPDATE", replace_ids)
                if sorted(row["id"] for row in cursor.fetchall()) != sorted(replace_ids):
                    raise RuntimeError("待删除接口集合已变化")
                cursor.execute(f"SELECT COUNT(*) count FROM api_case_detailed WHERE api_info_id IN ({ph})", replace_ids)
                if cursor.fetchone()["count"]:
                    raise RuntimeError("待删除接口仍有 case 引用")
                cursor.execute(f"SELECT COUNT(*) count FROM api_auth_config WHERE api_info_id IN ({ph})", replace_ids)
                if cursor.fetchone()["count"]:
                    raise RuntimeError("待删除接口仍有授权配置引用")
                cursor.execute(f"DELETE FROM api_info WHERE id IN ({ph})", replace_ids)
                deleted += cursor.rowcount
            connection.commit()
        except Exception as exc:
            connection.rollback()
            raise RuntimeError(f"第 {group['group_no']} 组最终删除失败：{exc}") from exc
    print("完成组号:", ",".join(str(group["group_no"]) for group in passed))
    print(f"删除旧接口 {deleted} 条。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--apply-plan", type=Path)
    actions.add_argument("--finalize-passed-plan", type=Path)
    actions.add_argument("--rollback-plan", type=Path)
    parser.add_argument("--test-suite-ids", type=int, nargs="*", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_master_database_config()
    connection = connect(config)
    try:
        plan_path = args.apply_plan or args.finalize_passed_plan or args.rollback_plan
        if not plan_path:
            plan = build_plan(connection, config)
            paths = write_plan(plan)
            print(json.dumps(plan["summary"], ensure_ascii=False, indent=2))
            print("计划:", paths[0])
            print("明细:", paths[1])
            print("复测:", paths[2])
            print("本次未修改数据库。")
            return 0
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        verify_plan(plan, config)
        if args.apply_plan:
            apply_plan(connection, plan)
        elif args.finalize_passed_plan:
            finalize_passed_groups(connection, plan, args.test_suite_ids)
        else:
            rollback_plan(connection, plan)
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())

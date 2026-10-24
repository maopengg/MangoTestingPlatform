"""最终收敛所有六字段重复 API，直接连接 master MySQL，不使用 Django。

默认只生成计划和完整备份；--execute-plan 在一个事务内迁移所有引用并删除冗余接口，
最终重复组不为 0 时整体回滚。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
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
BODY_PRIORITY = {"multipart": 0, "json": 1, "form": 2, "raw": 3, "none": 4, None: 5}
METHOD_TITLES = {0: "GET", 1: "POST", 2: "PUT", 3: "DELETE", 6: "PATCH"}


def has_value(value: Any) -> bool:
    normalized = canonical_json(value)
    return normalized not in {"null", "{}", "[]", '""'}


def choose_keep(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        rows,
        key=lambda row: (
            -int(row["auth_config_count"]),
            BODY_PRIORITY.get(row["body_type"], 99),
            -int(row["case_step_count"]),
            -int(has_value(row["body_config"])),
            -int(any(value not in (None, "", [], {}) for value in runtime_config(row).values())),
            int(row["id"]),
        ),
    )


def row_fingerprint(row: dict[str, Any]) -> str:
    fields = {
        "id": row["id"], "project_product_id": row["project_product_id"], "module_id": row["module_id"],
        "url": row["url"], "method": row["method"], "protocol_type": row["protocol_type"], "type": row["type"],
        "name": row["name"], "body_type": row["body_type"], "body_config": row["body_config"],
        "params": row["params"], "headers": row["headers"], "sse_config": row["sse_config"],
        "posterior_json_path": row["posterior_json_path"], "posterior_re": row["posterior_re"],
        "posterior_func": row["posterior_func"], "posterior_file": row["posterior_file"],
        "is_schema": row["is_schema"], "ass_schema": row["ass_schema"], "status": row["status"],
        "case_step_count": row["case_step_count"], "auth_config_count": row["auth_config_count"],
    }
    return sha256_json(json_safe(fields))


def build_plan(connection, config) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = fetch_duplicate_rows(connection)
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[duplicate_key(row)].append(row)
    api_ids = sorted(int(row["id"]) for row in rows)
    steps = fetch_by_ids(connection, STEP_QUERY_TEMPLATE, api_ids)
    step_ids = [int(step["step_id"]) for step in steps]
    parameters = fetch_by_ids(connection, PARAMETER_QUERY_TEMPLATE, step_ids) if step_ids else []
    parameter_hashes = parameter_fingerprints(parameters)
    steps_by_api: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for step in steps:
        item = json_safe(dict(step))
        item["parameter_snapshot"] = parameter_hashes.get(int(step["step_id"]), {"count": 0, "sha256": sha256_json([])})
        steps_by_api[int(step["api_info_id"])].append(item)

    placeholders = ",".join(["%s"] * len(api_ids))
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id, api_info_id FROM api_auth_config WHERE api_info_id IN ({placeholders}) ORDER BY id", api_ids)
        auth_rows = list(cursor.fetchall())
        cursor.execute(f"SELECT * FROM api_info WHERE id IN ({placeholders}) ORDER BY id", api_ids)
        full_api_rows = [json_safe(dict(row)) for row in cursor.fetchall()]
    auth_by_api: dict[int, list[int]] = defaultdict(list)
    for row in auth_rows:
        auth_by_api[int(row["api_info_id"])].append(int(row["id"]))

    groups = []
    cases: dict[int, dict[str, Any]] = {}
    for number, group_rows in enumerate(grouped.values(), start=1):
        keep = choose_keep(group_rows)
        group_steps = []
        for row in group_rows:
            group_steps.extend(steps_by_api.get(int(row["id"]), []))
        snapshots = [{
            "id": int(row["id"]), "fingerprint": row_fingerprint(row),
            "body_type": row["body_type"], "case_step_count": int(row["case_step_count"]),
            "auth_config_ids": auth_by_api.get(int(row["id"]), []), "name": row["name"],
        } for row in group_rows]
        group = {
            "group_no": number,
            "key": json_safe(duplicate_key(keep)),
            "project_product_name": keep["project_product_name"], "module_name": keep["module_name"],
            "method_title": METHOD_TITLES.get(keep["method"], str(keep["method"])),
            "keep_api_info_id": int(keep["id"]),
            "replace_api_info_ids": sorted(int(row["id"]) for row in group_rows if row["id"] != keep["id"]),
            "api_snapshots": snapshots,
            "steps": sorted(group_steps, key=lambda item: (item["case_id"], item["case_sort"] or 0, item["step_id"])),
            "case_ids": sorted({int(step["case_id"]) for step in group_steps}),
        }
        groups.append(group)
        for step in group_steps:
            cid = int(step["case_id"])
            cases.setdefault(cid, {"case_id": cid, "case_name": step["case_name"], "affected_step_ids": []})["affected_step_ids"].append(int(step["step_id"]))
    for case in cases.values():
        case["affected_step_ids"].sort()
    plan = {
        "plan_version": PLAN_VERSION, "created_at": datetime.now().astimezone().isoformat(),
        "database": {"host": config.host, "port": config.port, "name": config.database, "user": config.user},
        "keep_rule": "auth refs desc; multipart/json/form/raw/none; case refs desc; body/runtime config; id asc",
        "summary": {"groups": len(groups), "api_records": len(rows), "delete_records": sum(len(g["replace_api_info_ids"]) for g in groups), "affected_cases": len(cases), "affected_steps": len(steps)},
        "groups": groups, "retest_cases": sorted(cases.values(), key=lambda item: item["case_id"]),
    }
    plan["plan_sha256"] = sha256_json(plan)
    return plan, full_api_rows


def write_plan(plan: dict[str, Any], full_api_rows: list[dict[str, Any]]) -> tuple[Path, Path, Path, Path]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_path = BACKUP_DIR / f"final_duplicate_api_plan_{stamp}.json"
    backup_path = BACKUP_DIR / f"final_duplicate_api_full_backup_{stamp}.json"
    csv_path = BACKUP_DIR / f"final_duplicate_api_plan_{stamp}.csv"
    retest_path = BACKUP_DIR / f"final_duplicate_api_retest_cases_{stamp}.csv"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    backup_path.write_text(json.dumps({"created_at": plan["created_at"], "plan_sha256": plan["plan_sha256"], "api_info_rows": full_api_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(plan_path, 0o600); os.chmod(backup_path, 0o600)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        fields = ["group_no", "project_product", "module", "method", "url", "keep_id", "replace_ids", "case_ids"]
        writer = csv.DictWriter(file, fieldnames=fields); writer.writeheader()
        for g in plan["groups"]:
            writer.writerow({"group_no": g["group_no"], "project_product": g["project_product_name"], "module": g["module_name"], "method": g["method_title"], "url": g["key"][2], "keep_id": g["keep_api_info_id"], "replace_ids": ",".join(map(str, g["replace_api_info_ids"])), "case_ids": ",".join(map(str, g["case_ids"]))})
    with retest_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=["case_id", "case_name", "affected_step_ids"]); writer.writeheader()
        for case in plan["retest_cases"]:
            writer.writerow({**case, "affected_step_ids": ",".join(map(str, case["affected_step_ids"]))})
    return plan_path, backup_path, csv_path, retest_path


def verify_plan(plan: dict[str, Any], config) -> None:
    payload = dict(plan); expected = payload.pop("plan_sha256", None)
    if plan.get("plan_version") != PLAN_VERSION or sha256_json(payload) != expected:
        raise RuntimeError("计划版本或哈希校验失败")
    if plan["database"]["host"] != config.host or plan["database"]["name"] != config.database:
        raise RuntimeError("目标数据库不一致")


def execute_plan(connection, plan: dict[str, Any]) -> None:
    connection.begin()
    try:
        for group in plan["groups"]:
            all_ids = [item["id"] for item in group["api_snapshots"]]
            placeholders = ",".join(["%s"] * len(all_ids))
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT ai.*, (SELECT COUNT(*) FROM api_case_detailed d WHERE d.api_info_id=ai.id) case_step_count, "
                    f"(SELECT COUNT(*) FROM api_auth_config a WHERE a.api_info_id=ai.id) auth_config_count "
                    f"FROM api_info ai WHERE ai.id IN ({placeholders}) FOR UPDATE", all_ids,
                )
                current = list(cursor.fetchall())
                if sorted(row["id"] for row in current) != sorted(all_ids):
                    raise RuntimeError(f"第 {group['group_no']} 组接口集合变化")
                expected = {item["id"]: item["fingerprint"] for item in group["api_snapshots"]}
                for row in current:
                    if row_fingerprint(row) != expected[int(row["id"])]:
                        raise RuntimeError(f"接口 {row['id']} 配置或引用已变化")
                step_ids = [int(step["step_id"]) for step in group["steps"]]
                if step_ids:
                    ph_steps = ",".join(["%s"] * len(step_ids))
                    cursor.execute(f"SELECT id,case_id,api_info_id FROM api_case_detailed WHERE id IN ({ph_steps}) FOR UPDATE", step_ids)
                    actual_steps = sorted((int(x["id"]), int(x["case_id"]), int(x["api_info_id"])) for x in cursor.fetchall())
                    expected_steps = sorted((int(x["step_id"]), int(x["case_id"]), int(x["api_info_id"])) for x in group["steps"])
                    if actual_steps != expected_steps:
                        raise RuntimeError(f"第 {group['group_no']} 组步骤映射变化")
                    params = fetch_by_ids(connection, PARAMETER_QUERY_TEMPLATE, step_ids)
                    fps = parameter_fingerprints(params)
                    for step in group["steps"]:
                        actual = fps.get(int(step["step_id"]), {"count": 0, "sha256": sha256_json([])})
                        if actual != step["parameter_snapshot"]:
                            raise RuntimeError(f"步骤 {step['step_id']} 参数变化")
                replace_ids = group["replace_api_info_ids"]
                ph_replace = ",".join(["%s"] * len(replace_ids))
                cursor.execute(f"UPDATE api_case_detailed SET api_info_id=%s WHERE api_info_id IN ({ph_replace})", [group["keep_api_info_id"], *replace_ids])
                cursor.execute(f"UPDATE api_auth_config SET api_info_id=%s WHERE api_info_id IN ({ph_replace})", [group["keep_api_info_id"], *replace_ids])
                cursor.execute(f"DELETE FROM api_info WHERE id IN ({ph_replace})", replace_ids)
                if cursor.rowcount != len(replace_ids):
                    raise RuntimeError(f"第 {group['group_no']} 组删除数量不符")
        with connection.cursor() as cursor:
            cursor.execute("""SELECT COUNT(*) count FROM (SELECT 1 FROM api_info GROUP BY project_product_id,module_id,url,method,protocol_type,type HAVING COUNT(*)>1) d""")
            remaining = cursor.fetchone()["count"]
        if remaining != 0:
            raise RuntimeError(f"最终仍有 {remaining} 个重复组")
        connection.commit()
        print(f"完成 {len(plan['groups'])} 组，删除 {plan['summary']['delete_records']} 条，最终重复组=0。")
    except Exception:
        connection.rollback()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-plan", type=Path)
    args = parser.parse_args()
    config = load_master_database_config(); connection = connect(config)
    try:
        if not args.execute_plan:
            plan, backup = build_plan(connection, config); paths = write_plan(plan, backup)
            print(json.dumps(plan["summary"], ensure_ascii=False, indent=2))
            print("计划:", paths[0]); print("完整备份:", paths[1]); print("明细:", paths[2]); print("复测:", paths[3]); print("本次未修改数据库。")
            return 0
        plan = json.loads(args.execute_plan.read_text(encoding="utf-8")); verify_plan(plan, config); execute_plan(connection, plan); return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())

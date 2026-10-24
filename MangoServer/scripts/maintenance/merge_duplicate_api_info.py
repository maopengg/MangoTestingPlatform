"""安全合并重复 API 接口定义，不使用 Django。

默认右键运行只生成计划，不修改数据库。计划仅包含以下安全组：
1. 六字段重复：项目产品、模块、URL、方法、协议、端类型；
2. 同组 body_type 完全一致；
3. 同组 body_config 规范化后完全一致。

分阶段执行：
    python scripts/maintenance/merge_duplicate_api_info.py
    python scripts/maintenance/merge_duplicate_api_info.py --apply-plan PLAN.json
    python scripts/maintenance/merge_duplicate_api_info.py --finalize-plan PLAN.json
    python scripts/maintenance/merge_duplicate_api_info.py --rollback-plan PLAN.json

apply 只迁移外键，不删除接口，便于复测失败时回滚；复测通过后再 finalize 删除。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from cleanup_duplicate_api_info import (
    BACKUP_DIR,
    connect,
    load_master_database_config,
)


PLAN_VERSION = 1
METHOD_TITLES = {0: "GET", 1: "POST", 2: "PUT", 3: "DELETE", 6: "PATCH"}

DUPLICATE_ROWS_QUERY = """
SELECT
    ai.id,
    ai.create_time,
    ai.update_time,
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
    ai.body_type,
    ai.body_config,
    ai.params,
    ai.headers,
    ai.sse_config,
    ai.posterior_json_path,
    ai.posterior_re,
    ai.posterior_func,
    ai.posterior_file,
    ai.is_schema,
    ai.ass_schema,
    ai.status,
    (SELECT COUNT(*) FROM api_case_detailed acd WHERE acd.api_info_id = ai.id) AS case_step_count,
    (SELECT COUNT(*) FROM api_auth_config aac WHERE aac.api_info_id = ai.id) AS auth_config_count
FROM api_info ai
INNER JOIN (
    SELECT project_product_id, module_id, url, method, protocol_type, type
    FROM api_info
    GROUP BY project_product_id, module_id, url, method, protocol_type, type
    HAVING COUNT(*) > 1
) duplicate_key
    ON duplicate_key.project_product_id = ai.project_product_id
   AND duplicate_key.module_id = ai.module_id
   AND duplicate_key.url <=> ai.url
   AND duplicate_key.method = ai.method
   AND duplicate_key.protocol_type <=> ai.protocol_type
   AND duplicate_key.type = ai.type
INNER JOIN project_product pp ON pp.id = ai.project_product_id
INNER JOIN project p ON p.id = pp.project_id
INNER JOIN product_module pm ON pm.id = ai.module_id
ORDER BY ai.project_product_id, ai.module_id, ai.url, ai.method, ai.protocol_type, ai.type, ai.id
"""

STEP_QUERY_TEMPLATE = """
SELECT
    acd.id AS step_id,
    acd.api_info_id,
    acd.case_id,
    ac.name AS case_name,
    ac.status AS case_status,
    ac.project_product_id AS case_project_product_id,
    ac.module_id AS case_module_id,
    ac.case_people_id,
    acd.case_sort,
    acd.status AS step_status
FROM api_case_detailed acd
INNER JOIN api_case ac ON ac.id = acd.case_id
WHERE acd.api_info_id IN ({placeholders})
ORDER BY acd.case_id, acd.case_sort, acd.id
"""

PARAMETER_QUERY_TEMPLATE = """
SELECT
    id,
    case_detailed_id,
    error_retry,
    retry_interval,
    name,
    headers,
    params,
    data,
    json,
    file,
    protocol_type,
    body_type,
    body_config,
    sse_config,
    front_sql,
    front_func,
    ass_general,
    ass_sql,
    ass_json_all,
    ass_text_all,
    ass_jsonpath,
    ass_schema,
    posterior_sql,
    posterior_response,
    posterior_response_text,
    posterior_sleep,
    posterior_file,
    posterior_func,
    status
FROM api_case_detailed_parameter
WHERE case_detailed_id IN ({placeholders})
ORDER BY case_detailed_id, id
"""


def json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def parse_json_field(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list, int, float, bool)):
        return value
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return json_safe(value)


def canonical_json(value: Any) -> str:
    return json.dumps(parse_json_field(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def runtime_config(row: dict[str, Any]) -> dict[str, Any]:
    """API case 执行仍会从 ApiInfo 读取的接口级行为配置。"""
    return {
        "posterior_json_path": parse_json_field(row.get("posterior_json_path")),
        "posterior_re": parse_json_field(row.get("posterior_re")),
        "posterior_func": row.get("posterior_func"),
        "posterior_file": row.get("posterior_file"),
        "is_schema": row.get("is_schema"),
        "ass_schema": parse_json_field(row.get("ass_schema")),
    }


def sha256_json(value: Any) -> str:
    payload = json.dumps(json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def duplicate_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["project_product_id"],
        row["module_id"],
        row["url"],
        row["method"],
        row["protocol_type"],
        row["type"],
    )


def chunks(values: list[int], size: int = 500) -> Iterable[list[int]]:
    for index in range(0, len(values), size):
        yield values[index:index + size]


def fetch_by_ids(connection, query_template: str, ids: list[int]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for id_chunk in chunks(ids):
        placeholders = ",".join(["%s"] * len(id_chunk))
        with connection.cursor() as cursor:
            cursor.execute(query_template.format(placeholders=placeholders), id_chunk)
            result.extend(cursor.fetchall())
    return result


def fetch_duplicate_rows(connection) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(DUPLICATE_ROWS_QUERY)
        return list(cursor.fetchall())


def choose_keep_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return min(
        rows,
        key=lambda row: (
            -int(row["auth_config_count"]),
            -int(row["case_step_count"]),
            row["create_time"],
            row["id"],
        ),
    )


def parameter_fingerprints(parameters: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for parameter in parameters:
        grouped[int(parameter["case_detailed_id"])].append(parameter)
    return {
        step_id: {"count": len(items), "sha256": sha256_json(items)}
        for step_id, items in grouped.items()
    }


def build_plan(connection, config) -> dict[str, Any]:
    rows = fetch_duplicate_rows(connection)
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[duplicate_key(row)].append(row)

    eligible: list[list[dict[str, Any]]] = []
    excluded: list[dict[str, Any]] = []
    for key, group_rows in grouped.items():
        body_types = {row["body_type"] for row in group_rows}
        body_configs = {canonical_json(row["body_config"]) for row in group_rows}
        runtime_configs = {sha256_json(runtime_config(row)) for row in group_rows}
        reasons = []
        if len(body_types) > 1:
            reasons.append("body_type_diff")
        if len(body_configs) > 1:
            reasons.append("body_config_diff")
        if len(runtime_configs) > 1:
            reasons.append("api_runtime_config_diff")
        if reasons:
            excluded.append({
                "key": json_safe(key),
                "api_ids": [row["id"] for row in group_rows],
                "reasons": reasons,
            })
        else:
            eligible.append(group_rows)

    eligible_api_ids = sorted(row["id"] for group_rows in eligible for row in group_rows)
    steps = fetch_by_ids(connection, STEP_QUERY_TEMPLATE, eligible_api_ids)
    step_ids = [int(step["step_id"]) for step in steps]
    parameters = fetch_by_ids(connection, PARAMETER_QUERY_TEMPLATE, step_ids) if step_ids else []
    fingerprints = parameter_fingerprints(parameters)
    steps_by_api: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for step in steps:
        item = dict(step)
        item["parameter_snapshot"] = fingerprints.get(int(step["step_id"]), {"count": 0, "sha256": sha256_json([])})
        steps_by_api[int(step["api_info_id"])].append(json_safe(item))

    plan_groups = []
    for group_index, group_rows in enumerate(eligible, start=1):
        keep = choose_keep_row(group_rows)
        api_records = []
        group_steps = []
        for row in group_rows:
            record = {
                key: json_safe(row[key])
                for key in (
                    "id", "create_time", "update_time", "project_product_id", "project_product_name",
                    "module_id", "module_name", "url", "method", "protocol_type", "type", "name",
                    "body_type", "body_config", "params", "headers", "sse_config", "status",
                    "posterior_json_path", "posterior_re", "posterior_func", "posterior_file",
                    "is_schema", "ass_schema",
                    "case_step_count", "auth_config_count",
                )
            }
            record["body_config_sha256"] = hashlib.sha256(canonical_json(row["body_config"]).encode("utf-8")).hexdigest()
            api_records.append(record)
            group_steps.extend(steps_by_api.get(int(row["id"]), []))
        replace_ids = sorted(int(row["id"]) for row in group_rows if row["id"] != keep["id"])
        plan_groups.append({
            "group_no": group_index,
            "key": json_safe(duplicate_key(keep)),
            "project_product_name": keep["project_product_name"],
            "module_name": keep["module_name"],
            "method_title": METHOD_TITLES.get(keep["method"], str(keep["method"])),
            "body_type": keep["body_type"],
            "body_config_sha256": hashlib.sha256(canonical_json(keep["body_config"]).encode("utf-8")).hexdigest(),
            "runtime_config_sha256": sha256_json(runtime_config(keep)),
            "keep_api_info_id": int(keep["id"]),
            "replace_api_info_ids": replace_ids,
            "api_records": api_records,
            "steps": sorted(group_steps, key=lambda item: (item["case_id"], item["case_sort"] or 0, item["step_id"])),
            "case_ids": sorted({int(step["case_id"]) for step in group_steps}),
        })

    cases: dict[int, dict[str, Any]] = {}
    for step in steps:
        case_id = int(step["case_id"])
        cases.setdefault(case_id, {
            "case_id": case_id,
            "case_name": step["case_name"],
            "case_status": step["case_status"],
            "project_product_id": step["case_project_product_id"],
            "module_id": step["case_module_id"],
            "case_people_id": step["case_people_id"],
            "affected_step_ids": [],
        })["affected_step_ids"].append(int(step["step_id"]))
    for case in cases.values():
        case["affected_step_ids"].sort()

    plan = {
        "plan_version": PLAN_VERSION,
        "created_at": datetime.now().astimezone().isoformat(),
        "database": {"host": config.host, "port": config.port, "name": config.database, "user": config.user},
        "rules": {
            "duplicate_fields": ["project_product_id", "module_id", "url", "method", "protocol_type", "type"],
            "excluded_when": [
                "body_type differs",
                "normalized body_config differs",
                "ApiInfo runtime extraction/schema config differs",
            ],
            "keep_priority": ["auth_config_count desc", "case_step_count desc", "create_time asc", "id asc"],
        },
        "summary": {
            "all_duplicate_groups": len(grouped),
            "eligible_groups": len(plan_groups),
            "excluded_groups": len(excluded),
            "eligible_api_records": len(eligible_api_ids),
            "replace_api_records": sum(len(group["replace_api_info_ids"]) for group in plan_groups),
            "affected_cases": len(cases),
            "affected_steps": len(steps),
        },
        "excluded_groups": excluded,
        "groups": plan_groups,
        "retest_cases": sorted(cases.values(), key=lambda item: item["case_id"]),
    }
    plan["plan_sha256"] = sha256_json(plan)
    return plan


def write_plan(plan: dict[str, Any]) -> tuple[Path, Path, Path]:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = BACKUP_DIR / f"duplicate_api_merge_plan_{timestamp}.json"
    csv_path = BACKUP_DIR / f"duplicate_api_merge_plan_{timestamp}.csv"
    retest_path = BACKUP_DIR / f"duplicate_api_merge_retest_cases_{timestamp}.csv"
    json_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(json_path, 0o600)

    with csv_path.open("w", newline="", encoding="utf-8-sig") as file:
        fields = (
            "group_no", "project_product_name", "module_name", "method", "url", "protocol_type", "type",
            "body_type", "keep_api_info_id", "replace_api_info_ids", "case_ids", "affected_steps",
        )
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for group in plan["groups"]:
            key = group["key"]
            writer.writerow({
                "group_no": group["group_no"],
                "project_product_name": group["project_product_name"],
                "module_name": group["module_name"],
                "method": group["method_title"],
                "url": key[2],
                "protocol_type": key[4],
                "type": key[5],
                "body_type": group["body_type"],
                "keep_api_info_id": group["keep_api_info_id"],
                "replace_api_info_ids": ",".join(map(str, group["replace_api_info_ids"])),
                "case_ids": ",".join(map(str, group["case_ids"])),
                "affected_steps": len(group["steps"]),
            })

    with retest_path.open("w", newline="", encoding="utf-8-sig") as file:
        fields = (
            "case_id", "case_name", "case_status", "project_product_id", "module_id", "case_people_id",
            "affected_step_ids",
        )
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for case in plan["retest_cases"]:
            writer.writerow({**case, "affected_step_ids": ",".join(map(str, case["affected_step_ids"]))})
    return json_path, csv_path, retest_path


def verify_plan_file(plan: dict[str, Any], config) -> None:
    if plan.get("plan_version") != PLAN_VERSION:
        raise RuntimeError("计划版本不匹配")
    expected_hash = plan.get("plan_sha256")
    without_hash = dict(plan)
    without_hash.pop("plan_sha256", None)
    if sha256_json(without_hash) != expected_hash:
        raise RuntimeError("计划文件哈希校验失败，文件可能被修改")
    database = plan.get("database", {})
    if database.get("host") != config.host or database.get("name") != config.database:
        raise RuntimeError("计划目标数据库与 master 配置不一致")


def current_parameter_snapshot(connection, step_ids: list[int]) -> dict[int, dict[str, Any]]:
    parameters = fetch_by_ids(connection, PARAMETER_QUERY_TEMPLATE, step_ids) if step_ids else []
    result = parameter_fingerprints(parameters)
    for step_id in step_ids:
        result.setdefault(step_id, {"count": 0, "sha256": sha256_json([])})
    return result


def validate_group_before_apply(connection, group: dict[str, Any]) -> None:
    api_ids = [group["keep_api_info_id"], *group["replace_api_info_ids"]]
    placeholders = ",".join(["%s"] * len(api_ids))
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT id, project_product_id, module_id, url, method, protocol_type, type, body_type, body_config, "
            f"posterior_json_path, posterior_re, posterior_func, posterior_file, is_schema, ass_schema "
            f"FROM api_info WHERE id IN ({placeholders}) FOR UPDATE",
            api_ids,
        )
        rows = list(cursor.fetchall())
        cursor.execute(
            f"SELECT id AS step_id, api_info_id, case_id FROM api_case_detailed "
            f"WHERE api_info_id IN ({placeholders}) ORDER BY id FOR UPDATE",
            api_ids,
        )
        steps = list(cursor.fetchall())
    if sorted(row["id"] for row in rows) != sorted(api_ids):
        raise RuntimeError("接口集合已变化")
    for row in rows:
        if list(duplicate_key(row)) != group["key"]:
            raise RuntimeError(f"接口 {row['id']} 的重复键已变化")
        if row["body_type"] != group["body_type"]:
            raise RuntimeError(f"接口 {row['id']} 的 body_type 已变化")
        body_hash = hashlib.sha256(canonical_json(row["body_config"]).encode("utf-8")).hexdigest()
        if body_hash != group["body_config_sha256"]:
            raise RuntimeError(f"接口 {row['id']} 的 body_config 已变化")
        if sha256_json(runtime_config(row)) != group["runtime_config_sha256"]:
            raise RuntimeError(f"接口 {row['id']} 的运行时提取/schema 配置已变化")

    expected_steps = sorted(
        (int(step["step_id"]), int(step["api_info_id"]), int(step["case_id"])) for step in group["steps"]
    )
    actual_steps = sorted((int(step["step_id"]), int(step["api_info_id"]), int(step["case_id"])) for step in steps)
    if actual_steps != expected_steps:
        raise RuntimeError("case 步骤绑定已变化")
    snapshots = current_parameter_snapshot(connection, [step[0] for step in expected_steps])
    for expected in group["steps"]:
        if snapshots[int(expected["step_id"])] != expected["parameter_snapshot"]:
            raise RuntimeError(f"步骤 {expected['step_id']} 的场景参数已变化")


def apply_plan(connection, plan: dict[str, Any]) -> None:
    completed = 0
    for group in plan["groups"]:
        try:
            connection.begin()
            validate_group_before_apply(connection, group)
            replace_ids = group["replace_api_info_ids"]
            if replace_ids:
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
            completed += 1
        except Exception:
            connection.rollback()
            raise RuntimeError(f"第 {group['group_no']} 组应用失败，已回滚该组")
    print(f"已迁移 {completed} 组外键；尚未删除重复接口。请按 retest_cases 清单复测。")


def finalize_plan(connection, plan: dict[str, Any]) -> None:
    deleted = 0
    for group in plan["groups"]:
        replace_ids = group["replace_api_info_ids"]
        if not replace_ids:
            continue
        placeholders = ",".join(["%s"] * len(replace_ids))
        try:
            connection.begin()
            with connection.cursor() as cursor:
                all_ids = [group["keep_api_info_id"], *replace_ids]
                all_placeholders = ",".join(["%s"] * len(all_ids))
                cursor.execute(
                    f"SELECT id, project_product_id, module_id, url, method, protocol_type, type, body_type, "
                    f"body_config, posterior_json_path, posterior_re, posterior_func, posterior_file, "
                    f"is_schema, ass_schema FROM api_info WHERE id IN ({all_placeholders}) FOR UPDATE",
                    all_ids,
                )
                current_rows = list(cursor.fetchall())
                if sorted(row["id"] for row in current_rows) != sorted(all_ids):
                    raise RuntimeError("接口集合已变化")
                for row in current_rows:
                    if list(duplicate_key(row)) != group["key"]:
                        raise RuntimeError(f"接口 {row['id']} 的重复键已变化")
                    if row["body_type"] != group["body_type"]:
                        raise RuntimeError(f"接口 {row['id']} 的 body_type 已变化")
                    body_hash = hashlib.sha256(canonical_json(row["body_config"]).encode("utf-8")).hexdigest()
                    if body_hash != group["body_config_sha256"]:
                        raise RuntimeError(f"接口 {row['id']} 的 body_config 已变化")
                    if sha256_json(runtime_config(row)) != group["runtime_config_sha256"]:
                        raise RuntimeError(f"接口 {row['id']} 的运行时配置已变化")
                cursor.execute(
                    f"SELECT COUNT(*) count FROM api_case_detailed WHERE api_info_id IN ({placeholders})",
                    replace_ids,
                )
                if cursor.fetchone()["count"]:
                    raise RuntimeError("仍有 case 步骤引用待删除接口")
                cursor.execute(
                    f"SELECT COUNT(*) count FROM api_auth_config WHERE api_info_id IN ({placeholders})",
                    replace_ids,
                )
                if cursor.fetchone()["count"]:
                    raise RuntimeError("仍有授权配置引用待删除接口")
                cursor.execute(f"DELETE FROM api_info WHERE id IN ({placeholders})", replace_ids)
                deleted += cursor.rowcount
            connection.commit()
        except Exception:
            connection.rollback()
            raise RuntimeError(f"第 {group['group_no']} 组删除失败，已回滚该组")
    print(f"最终删除接口 {deleted} 条。")


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
    case_status: dict[int, int] = {}
    for row in report_rows:
        case_status[int(row["case_id"])] = int(row["status"])

    passed_groups = []
    skipped_groups = []
    for group in plan["groups"]:
        statuses = [case_status.get(int(case_id)) for case_id in group["case_ids"]]
        if statuses and all(status == 1 for status in statuses):
            passed_groups.append(group)
        else:
            skipped_groups.append({
                "group_no": group["group_no"],
                "case_statuses": dict(zip(group["case_ids"], statuses)),
            })
    if not passed_groups:
        print("没有关联 case 全部通过的组，不执行删除。")
        return
    subset_plan = dict(plan)
    subset_plan["groups"] = passed_groups
    print(f"复测全部通过组: {len(passed_groups)}，跳过组: {len(skipped_groups)}")
    print("将删除的组号:", ",".join(str(group["group_no"]) for group in passed_groups))
    finalize_plan(connection, subset_plan)


def rollback_plan(connection, plan: dict[str, Any]) -> None:
    restored = 0
    for group in plan["groups"]:
        try:
            connection.begin()
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
            raise RuntimeError(f"第 {group['group_no']} 组回滚失败")
    print(f"已恢复 {restored} 个 case 步骤的原接口 ID。")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--apply-plan", type=Path)
    actions.add_argument("--finalize-plan", type=Path)
    actions.add_argument("--finalize-passed-plan", type=Path)
    actions.add_argument("--rollback-plan", type=Path)
    parser.add_argument("--test-suite-ids", type=int, nargs="*", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_master_database_config()
    print(f"目标数据库: {config.user}@{config.host}:{config.port}/{config.database}")
    connection = connect(config)
    try:
        plan_path = args.apply_plan or args.finalize_plan or args.finalize_passed_plan or args.rollback_plan
        if not plan_path:
            plan = build_plan(connection, config)
            json_path, csv_path, retest_path = write_plan(plan)
            print(json.dumps(plan["summary"], ensure_ascii=False, indent=2))
            print(f"计划 JSON: {json_path}")
            print(f"计划 CSV: {csv_path}")
            print(f"复测清单: {retest_path}")
            print("本次只生成计划，未修改数据库。")
            return 0

        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        verify_plan_file(plan, config)
        if args.apply_plan:
            apply_plan(connection, plan)
        elif args.finalize_plan:
            finalize_plan(connection, plan)
        elif args.finalize_passed_plan:
            finalize_passed_groups(connection, plan, args.test_suite_ids)
        else:
            rollback_plan(connection, plan)
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())

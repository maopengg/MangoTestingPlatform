#!/usr/bin/env python3
"""Inventory Django models, Pydantic schemas, DRF serializers and dataclasses."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOTS = (
    ROOT / "MangoServer" / "src",
    ROOT / "MangoActuator" / "src",
    Path("/Users/mango/code/mango_tools/mangotools"),
    Path("/Users/mango/code/mango_automation/mangoautomation"),
)


def _name(node: ast.expr) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _fields(node: ast.ClassDef) -> list[str]:
    result: list[str] = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            result.append(item.target.id)
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and isinstance(item.value, ast.Call):
                    if _name(item.value.func).startswith("models."):
                        result.append(target.id)
    return result


def _db_table(node: ast.ClassDef) -> str | None:
    for item in node.body:
        if not isinstance(item, ast.ClassDef) or item.name != "Meta":
            continue
        for statement in item.body:
            if not isinstance(statement, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "db_table" for target in statement.targets):
                continue
            if isinstance(statement.value, ast.Constant) and isinstance(statement.value.value, str):
                return statement.value.value
    return None


def _json_fields(node: ast.ClassDef) -> list[str]:
    result: list[str] = []
    for item in node.body:
        if not isinstance(item, (ast.Assign, ast.AnnAssign)):
            continue
        value = item.value
        if not isinstance(value, ast.Call) or not _name(value.func).endswith("JSONField"):
            continue
        targets = item.targets if isinstance(item, ast.Assign) else [item.target]
        result.extend(target.id for target in targets if isinstance(target, ast.Name))
    return result


def _kind(node: ast.ClassDef) -> str | None:
    bases = {_name(base) for base in node.bases}
    if bases & {
        "BaseModel",
        "RootModel",
        "StrictSchema",
        "FrozenSchema",
        "OrmSchema",
        "TrimmedStrictSchema",
        "ContractModel",
        "StrictModel",
        "_StrictConfigModel",
    }:
        return "pydantic_schema"
    if any(base.endswith("Serializer") for base in bases):
        return "drf_serializer"
    if bases & {"models.Model", "AuditModel", "CreatedAtModel", "TimeStampedModel"}:
        return "django_model"
    if any(isinstance(decorator, ast.Name) and decorator.id == "dataclass" for decorator in node.decorator_list):
        return "dataclass"
    if any(isinstance(decorator, ast.Call) and _name(decorator.func) == "dataclass" for decorator in node.decorator_list):
        return "dataclass"
    return None


def _app(path: Path) -> str | None:
    parts = path.parts
    try:
        index = parts.index("apps")
    except ValueError:
        return None
    return parts[index + 1] if len(parts) > index + 1 else None


def collect(roots: tuple[Path, ...]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    parsed_files: dict[Path, ast.Module] = {}
    for source_root in roots:
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            parsed_files[path] = tree
            relative_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
            for node in tree.body:
                if not isinstance(node, ast.ClassDef):
                    continue
                kind = _kind(node)
                if kind is None:
                    continue
                records.append(
                    {
                        "class_name": node.name,
                        "kind": kind,
                        "app": _app(path),
                        "path": relative_path,
                        "fields": _fields(node),
                        "db_table": (
                            _db_table(node) or (f"{_app(path)}_{node.name.lower()}" if _app(path) else None)
                            if kind == "django_model"
                            else None
                        ),
                        "json_fields": _json_fields(node) if kind == "django_model" else [],
                        "cross_process_direction": None,
                        "callers": [],
                    }
                )
    locations: dict[tuple[str, str], set[str]] = {}
    for record in records:
        locations.setdefault((record["kind"], record["class_name"]), set()).add(record["path"])
    uses: dict[str, set[str]] = {}
    for path, tree in parsed_files.items():
        relative_path = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        for name in {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}:
            uses.setdefault(name, set()).add(relative_path)
    for record in records:
        record["callers"] = sorted(uses.get(record["class_name"], set()) - {record["path"]})
        if record["kind"] == "pydantic_schema":
            class_locations = locations[(record["kind"], record["class_name"])]
            usage_locations = set(record["callers"]) | class_locations
            server = any(location.startswith("MangoServer/") for location in usage_locations)
            actuator = any(location.startswith("MangoActuator/") for location in usage_locations)
            defined_in_server = any(location.startswith("MangoServer/") for location in class_locations)
            defined_in_actuator = any(
                location.startswith("MangoActuator/") or "/mango_automation/" in location
                for location in class_locations
            )
            shared = any("/mango_tools/" in location for location in class_locations)
            if shared and server and actuator:
                record["cross_process_direction"] = "server<->actuator"
            elif shared and server:
                record["cross_process_direction"] = "shared->server"
            elif shared and actuator:
                record["cross_process_direction"] = "shared->actuator"
            elif shared:
                record["cross_process_direction"] = "shared-library"
            elif defined_in_server and defined_in_actuator:
                record["cross_process_direction"] = "duplicated-server<->actuator"
    return records


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    records = collect(DEFAULT_ROOTS)
    payload = json.dumps(records, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()

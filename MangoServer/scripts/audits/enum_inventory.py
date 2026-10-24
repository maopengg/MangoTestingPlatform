#!/usr/bin/env python3
"""扫描项目枚举定义、调用方、Django choices 字段与 /system/enum 目录 key。

该脚本只做静态分析，不加载 Django，不修改任何文件。
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = SERVER_ROOT.parent
SERVER_SOURCE_ROOT = SERVER_ROOT / "src"
ACTUATOR_SOURCE_ROOT = REPOSITORY_ROOT / "MangoActuator" / "src"
IGNORED_PARTS = {"__pycache__", "migrations", "tests", ".venv"}


@dataclass
class EnumDefinition:
    name: str
    module: str
    path: str
    line: int
    bases: list[str]
    owner: str
    members: dict[str, str] = field(default_factory=dict)
    database_fields: list[str] = field(default_factory=list)
    catalog_keys: list[str] = field(default_factory=list)
    backend_callers: list[str] = field(default_factory=list)
    actuator_callers: list[str] = field(default_factory=list)


def _iter_python_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        yield path


def _module_name(path: Path, source_root: Path) -> str:
    relative = path.relative_to(source_root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(["src", *parts])


def _owner(path: Path) -> str:
    try:
        relative = path.relative_to(SERVER_SOURCE_ROOT)
    except ValueError:
        return "actuator"
    if len(relative.parts) >= 3 and relative.parts[0] == "apps":
        return relative.parts[1]
    if relative.parts and relative.parts[0] == "common":
        return "common"
    if relative.parts and relative.parts[0] == "processes":
        return "processes"
    if relative.parts and relative.parts[0] == "interfaces":
        return "interfaces"
    return "project"


def _base_names(node: ast.ClassDef) -> list[str]:
    return [ast.unparse(base) for base in node.bases]


def _is_enum(node: ast.ClassDef, path: Path) -> bool:
    bases = _base_names(node)
    return (
        node.name == "BaseEnum"
        or node.name.endswith(("Enum", "Choices"))
        or any(base.endswith(("Enum", "Choices")) for base in bases)
        or "enums" in path.parts and bool(bases)
    )


def _member_expression(node: ast.ClassDef) -> dict[str, str]:
    members: dict[str, str] = {}
    for statement in node.body:
        targets: list[ast.expr] = []
        value = None
        if isinstance(statement, ast.Assign):
            targets = statement.targets
            value = statement.value
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
            value = statement.value
        if value is None:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                members[target.id] = ast.unparse(value)
    return members


def _load_sources(root: Path) -> dict[Path, tuple[str, ast.AST]]:
    sources = {}
    for path in _iter_python_files(root):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        sources[path] = (source, tree)
    return sources


def _collect_definitions(sources: dict[Path, tuple[str, ast.AST]]) -> list[EnumDefinition]:
    definitions = []
    for path, (_source, tree) in sources.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef) or not _is_enum(node, path):
                continue
            definitions.append(
                EnumDefinition(
                    name=node.name,
                    module=_module_name(path, SERVER_SOURCE_ROOT),
                    path=str(path.relative_to(REPOSITORY_ROOT)),
                    line=node.lineno,
                    bases=_base_names(node),
                    owner=_owner(path),
                    members=_member_expression(node),
                )
            )
    return definitions


def _referenced_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _collect_database_fields(tree: ast.AST, enum_name: str) -> list[int]:
    lines = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != "choices":
                continue
            expression = ast.unparse(keyword.value)
            if enum_name in expression:
                lines.append(node.lineno)
    return lines


def _collect_catalog_keys(tree: ast.AST) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Attribute):
                continue
            if value.func.attr != "get_option" or not isinstance(value.func.value, ast.Name):
                continue
            result.setdefault(value.func.value.id, []).append(key.value)
    return result


def build_inventory() -> dict:
    backend_sources = _load_sources(SERVER_SOURCE_ROOT)
    actuator_sources = _load_sources(ACTUATOR_SOURCE_ROOT)
    definitions = _collect_definitions(backend_sources)
    backend_names = {path: _referenced_names(tree) for path, (_source, tree) in backend_sources.items()}
    actuator_names = {path: _referenced_names(tree) for path, (_source, tree) in actuator_sources.items()}

    catalog_keys: dict[str, list[str]] = {}
    for _path, (_source, tree) in backend_sources.items():
        for enum_name, keys in _collect_catalog_keys(tree).items():
            catalog_keys.setdefault(enum_name, []).extend(keys)

    for definition in definitions:
        definition_path = REPOSITORY_ROOT / definition.path
        for path, (_source, tree) in backend_sources.items():
            if path == definition_path:
                continue
            if definition.name in backend_names[path]:
                relative = path.relative_to(REPOSITORY_ROOT)
                definition.backend_callers.append(str(relative))
                for line in _collect_database_fields(tree, definition.name):
                    definition.database_fields.append(f"{relative}:{line}")
        for path, names in actuator_names.items():
            if definition.name in names:
                definition.actuator_callers.append(str(path.relative_to(REPOSITORY_ROOT)))
        definition.catalog_keys = sorted(set(catalog_keys.get(definition.name, [])))
        definition.backend_callers.sort()
        definition.actuator_callers.sort()
        definition.database_fields.sort()

    return {
        "summary": {
            "backend_enum_count": len(definitions),
            "owners": {
                owner: sum(1 for item in definitions if item.owner == owner)
                for owner in sorted({item.owner for item in definitions})
            },
        },
        "enums": [asdict(item) for item in definitions],
    }


def main():
    parser = argparse.ArgumentParser(description="输出枚举定义与使用清单")
    parser.add_argument("--compact", action="store_true", help="输出单行 JSON")
    args = parser.parse_args()
    inventory = build_inventory()
    print(json.dumps(inventory, ensure_ascii=False, indent=None if args.compact else 2))


if __name__ == "__main__":
    main()

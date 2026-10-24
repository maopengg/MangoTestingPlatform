#!/usr/bin/env python3
"""Replace project-local star imports with explicit imports.

This is a one-way architecture migration helper. It resolves the names that a
Python star import exposes (honouring literal ``__all__`` declarations) and
rewrites only modules below ``src``.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = ROOT / "src"


def module_path(importer: Path, node: ast.ImportFrom) -> Path | None:
    relative = importer.relative_to(SOURCE_ROOT)
    package_parts = list(relative.parent.parts)
    if node.level:
        keep = len(package_parts) - (node.level - 1)
        parts = package_parts[:keep]
    else:
        parts = []
    if node.module:
        module_parts = node.module.split(".")
        if module_parts[0] == "src":
            parts = module_parts[1:]
        else:
            parts.extend(module_parts)
    candidate = SOURCE_ROOT.joinpath(*parts)
    file_candidate = candidate.with_suffix(".py")
    if file_candidate.is_file():
        return file_candidate
    init_candidate = candidate / "__init__.py"
    return init_candidate if init_candidate.is_file() else None


def assigned_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return {name for item in target.elts for name in assigned_names(item)}
    return set()


def exports(path: Path, stack: tuple[Path, ...] = ()) -> list[str]:
    if path in stack:
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "__all__" for target in targets):
                try:
                    values = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    break
                if isinstance(values, (list, tuple)) and all(isinstance(value, str) for value in values):
                    return list(dict.fromkeys(values))

    names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                names.extend(assigned_names(target))
        elif isinstance(node, ast.Import):
            names.extend(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    names.append(alias.asname or alias.name)
                    continue
                dependency = module_path(path, node)
                if dependency:
                    names.extend(exports(dependency, (*stack, path)))
    return sorted({name for name in names if name != "__all__" and not name.startswith("_")})


def replacement(node: ast.ImportFrom, names: list[str], indent: str) -> str:
    prefix = "." * node.level + (node.module or "")
    if len(names) <= 4 and sum(map(len, names)) < 72:
        return f"{indent}from {prefix} import {', '.join(names)}"
    body = "\n".join(f"{indent}    {name}," for name in names)
    return f"{indent}from {prefix} import (\n{body}\n{indent})"


def rewrite(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines(keepends=True)
    changes: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not any(alias.name == "*" for alias in node.names):
            continue
        dependency = module_path(path, node)
        if dependency is None:
            raise RuntimeError(f"无法解析星号导入：{path}:{node.lineno}")
        names = exports(dependency)
        if not names:
            raise RuntimeError(f"星号导入没有可解析的公开名称：{path}:{node.lineno}")
        indent = lines[node.lineno - 1][: node.col_offset]
        changes.append((node.lineno - 1, node.end_lineno or node.lineno, replacement(node, names, indent) + "\n"))
    if not changes:
        return False
    for start, end, text in sorted(changes, reverse=True):
        lines[start:end] = [text]
    path.write_text("".join(lines), encoding="utf-8")
    return True


def main() -> None:
    changed = [path for path in SOURCE_ROOT.rglob("*.py") if rewrite(path)]
    print(f"expanded star imports in {len(changed)} files")


if __name__ == "__main__":
    main()

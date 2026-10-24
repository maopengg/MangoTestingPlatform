#!/usr/bin/env python3
"""Shared, dependency-free helpers for the code-driven API case builder."""

from __future__ import annotations

import ast
import copy
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping, Sequence


SCHEMA_VERSION = "3.0"
TOOL_VERSION = "0.4.0"
RAW_EVIDENCE_FORMAT = "canonical-json-list-v1"
HTTP_DECORATORS = {
    "get": ("GET",),
    "post": ("POST",),
    "put": ("PUT",),
    "patch": ("PATCH",),
    "delete": ("DELETE",),
    "options": ("OPTIONS",),
    "head": ("HEAD",),
}
FASTAPI_PARAMETER_BINDINGS = {
    "Body",
    "Cookie",
    "Depends",
    "File",
    "Form",
    "Header",
    "Path",
    "Query",
    "Security",
}
FASTAPI_ROUTER_SYMBOL_MODULES = {
    "APIRouter": frozenset({"fastapi", "fastapi.routing"}),
}
FASTAPI_APPLICATION_SYMBOL_MODULES = {
    "FastAPI": frozenset({"fastapi", "fastapi.applications"}),
    "Starlette": frozenset({"starlette", "starlette.applications"}),
}
FASTAPI_PARAMETER_SYMBOL_MODULES = {
    name: frozenset({"fastapi", "fastapi.param_functions", "fastapi.params"})
    for name in FASTAPI_PARAMETER_BINDINGS
}
FASTAPI_PARAMETER_SYMBOL_MODULES["Security"] = frozenset(
    {
        "fastapi",
        "fastapi.param_functions",
        "fastapi.params",
        "fastapi.security",
    }
)
PYDANTIC_SYMBOL_MODULES = {
    "BaseModel": frozenset(
        {"pydantic", "pydantic.main", "pydantic.v1", "pydantic.v1.main"}
    ),
    "Field": frozenset(
        {"pydantic", "pydantic.fields", "pydantic.v1", "pydantic.v1.fields"}
    ),
    "validator": frozenset(
        {
            "pydantic",
            "pydantic.class_validators",
            "pydantic.v1",
            "pydantic.v1.class_validators",
        }
    ),
    "root_validator": frozenset(
        {
            "pydantic",
            "pydantic.class_validators",
            "pydantic.v1",
            "pydantic.v1.class_validators",
        }
    ),
    "field_validator": frozenset(
        {"pydantic", "pydantic.functional_validators"}
    ),
    "model_validator": frozenset(
        {"pydantic", "pydantic.functional_validators"}
    ),
}
DEFAULT_EXCLUDED_PARTS = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "alembic",
    "build",
    "dist",
    "env",
    "htmlcov",
    "migrations",
    "node_modules",
    "site-packages",
    "test",
    "tests",
    "venv",
}
SENSITIVE_NAME_PATTERN = re.compile(
    r"(?:^|[_\-.])(authorization|auth|credential|credentials|cookie|password|passwd|private[_-]?key|"
    r"client[_-]?secret|api[_-]?key|access[_-]?key|refresh[_-]?token|"
    r"access[_-]?token|token|secret|dsn)(?:$|[_\-.])",
    re.IGNORECASE,
)
NON_SECRET_METADATA_NAME_PATTERN = re.compile(
    r"(?:authorization|auth|credential|credentials|cookie|password|passwd|"
    r"private_key|client_secret|api_key|access_key|refresh_token|access_token|"
    r"token|secret|dsn)_(?:enabled|expires|expiry|length|method|mode|name|policy|"
    r"present|provider|required|scheme|scope|status|ttl|type|url)$",
    re.IGNORECASE,
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"^Bearer\s+\S+$", re.IGNORECASE),
    re.compile(r"^eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"^[a-z][a-z0-9+.-]*://[^/@\s]+:[^/@\s]+@", re.IGNORECASE),
)


class ToolInputError(ValueError):
    """Raised when a CLI input cannot be interpreted safely."""


@dataclass(frozen=True)
class PythonSource:
    root: Path
    path: Path
    relative_path: str


def stable_json(value: Any, *, pretty: bool = False) -> str:
    """Serialize JSON deterministically and without ASCII escaping."""

    separators = None if pretty else (",", ":")
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2 if pretty else None,
        separators=separators,
        sort_keys=True,
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def raw_evidence_descriptor(evidence: Sequence[Any]) -> dict[str, Any]:
    """Describe the exact ordered scanner Evidence set with canonical JSON.

    The descriptor deliberately hashes the complete raw objects rather than a
    projection.  Any field edit, item insertion/deletion, or ordering change is
    therefore visible before workflow overlays are considered.
    """

    if not isinstance(evidence, (list, tuple)):
        raise TypeError("raw evidence must be a list or tuple")
    material = list(evidence)
    return {
        "format": RAW_EVIDENCE_FORMAT,
        "count": len(material),
        "sha256": sha256_text(stable_json(material)),
    }


def build_source_snapshot(
    repository: Mapping[str, Any],
    sources: Iterable[tuple[str, Path]],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Pin one scan to immutable aggregate and per-file content digests.

    A clean or dirty Git checkout keeps its full commit SHA as ``revision`` while
    ``snapshot_id`` identifies the exact selected file contents.  A non-Git tree
    uses the aggregate content digest itself as its immutable revision.  Paths in
    the digest material are authorized, repository-relative display paths only;
    absolute local paths never enter the artifact.
    """

    file_hashes: dict[str, str] = {}
    for relative_path, path in sorted(sources, key=lambda item: item[0]):
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ToolInputError(
                f"cannot hash source file {relative_path!r}: {exc}"
            ) from exc
        file_hashes[relative_path] = hashlib.sha256(content).hexdigest()

    raw_revision = repository.get("revision")
    git_revision = (
        raw_revision.strip().lower()
        if isinstance(raw_revision, str)
        and re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", raw_revision.strip())
        else None
    )
    snapshot_kind = "git" if git_revision else "content"
    snapshot_material = {
        "repository": str(repository.get("repository") or "source-snapshot"),
        "base_revision": git_revision,
        "dirty": bool(repository.get("dirty")) if git_revision else False,
        "files": [
            {"file": relative_path, "content_sha256": digest}
            for relative_path, digest in sorted(file_hashes.items())
        ],
    }
    snapshot_id = sha256_text(stable_json(snapshot_material))
    pinned = dict(repository)
    pinned.update(
        {
            "revision": git_revision or f"sha256:{snapshot_id}",
            "dirty": bool(repository.get("dirty")) if git_revision else False,
            "snapshot_kind": snapshot_kind,
            "snapshot_id": snapshot_id,
            "source_file_count": len(file_hashes),
        }
    )
    return pinned, file_hashes


def is_sensitive_name(value: str | None) -> bool:
    if not value:
        return False
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    if NON_SECRET_METADATA_NAME_PATTERN.search(normalized):
        return False
    return bool(SENSITIVE_NAME_PATTERN.search(normalized))


def redact_scalar(value: Any, *, name: str | None = None) -> Any:
    if is_sensitive_name(name):
        return "<redacted>"
    if isinstance(value, str) and any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
        return "<redacted>"
    if isinstance(value, list):
        return [redact_scalar(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): redact_scalar(item, name=str(key)) for key, item in value.items()
        }
    return value


def repository_metadata(scan_path: str) -> dict[str, Any]:
    """Return best-effort, read-only Git metadata for traceability."""

    path = Path(scan_path).expanduser().resolve()
    cwd = path.parent if path.is_file() else path
    fallback = {
        "repository": cwd.name,
        "revision": None,
        "dirty": None,
        "root": cwd.name,
    }
    try:
        root_result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        git_root = Path(root_result.stdout.strip()).resolve()
        revision_result = subprocess.run(
            ["git", "-C", str(git_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        dirty_result = subprocess.run(
            ["git", "-C", str(git_root), "status", "--porcelain", "--untracked-files=normal"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return fallback
    return {
        "repository": git_root.name,
        "revision": revision_result.stdout.strip() or None,
        "dirty": bool(dirty_result.stdout.strip()),
        "root": git_root.name,
    }


def write_output(path: str | None, text: str) -> None:
    """Write output to a file, or stdout when path is '-' or omitted."""

    if not path or path == "-":
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    output = Path(path).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")


def parse_patterns(values: Sequence[str] | None) -> list[str]:
    patterns: list[str] = []
    for value in values or ():
        patterns.extend(part.strip() for part in value.split(",") if part.strip())
    return patterns


def _matches_pattern(relative_path: str, pattern: str) -> bool:
    normalized = pattern.replace(os.sep, "/")
    candidates = [normalized]
    if normalized.startswith("**/"):
        candidates.append(normalized[3:])
    return any(
        fnmatch.fnmatch(relative_path, candidate)
        or fnmatch.fnmatch(Path(relative_path).name, candidate)
        for candidate in candidates
    )


def ensure_bounded_scan_root(path: Path, *, label: str = "scan path") -> None:
    """Reject roots that would turn a repository scan into a machine/home crawl."""

    resolved = path.expanduser().resolve()
    anchor = Path(resolved.anchor).resolve()
    home = Path.home().resolve()
    if resolved == anchor or resolved.parent == anchor or resolved == home:
        raise ToolInputError(
            f"{label} is too broad for code scanning: {str(resolved)!r}; "
            "select the exact repository, service, module, or source file"
        )


def discover_python_sources(
    inputs: Sequence[str],
    *,
    include: Sequence[str] = (),
    exclude: Sequence[str] = (),
    default_excludes: bool = True,
) -> tuple[list[PythonSource], list[dict[str, str]]]:
    """Return stable Python source candidates and skipped-path reasons."""

    if not inputs:
        raise ToolInputError("at least one scan path is required")
    roots: list[Path] = []
    for raw in inputs:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            raise ToolInputError(f"scan path does not exist: {raw!r}")
        if not (path.is_dir() or (path.is_file() and path.suffix == ".py")):
            raise ToolInputError(f"scan path is not a directory or Python file: {raw!r}")
        if path.is_dir():
            ensure_bounded_scan_root(path)
        roots.append(path)

    multiple_roots = len(roots) > 1
    sources: list[PythonSource] = []
    skipped: list[dict[str, str]] = []
    seen_paths: set[Path] = set()
    for root in roots:
        candidates: Iterable[Path] = [root] if root.is_file() else root.rglob("*.py")
        for path in candidates:
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            base = root.parent if root.is_file() else root
            try:
                local_relative = resolved.relative_to(base).as_posix()
            except ValueError as exc:
                raise ToolInputError(
                    f"source path escapes the authorized scan root through a symlink: {path}"
                ) from exc
            relative = (
                f"{root.name}/{local_relative}" if multiple_roots and root.is_dir() else local_relative
            )
            parts = set(Path(local_relative).parts[:-1])
            if default_excludes and parts.intersection(DEFAULT_EXCLUDED_PARTS):
                skipped.append({"path": relative, "reason": "default_exclude"})
                continue
            if include and not any(_matches_pattern(relative, pattern) for pattern in include):
                skipped.append({"path": relative, "reason": "not_included"})
                continue
            if exclude and any(_matches_pattern(relative, pattern) for pattern in exclude):
                skipped.append({"path": relative, "reason": "excluded"})
                continue
            sources.append(PythonSource(root=base, path=resolved, relative_path=relative))
    sources.sort(key=lambda item: item.relative_path)
    skipped.sort(key=lambda item: (item["path"], item["reason"]))
    return sources, skipped


def parse_source(source: PythonSource) -> tuple[str, ast.Module]:
    try:
        text = source.path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = source.path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as exc:
            raise ToolInputError(f"cannot decode {source.relative_path}: {exc}") from exc
    except OSError as exc:
        raise ToolInputError(f"cannot read {source.relative_path}: {exc}") from exc
    try:
        return text, ast.parse(text, filename=source.relative_path, type_comments=True)
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno else "unknown line"
        raise ToolInputError(f"cannot parse {source.relative_path} ({location}): {exc.msg}") from exc


def dotted_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


class _ModuleBindingCollector(ast.NodeVisitor):
    """Collect non-import module bindings that make an import name ambiguous."""

    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.names.add(node.name)

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        return

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        return


class AstImportResolver:
    """Resolve symbol provenance from unconditional module-level AST imports only.

    The resolver never imports or executes project code. Multiple possible sources,
    relative/project re-exports, local rebinding, and runtime-conditional imports all
    fail closed.
    """

    def __init__(self, tree: ast.Module) -> None:
        self.direct_symbols: dict[str, set[tuple[str, str]]] = {}
        self.module_aliases: dict[str, set[str]] = {}
        self.wildcard_modules: set[str] = set()
        bindings = _ModuleBindingCollector()
        bindings.visit(tree)
        self.shadowed_names = bindings.names

        for statement in tree.body:
            if isinstance(statement, ast.ImportFrom) and statement.level == 0:
                module = statement.module or ""
                for alias in statement.names:
                    if alias.name == "*":
                        if module:
                            self.wildcard_modules.add(module)
                        continue
                    local_name = alias.asname or alias.name
                    self.direct_symbols.setdefault(local_name, set()).add(
                        (module, alias.name)
                    )
            elif isinstance(statement, ast.Import):
                for alias in statement.names:
                    local_name = alias.asname or alias.name.split(".", 1)[0]
                    imported_module = (
                        alias.name if alias.asname else alias.name.split(".", 1)[0]
                    )
                    self.module_aliases.setdefault(local_name, set()).add(
                        imported_module
                    )

    def candidates(self, node: ast.AST | None) -> set[tuple[str, str]]:
        name = dotted_name(node)
        if not name:
            return set()
        parts = name.split(".")
        root = parts[0]
        if root in self.shadowed_names:
            return set()
        if len(parts) == 1:
            candidates = set(self.direct_symbols.get(root, set()))
            if candidates:
                return candidates
            return {(module, root) for module in self.wildcard_modules}

        candidates: set[tuple[str, str]] = set()
        for imported_module in self.module_aliases.get(root, set()):
            module = ".".join([imported_module, *parts[1:-1]])
            candidates.add((module, parts[-1]))
        for imported_module, imported_symbol in self.direct_symbols.get(root, set()):
            module = ".".join(
                [imported_module, imported_symbol, *parts[1:-1]]
            )
            candidates.add((module, parts[-1]))
        return candidates

    def official_symbol(
        self,
        node: ast.AST | None,
        allowed_modules: Mapping[str, frozenset[str]],
    ) -> str | None:
        candidates = self.candidates(node)
        if len(candidates) != 1:
            return None
        module, symbol = next(iter(candidates))
        return symbol if module in allowed_modules.get(symbol, frozenset()) else None

    def candidate_symbol(
        self,
        node: ast.AST | None,
        names: set[str] | frozenset[str],
    ) -> str | None:
        candidates = {symbol for _module, symbol in self.candidates(node) if symbol in names}
        if len(candidates) == 1:
            return next(iter(candidates))
        dotted = dotted_name(node) or ""
        parts = dotted.split(".") if dotted else []
        root = parts[0] if parts else ""
        imported_candidates = {
            symbol
            for _module, symbol in self.direct_symbols.get(root, set())
            if symbol in names
        }
        if len(imported_candidates) == 1:
            return next(iter(imported_candidates))
        terminal = dotted.rsplit(".", 1)[-1]
        return terminal if terminal in names else None


def _expression_name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        slice_node = node.slice
        if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
            return slice_node.value
    return ""


class _SecretRedactor(ast.NodeTransformer):
    def visit_Constant(self, node: ast.Constant) -> ast.AST:  # noqa: N802
        if isinstance(node.value, str) and redact_scalar(node.value) == "<redacted>":
            return ast.copy_location(ast.Constant(value="<redacted>"), node)
        return node

    def visit_keyword(self, node: ast.keyword) -> ast.AST:  # noqa: N802
        if is_sensitive_name(node.arg):
            node.value = ast.copy_location(ast.Constant(value="<redacted>"), node.value)
            return node
        return self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> ast.AST:  # noqa: N802
        if any(is_sensitive_name(_expression_name(target)) for target in node.targets):
            node.value = ast.copy_location(ast.Constant(value="<redacted>"), node.value)
            return node
        return self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST:  # noqa: N802
        if node.value is not None and is_sensitive_name(_expression_name(node.target)):
            node.value = ast.copy_location(ast.Constant(value="<redacted>"), node.value)
            return node
        return self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)
        if is_sensitive_name(_expression_name(node.left)):
            node.comparators = [
                ast.copy_location(ast.Constant(value="<redacted>"), comparator)
                for comparator in node.comparators
            ]
        return node

    def visit_Dict(self, node: ast.Dict) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)
        for index, key in enumerate(node.keys):
            if (
                isinstance(key, ast.Constant)
                and isinstance(key.value, str)
                and is_sensitive_name(key.value)
            ):
                node.values[index] = ast.copy_location(
                    ast.Constant(value="<redacted>"), node.values[index]
                )
        return node

    def visit_Call(self, node: ast.Call) -> ast.AST:  # noqa: N802
        node = self.generic_visit(node)
        if is_sensitive_name(_expression_name(node.func)):
            node.args = [
                ast.copy_location(ast.Constant(value="<redacted>"), argument)
                for argument in node.args
            ]
        return node


def render_node(node: ast.AST | None, *, sensitive_context: str | None = None) -> str:
    if node is None:
        return ""
    if is_sensitive_name(sensitive_context):
        return "<redacted>"
    try:
        safe_node = _SecretRedactor().visit(copy.deepcopy(node))
        ast.fix_missing_locations(safe_node)
        return ast.unparse(safe_node).strip()
    except Exception:  # pragma: no cover - fallback for future AST nodes
        return ast.dump(node, annotate_fields=True, include_attributes=False)


def static_value(node: ast.AST | None) -> Any:
    """Evaluate JSON-like literals and simple string concatenation only."""

    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = [static_value(item) for item in node.elts]
        if all(value is not _UNKNOWN for value in values):
            return values
        return _UNKNOWN
    if isinstance(node, ast.Dict):
        keys = [static_value(item) for item in node.keys]
        values = [static_value(item) for item in node.values]
        if all(value is not _UNKNOWN for value in keys + values):
            try:
                return dict(zip(keys, values))
            except TypeError:
                return _UNKNOWN
        return _UNKNOWN
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = static_value(node.left)
        right = static_value(node.right)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
        return _UNKNOWN
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                return _UNKNOWN
            parts.append(value.value)
        return "".join(parts)
    return _UNKNOWN


class _Unknown:
    pass


_UNKNOWN = _Unknown()


def keyword_node(call: ast.Call, name: str) -> ast.AST | None:
    return next((keyword.value for keyword in call.keywords if keyword.arg == name), None)


def normalize_route_path(path: str) -> str:
    compact = "/".join(part for part in path.strip().split("/") if part)
    return f"/{compact}" if compact else "/"


def route_matches_prefix(path: str, prefix: str | None) -> bool:
    """Return whether *path* is inside the requested route-prefix boundary."""

    if not prefix:
        return True
    normalized_path = normalize_route_path(path)
    normalized_prefix = normalize_route_path(prefix)
    if normalized_prefix == "/":
        return True
    return normalized_path == normalized_prefix or normalized_path.startswith(
        normalized_prefix + "/"
    )


def infer_api_version(path: str) -> tuple[str, str]:
    """Return an explicit API version and the source used to derive it."""

    match = re.search(r"(?:^|/)(v[0-9]+)(?:/|$)", path, re.IGNORECASE)
    if match:
        return match.group(1).lower(), "path"
    return "unversioned", "none"


def join_route_paths(prefix: str, path: str) -> str:
    if not prefix:
        return normalize_route_path(path)
    return normalize_route_path(f"{prefix.rstrip('/')}/{path.lstrip('/')}")


def _join_router_prefixes(*prefixes: str) -> str:
    result = ""
    for prefix in prefixes:
        if not prefix:
            continue
        result = join_route_paths(result, prefix)
    return result


def annotated_parts(annotation: ast.AST | None) -> tuple[ast.AST | None, list[ast.AST]]:
    """Split ``Annotated[T, ...]`` into its base annotation and metadata nodes."""

    if not isinstance(annotation, ast.Subscript):
        return annotation, []
    annotation_name = (dotted_name(annotation.value) or "").rsplit(".", 1)[-1]
    if annotation_name != "Annotated":
        return annotation, []
    slice_node = annotation.slice
    items = list(slice_node.elts) if isinstance(slice_node, ast.Tuple) else [slice_node]
    if not items:
        return annotation, []
    return items[0], items[1:]


def annotation_binding(
    annotation: ast.AST | None,
    import_resolver: AstImportResolver,
) -> dict[str, Any] | None:
    """Return the first FastAPI parameter-binding call from Annotated metadata."""

    _base, metadata = annotated_parts(annotation)
    for meta in metadata:
        if not isinstance(meta, ast.Call):
            continue
        name = import_resolver.official_symbol(
            meta.func,
            FASTAPI_PARAMETER_SYMBOL_MODULES,
        )
        if name is not None:
            return {
                "name": name,
                "expression": render_node(meta),
            }
    return None


_RUNTIME_REGISTRATION_CONTEXTS = tuple(
    node_type
    for node_type in (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.Try,
        getattr(ast, "TryStar", None),
        ast.With,
        ast.AsyncWith,
        getattr(ast, "Match", None),
    )
    if node_type is not None
)


class _RegistrationContextCollector(ast.NodeVisitor):
    """Record runtime ancestors without mistaking top-level declarations as conditional."""

    def __init__(self) -> None:
        self.contexts: dict[int, tuple[str, ...]] = {}
        self.stack: list[str] = []
        self.function_depth = 0

    def generic_visit(self, node: ast.AST) -> None:
        self.contexts[id(node)] = tuple(self.stack)
        if isinstance(node, _RUNTIME_REGISTRATION_CONTEXTS):
            self.stack.append(type(node).__name__)
            super().generic_visit(node)
            self.stack.pop()
            return
        super().generic_visit(node)

    def _function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.contexts[id(node)] = tuple(self.stack)
        self.stack.append(f"function_body:{node.name}")
        self.function_depth += 1
        super().generic_visit(node)
        self.function_depth -= 1
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._function(node)


def _registration_contexts(tree: ast.Module) -> dict[int, tuple[str, ...]]:
    collector = _RegistrationContextCollector()
    collector.visit(tree)
    return collector.contexts


def _conditional_registration_context(
    contexts: Mapping[int, tuple[str, ...]], node: ast.AST
) -> tuple[str, ...]:
    return contexts.get(id(node), ())


def _assignment_target_value(node: ast.AST) -> tuple[ast.AST | None, ast.AST | None]:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        return node.targets[0], node.value
    if isinstance(node, ast.AnnAssign):
        return node.target, node.value
    return None, None


def _collect_router_declarations(tree: ast.Module) -> dict[str, dict[str, Any]]:
    declarations: dict[str, dict[str, Any]] = {}
    contexts = _registration_contexts(tree)
    import_resolver = AstImportResolver(tree)
    for node in ast.walk(tree):
        target, value = _assignment_target_value(node)
        if not isinstance(value, ast.Call):
            continue
        if import_resolver.official_symbol(
            value.func,
            FASTAPI_ROUTER_SYMBOL_MODULES,
        ) != "APIRouter":
            continue
        runtime_context = _conditional_registration_context(contexts, node)
        if runtime_context:
            continue
        target_name = dotted_name(target)
        prefix_node = keyword_node(value, "prefix")
        prefix = "" if prefix_node is None else static_value(prefix_node)
        if target_name:
            declarations[target_name] = {
                "prefix": prefix if isinstance(prefix, str) else None,
                "prefix_is_static": isinstance(prefix, str),
                "line": getattr(value, "lineno", None),
                "expression": render_node(value),
            }
    return declarations


def _is_application_constructor(
    call: ast.Call,
    import_resolver: AstImportResolver,
) -> bool:
    return import_resolver.official_symbol(
        call.func,
        FASTAPI_APPLICATION_SYMBOL_MODULES,
    ) is not None


def _collect_application_declarations(tree: ast.Module) -> set[str]:
    import_resolver = AstImportResolver(tree)
    applications: set[str] = set()
    contexts = _registration_contexts(tree)
    for statement in ast.walk(tree):
        target, value = _assignment_target_value(statement)
        if not isinstance(value, ast.Call) or not _is_application_constructor(
            value, import_resolver
        ):
            continue
        if _conditional_registration_context(contexts, statement):
            continue
        target_name = dotted_name(target)
        if target_name:
            applications.add(target_name)
    return applications


def python_module_name(relative_path: str) -> str:
    """Return a stable dotted module name for a source-relative Python path."""

    path = PurePosixPath(relative_path)
    parts = list(path.parts)
    if not parts:
        return ""
    filename = parts.pop()
    stem = filename[:-3] if filename.endswith(".py") else filename
    if stem != "__init__":
        parts.append(stem)
    return ".".join(part for part in parts if part)


def _python_package_name(relative_path: str) -> str:
    module = python_module_name(relative_path)
    if PurePosixPath(relative_path).name == "__init__.py":
        return module
    return module.rpartition(".")[0]


def _lookup_router_identity(
    module: str,
    symbol: str,
    known: set[tuple[str, str]],
) -> tuple[str, str] | None:
    exact = (module, symbol)
    if exact in known:
        return exact
    suffix_matches = {
        identity
        for identity in known
        if identity[1] == symbol
        and module
        and identity[0]
        and (
            module.endswith(f".{identity[0]}")
            or identity[0].endswith(f".{module}")
        )
    }
    if len(suffix_matches) == 1:
        return next(iter(suffix_matches))
    symbol_matches = {identity for identity in known if identity[1] == symbol}
    return next(iter(symbol_matches)) if len(symbol_matches) == 1 else None


def _router_import_context(
    tree: ast.Module,
    relative_path: str,
    known: set[tuple[str, str]],
) -> tuple[dict[str, tuple[str, str]], dict[str, str]]:
    current_module = python_module_name(relative_path)
    current_package = _python_package_name(relative_path)
    direct: dict[str, tuple[str, str]] = {
        symbol: (current_module, symbol)
        for module, symbol in known
        if module == current_module
    }
    module_aliases: dict[str, str] = {}
    for statement in tree.body:
        if isinstance(statement, ast.ImportFrom):
            imported_module = _resolve_import_from_module(
                current_package,
                level=statement.level,
                module=statement.module,
            )
            for alias in statement.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                identity = _lookup_router_identity(imported_module, alias.name, known)
                if identity is not None:
                    direct[local_name] = identity
                    continue
                module_aliases[local_name] = ".".join(
                    part for part in (imported_module, alias.name) if part
                )
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.asname:
                    module_aliases[alias.asname] = alias.name
                else:
                    root_name = alias.name.split(".", 1)[0]
                    module_aliases[root_name] = root_name
    return direct, module_aliases


def _resolve_router_reference(
    node: ast.AST | None,
    direct: Mapping[str, tuple[str, str]],
    module_aliases: Mapping[str, str],
    known: set[tuple[str, str]],
) -> tuple[str, str] | None:
    expression = dotted_name(node)
    if not expression:
        return None
    if expression in direct:
        return direct[expression]
    parts = expression.split(".")
    if len(parts) == 1:
        return None
    imported_module = module_aliases.get(parts[0])
    if imported_module is None:
        return None
    if len(parts) > 2:
        imported_module = ".".join([imported_module, *parts[1:-1]])
    return _lookup_router_identity(imported_module, parts[-1], known)


def _routing_gap_warning(
    code: str,
    message: str,
    relative_path: str,
    node: ast.AST,
    *,
    symbol: str | None = None,
    missing_evidence: Sequence[str],
    affected_scope: str = "当前接口",
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "path": relative_path,
        "line": getattr(node, "lineno", None),
        "symbol": symbol,
        "disposition": "needs_confirmation",
        "affected_scope": affected_scope,
        "missing_evidence": list(missing_evidence),
        "next_action": "resolve the static route registration or reconcile it with runtime OpenAPI",
        "safe_resumption_point": "resume endpoint discovery before generating route evidence",
    }


def _conditional_fastapi_declaration_warnings(
    tree: ast.Module,
    relative_path: str,
) -> list[dict[str, Any]]:
    contexts = _registration_contexts(tree)
    import_resolver = AstImportResolver(tree)
    warnings: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        target, value = _assignment_target_value(node)
        if not isinstance(value, ast.Call):
            continue
        runtime_context = _conditional_registration_context(contexts, node)
        if not runtime_context:
            continue
        is_router = import_resolver.official_symbol(
            value.func,
            FASTAPI_ROUTER_SYMBOL_MODULES,
        ) == "APIRouter"
        is_application = _is_application_constructor(value, import_resolver)
        if not is_router and not is_application:
            continue
        symbol = dotted_name(target) or render_node(target)
        kind = "router" if is_router else "application"
        warning = _routing_gap_warning(
            (
                "FASTAPI_ROUTER_DECLARATION_CONDITIONAL"
                if is_router
                else "FASTAPI_APPLICATION_DECLARATION_CONDITIONAL"
            ),
            (
                f"{kind} declaration occurs in a conditional/runtime context; "
                "it was excluded from route and mount inference"
            ),
            relative_path,
            node,
            symbol=symbol or None,
            missing_evidence=[
                "unconditional application/router declaration",
                "runtime activation and registration outcome",
            ],
            affected_scope="全项目",
        )
        warning["runtime_context"] = list(runtime_context)
        warnings.append(warning)
    return warnings


def _conditional_fastapi_declaration_symbols(tree: ast.Module) -> set[str]:
    contexts = _registration_contexts(tree)
    import_resolver = AstImportResolver(tree)
    symbols: set[str] = set()
    for node in ast.walk(tree):
        target, value = _assignment_target_value(node)
        if not isinstance(value, ast.Call) or not _conditional_registration_context(
            contexts, node
        ):
            continue
        is_router = import_resolver.official_symbol(
            value.func,
            FASTAPI_ROUTER_SYMBOL_MODULES,
        ) == "APIRouter"
        if not is_router and not _is_application_constructor(value, import_resolver):
            continue
        symbol = dotted_name(target)
        if symbol:
            symbols.add(symbol)
    return symbols


def collect_router_prefix_registry(
    parsed_modules: Iterable[tuple[str, ast.Module]],
    *,
    warnings: list[dict[str, Any]] | None = None,
) -> dict[tuple[str, str], tuple[str, ...]]:
    """Resolve APIRouter prefixes, including common cross-module include_router calls."""

    modules = list(parsed_modules)
    declarations: dict[tuple[str, str], dict[str, Any]] = {}
    application_identities: set[tuple[str, str]] = set()
    source_by_module: dict[str, str] = {}
    for relative_path, tree in modules:
        module = python_module_name(relative_path)
        source_by_module[module] = relative_path
        for symbol, declaration in _collect_router_declarations(tree).items():
            declarations[(module, symbol)] = declaration
        for symbol in _collect_application_declarations(tree):
            application_identities.add((module, symbol))

    known = set(declarations)
    warning_sink = warnings if warnings is not None else []
    for relative_path, tree in modules:
        warning_sink.extend(
            _conditional_fastapi_declaration_warnings(tree, relative_path)
        )
    warned_router_identities: set[tuple[str, str]] = set()
    for identity, declaration in sorted(declarations.items()):
        if declaration.get("prefix_is_static"):
            continue
        module, symbol = identity
        warned_router_identities.add(identity)
        warning_sink.append(
            _routing_gap_warning(
                "FASTAPI_ROUTER_PREFIX_UNRESOLVED",
                f"APIRouter prefix for {module}.{symbol} is dynamic; mounted paths were skipped",
                source_by_module.get(module, module),
                ast.Constant(value=None, lineno=declaration.get("line") or 0),
                symbol=f"{module}.{symbol}",
                missing_evidence=["static APIRouter prefix", "resolved mounted endpoint path"],
            )
        )

    edges: list[tuple[tuple[str, str] | None, tuple[str, str], str]] = []
    for relative_path, tree in modules:
        direct, module_aliases = _router_import_context(tree, relative_path, known)
        application_direct, application_modules = _router_import_context(
            tree, relative_path, application_identities
        )
        registration_contexts = _registration_contexts(tree)
        for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
            if not isinstance(call.func, ast.Attribute) or call.func.attr != "include_router":
                continue
            router_node = call.args[0] if call.args else keyword_node(call, "router")
            runtime_context = _conditional_registration_context(
                registration_contexts, call
            )
            if runtime_context:
                warning = _routing_gap_warning(
                    "FASTAPI_INCLUDE_ROUTER_CONDITIONAL",
                    "include_router occurs in a conditional/runtime context; no mount edge was inferred",
                    relative_path,
                    call,
                    symbol=render_node(router_node) or None,
                    missing_evidence=[
                        "unconditional include_router registration",
                        "runtime activation and mount outcome",
                    ],
                    affected_scope="全项目",
                )
                warning["runtime_context"] = list(runtime_context)
                warning_sink.append(warning)
                continue
            router_identity = _resolve_router_reference(
                router_node, direct, module_aliases, known
            )
            if router_identity is None:
                warning_sink.append(
                    _routing_gap_warning(
                        "FASTAPI_INCLUDE_ROUTER_TARGET_UNRESOLVED",
                        "include_router target could not be resolved statically; no mounted path was inferred",
                        relative_path,
                        call,
                        symbol=render_node(router_node) or None,
                        missing_evidence=["statically resolvable router import/assignment"],
                        affected_scope="全项目",
                    )
                )
                continue
            prefix_node = keyword_node(call, "prefix")
            prefix_value = "" if prefix_node is None else static_value(prefix_node)
            if not isinstance(prefix_value, str):
                warned_router_identities.add(router_identity)
                warning_sink.append(
                    _routing_gap_warning(
                        "FASTAPI_INCLUDE_ROUTER_PREFIX_UNRESOLVED",
                        "include_router prefix is dynamic; affected mounted paths were skipped",
                        relative_path,
                        call,
                        symbol=".".join(router_identity),
                        missing_evidence=["static include_router prefix", "resolved mounted endpoint path"],
                    )
                )
                continue
            parent_identity = _resolve_router_reference(
                call.func.value, direct, module_aliases, known
            )
            if parent_identity is not None:
                edges.append((parent_identity, router_identity, prefix_value))
                continue
            application_identity = _resolve_router_reference(
                call.func.value,
                application_direct,
                application_modules,
                application_identities,
            )
            if application_identity is not None:
                edges.append((None, router_identity, prefix_value))
                continue
            warned_router_identities.add(router_identity)
            warning_sink.append(
                _routing_gap_warning(
                    "FASTAPI_INCLUDE_ROUTER_PARENT_UNRESOLVED",
                    "include_router receiver is not a statically confirmed FastAPI, Starlette, or APIRouter instance; affected routes were skipped",
                    relative_path,
                    call,
                    symbol=render_node(call.func.value) or None,
                    missing_evidence=[
                        "statically resolved FastAPI/Starlette application or APIRouter parent"
                    ],
                )
            )

    effective: dict[tuple[str, str], set[str]] = {}
    for parent, child, include_prefix in edges:
        child_prefix = declarations[child].get("prefix")
        if parent is None and isinstance(child_prefix, str):
            effective.setdefault(child, set()).add(
                _join_router_prefixes(include_prefix, child_prefix)
            )

    for _ in range(max(1, len(declarations))):
        changed = False
        for parent, child, include_prefix in edges:
            if parent is None:
                continue
            child_prefix = declarations[child].get("prefix")
            if not isinstance(child_prefix, str):
                continue
            for parent_prefix in effective.get(parent, set()):
                mounted = _join_router_prefixes(
                    parent_prefix, include_prefix, child_prefix
                )
                target = effective.setdefault(child, set())
                if mounted not in target:
                    target.add(mounted)
                    changed = True
        if not changed:
            break

    for identity, declaration in sorted(declarations.items()):
        if effective.get(identity) or identity in warned_router_identities:
            continue
        module, symbol = identity
        warning_sink.append(
            _routing_gap_warning(
                "FASTAPI_ROUTER_MOUNT_UNRESOLVED",
                f"APIRouter {module}.{symbol} has no statically resolved mount chain; its routes were skipped",
                source_by_module.get(module, module),
                ast.Constant(value=None, lineno=declaration.get("line") or 0),
                symbol=f"{module}.{symbol}",
                missing_evidence=[
                    "include_router mount chain from a FastAPI/Starlette application",
                    "resolved mounted endpoint path",
                ],
            )
        )

    return {
        identity: tuple(sorted(effective.get(identity, set())))
        for identity in sorted(declarations)
    }


def _resolve_import_from_module(
    current_package: str,
    *,
    level: int,
    module: str | None,
) -> str:
    if level <= 0:
        return module or ""
    package_parts = [part for part in current_package.split(".") if part]
    parents_to_remove = max(0, level - 1)
    if parents_to_remove >= len(package_parts):
        base_parts: list[str] = []
    else:
        base_parts = package_parts[: len(package_parts) - parents_to_remove]
    if module:
        base_parts.extend(part for part in module.split(".") if part)
    return ".".join(base_parts)


def resolve_router_prefixes(
    tree: ast.Module,
    relative_path: str,
    registry: Mapping[tuple[str, str], str | Sequence[str]],
) -> dict[str, str | tuple[str, ...]]:
    """Resolve local and explicitly imported APIRouter symbols across scan files.

    Prefer exact module+symbol matches. Fall back to a globally unique symbol only
    for absolute imports whose package prefix lies outside the selected scan root.
    This avoids treating every common variable named ``router`` as the same object.
    """

    known = set(registry)
    direct, module_aliases = _router_import_context(tree, relative_path, known)
    resolved: dict[str, str | tuple[str, ...]] = {}

    for local_name, identity in direct.items():
        value = registry.get(identity)
        if value is not None:
            resolved[local_name] = (
                value if isinstance(value, str) else tuple(value)
            )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        receiver = dotted_name(node.func.value)
        if not receiver:
            continue
        identity = _resolve_router_reference(
            node.func.value, direct, module_aliases, known
        )
        if identity is None:
            continue
        value = registry.get(identity)
        if value is not None:
            resolved[receiver] = value if isinstance(value, str) else tuple(value)
    return resolved


def _module_route_decorator_aliases(
    tree: ast.Module,
) -> tuple[dict[str, tuple[str, str]], set[str]]:
    candidates: dict[str, list[tuple[str, str]]] = {}
    unsafe: set[str] = set()
    contexts = _registration_contexts(tree)
    for node in ast.walk(tree):
        target, value = _assignment_target_value(node)
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Attribute):
            continue
        decorator_name = value.attr.lower()
        if decorator_name not in HTTP_DECORATORS and decorator_name not in {
            "api_route",
            "route",
        }:
            continue
        receiver = dotted_name(value.value)
        if not receiver:
            unsafe.add(target.id)
            continue
        if node not in tree.body or _conditional_registration_context(contexts, node):
            unsafe.add(target.id)
            continue
        candidates.setdefault(target.id, []).append((receiver, decorator_name))
    aliases: dict[str, tuple[str, str]] = {}
    for name, values in candidates.items():
        if name in unsafe or len(set(values)) != 1:
            unsafe.add(name)
            continue
        aliases[name] = values[0]
    return aliases, unsafe


def _route_decorator_target(
    decorator: ast.AST,
    aliases: Mapping[str, tuple[str, str]],
) -> tuple[ast.Call, str, str] | None:
    if not isinstance(decorator, ast.Call):
        return None
    if isinstance(decorator.func, ast.Attribute):
        decorator_name = decorator.func.attr.lower()
        receiver = dotted_name(decorator.func.value) or render_node(decorator.func.value)
    elif isinstance(decorator.func, ast.Name) and decorator.func.id in aliases:
        receiver, decorator_name = aliases[decorator.func.id]
    else:
        return None
    if decorator_name not in HTTP_DECORATORS and decorator_name not in {
        "api_route",
        "route",
    }:
        return None
    return decorator, receiver, decorator_name


def extract_route_decorator(
    decorator: ast.AST,
    router_prefixes: Mapping[str, str | Sequence[str]],
    decorator_aliases: Mapping[str, tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    target = _route_decorator_target(decorator, decorator_aliases or {})
    if target is None:
        return []
    decorator, receiver, decorator_name = target
    if receiver not in router_prefixes:
        return []
    path_node = decorator.args[0] if decorator.args else keyword_node(decorator, "path")
    path_value = static_value(path_node)
    if not isinstance(path_value, str):
        return []
    declared_path = path_value

    configured_prefixes = router_prefixes[receiver]
    if isinstance(configured_prefixes, str):
        prefixes = (configured_prefixes,)
    else:
        prefixes = tuple(configured_prefixes)
    if not prefixes:
        return []

    if decorator_name in {"api_route", "route"}:
        methods_node = keyword_node(decorator, "methods")
        raw_methods = static_value(methods_node)
        if methods_node is None or raw_methods is None:
            methods = ["GET"]
        elif isinstance(raw_methods, list) and raw_methods:
            methods = [str(method).upper() for method in raw_methods]
        else:
            return []
    else:
        methods = list(HTTP_DECORATORS[decorator_name])
    result: list[dict[str, Any]] = []
    for prefix in sorted(set(prefixes)):
        path = join_route_paths(prefix, declared_path)
        for method in sorted(set(methods)):
            result.append(
                {
                    "method": method,
                    "path": path,
                    "declared_path": declared_path,
                    "path_is_static": True,
                    "router": receiver,
                    "router_prefix": prefix,
                    "decorator": render_node(decorator),
                    "decorator_line": getattr(decorator, "lineno", None),
                }
            )
    return result


def collect_fastapi_route_warnings(
    tree: ast.Module,
    relative_path: str,
    router_prefixes: Mapping[str, str | Sequence[str]] | None = None,
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    registration_contexts = _registration_contexts(tree)
    known_receivers: dict[str, str | Sequence[str]] = {
        symbol: () for symbol in _collect_router_declarations(tree)
    }
    known_receivers.update(
        {symbol: "" for symbol in _collect_application_declarations(tree)}
    )
    known_receivers.update(router_prefixes or {})
    for symbol in _conditional_fastapi_declaration_symbols(tree):
        known_receivers.pop(symbol, None)
    decorator_aliases, unsafe_aliases = _module_route_decorator_aliases(tree)
    import_resolver = AstImportResolver(tree)

    constructor_modules = {
        **FASTAPI_ROUTER_SYMBOL_MODULES,
        **FASTAPI_APPLICATION_SYMBOL_MODULES,
    }
    for node in ast.walk(tree):
        target, value = _assignment_target_value(node)
        if not isinstance(value, ast.Call):
            continue
        candidate = import_resolver.candidate_symbol(
            value.func,
            set(constructor_modules),
        )
        if candidate is None or import_resolver.official_symbol(
            value.func,
            constructor_modules,
        ) is not None:
            continue
        kind = "router" if candidate == "APIRouter" else "application"
        warnings.append(
            _routing_gap_warning(
                (
                    "FASTAPI_ROUTER_CONSTRUCTOR_SOURCE_UNRESOLVED"
                    if kind == "router"
                    else "FASTAPI_APPLICATION_CONSTRUCTOR_SOURCE_UNRESOLVED"
                ),
                (
                    f"{candidate} constructor source is not proven by an official "
                    "FastAPI/Starlette AST import; declaration was excluded"
                ),
                relative_path,
                value,
                symbol=dotted_name(target) or render_node(target) or None,
                missing_evidence=[
                    f"explicit official import provenance for {candidate}"
                ],
                affected_scope="全项目",
            )
        )

    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        registration_kind: str | None = None
        if isinstance(call.func, ast.Attribute) and call.func.attr in {
            "add_api_route",
            "add_route",
            "mount",
        }:
            registration_kind = f".{call.func.attr}(...)"
        elif (
            isinstance(call.func, ast.Attribute)
            and call.func.attr in {"append", "extend"}
            and isinstance(call.func.value, ast.Attribute)
            and call.func.value.attr == "routes"
        ):
            registration_kind = f".routes.{call.func.attr}(...)"
        elif _is_application_constructor(call, import_resolver):
            routes_node = keyword_node(call, "routes")
            routes_value = static_value(routes_node)
            if routes_node is not None and not (
                routes_value is None
                or (isinstance(routes_value, list) and not routes_value)
            ):
                registration_kind = "application constructor routes=..."
        if registration_kind is None:
            continue
        warning = _routing_gap_warning(
            "FASTAPI_PROGRAMMATIC_ROUTE_REGISTRATION_UNSUPPORTED",
            f"{registration_kind} programmatic registration is not fully parsed; route inventory is incomplete",
            relative_path,
            call,
            symbol=(
                render_node(call.func.value)
                if isinstance(call.func, ast.Attribute)
                else render_node(call.func)
            )
            or None,
            missing_evidence=[
                "AST adapter for programmatic route registration",
                "resolved runtime route or mount inventory",
            ],
            affected_scope="全项目",
        )
        runtime_context = _conditional_registration_context(
            registration_contexts, call
        )
        if runtime_context:
            warning["runtime_context"] = list(runtime_context)
        warnings.append(warning)

    for alias in sorted(unsafe_aliases):
        warnings.append(
            _routing_gap_warning(
                "FASTAPI_ROUTE_DECORATOR_ALIAS_UNRESOLVED",
                f"route decorator alias {alias!r} is conditional, nested, or ambiguous; aliased routes were skipped",
                relative_path,
                tree,
                symbol=alias,
                missing_evidence=["one unconditional module-level route decorator alias"],
                affected_scope="全项目",
            )
        )
    for symbol, function in iter_functions(tree):
        route_decorators = [
            decorator
            for decorator in function.decorator_list
            if _route_decorator_target(decorator, decorator_aliases) is not None
            or (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
                and decorator.func.id in unsafe_aliases
            )
        ]
        runtime_context = _conditional_registration_context(
            registration_contexts, function
        )
        if route_decorators and runtime_context:
            warning = _routing_gap_warning(
                "FASTAPI_ROUTE_REGISTRATION_CONDITIONAL",
                "route-decorated function occurs in a conditional/runtime or nested-function context; endpoint inference was skipped",
                relative_path,
                function,
                symbol=symbol,
                missing_evidence=[
                    "unconditional module/class route registration",
                    "runtime activation and registered route inventory",
                ],
                affected_scope="全项目",
            )
            warning["runtime_context"] = list(runtime_context)
            warnings.append(warning)
            continue
        for decorator in route_decorators:
            target = _route_decorator_target(decorator, decorator_aliases)
            if target is None:
                continue
            decorator, receiver, decorator_name = target
            if receiver not in known_receivers:
                warnings.append(
                    _routing_gap_warning(
                        "FASTAPI_ROUTE_RECEIVER_UNRESOLVED",
                        "route-like decorator receiver is not a statically confirmed FastAPI/Starlette app or APIRouter; endpoint was skipped",
                        relative_path,
                        decorator,
                        symbol=f"{symbol}:{receiver}",
                        missing_evidence=[
                            "statically confirmed FastAPI/Starlette/APIRouter receiver"
                        ],
                        affected_scope="全项目",
                    )
                )
                continue
            path_node = (
                decorator.args[0]
                if decorator.args
                else keyword_node(decorator, "path")
            )
            if not isinstance(static_value(path_node), str):
                warnings.append(
                    _routing_gap_warning(
                        "FASTAPI_ROUTE_PATH_UNRESOLVED",
                        "route decorator path is dynamic; endpoint and evidence were skipped",
                        relative_path,
                        decorator,
                        symbol=symbol,
                        missing_evidence=["static route decorator path"],
                    )
                )
                continue
            if decorator_name in {"api_route", "route"}:
                methods_node = keyword_node(decorator, "methods")
                raw_methods = static_value(methods_node)
                if methods_node is not None and raw_methods is not None and not (
                    isinstance(raw_methods, list) and raw_methods
                ):
                    warnings.append(
                        _routing_gap_warning(
                            "FASTAPI_ROUTE_METHODS_UNRESOLVED",
                            f"{decorator_name} methods are dynamic; endpoint and evidence were skipped",
                            relative_path,
                            decorator,
                            symbol=symbol,
                            missing_evidence=[f"static {decorator_name} methods"],
                        )
                    )
    return warnings


def function_parameters(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    import_resolver: AstImportResolver,
) -> list[dict[str, Any]]:
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    defaults: list[ast.AST | None] = [None] * (len(positional) - len(args.defaults)) + list(
        args.defaults
    )
    parameters: list[dict[str, Any]] = []
    for index, (argument, default) in enumerate(zip(positional, defaults)):
        kind = "positional_only" if index < len(args.posonlyargs) else "positional_or_keyword"
        parameters.append(
            _parameter_record(argument, default, kind, import_resolver=import_resolver)
        )
    if args.vararg:
        parameters.append(
            _parameter_record(
                args.vararg,
                None,
                "var_positional",
                required=False,
                import_resolver=import_resolver,
            )
        )
    for argument, default in zip(args.kwonlyargs, args.kw_defaults):
        parameters.append(
            _parameter_record(
                argument,
                default,
                "keyword_only",
                import_resolver=import_resolver,
            )
        )
    if args.kwarg:
        parameters.append(
            _parameter_record(
                args.kwarg,
                None,
                "var_keyword",
                required=False,
                import_resolver=import_resolver,
            )
        )
    return parameters


def _parameter_record(
    argument: ast.arg,
    default: ast.AST | None,
    kind: str,
    *,
    required: bool | None = None,
    import_resolver: AstImportResolver,
) -> dict[str, Any]:
    base_annotation, metadata = annotated_parts(argument.annotation)
    return {
        "name": argument.arg,
        "kind": kind,
        "annotation": render_node(argument.annotation) or None,
        "base_annotation": render_node(base_annotation) or None,
        "annotation_metadata": [render_node(item) for item in metadata],
        "binding": annotation_binding(argument.annotation, import_resolver),
        "default": (
            render_node(default, sensitive_context=argument.arg)
            if default is not None
            else None
        ),
        "required": default is None if required is None else required,
        "line": getattr(argument, "lineno", None),
    }


class FunctionCollector(ast.NodeVisitor):
    """Collect functions with stable qualified symbols and structural slots."""

    def __init__(self) -> None:
        self.stack: list[str] = []
        self.functions: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        symbol = ".".join([*self.stack, node.name])
        self.functions.append((symbol, node))
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        symbol = ".".join([*self.stack, node.name])
        self.functions.append((symbol, node))
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()


def iter_functions(tree: ast.Module) -> Iterator[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    collector = FunctionCollector()
    collector.visit(tree)
    yield from collector.functions


def route_id(method: str, path: str, relative_path: str, symbol: str) -> str:
    material = stable_json([method.upper(), path, relative_path, symbol])
    return f"route_{sha256_text(material)[:20]}"


def endpoint_records(
    tree: ast.Module,
    relative_path: str,
    *,
    route_prefix: str | None = None,
    router_prefixes: Mapping[str, str | Sequence[str]] | None = None,
) -> list[dict[str, Any]]:
    import_resolver = AstImportResolver(tree)
    resolved_router_prefixes: dict[str, str | Sequence[str]] = {
        symbol: () for symbol in _collect_router_declarations(tree)
    }
    for symbol in _collect_application_declarations(tree):
        resolved_router_prefixes[symbol] = ""
    resolved_router_prefixes.update(router_prefixes or {})
    for symbol in _conditional_fastapi_declaration_symbols(tree):
        resolved_router_prefixes[symbol] = ()
    records: list[dict[str, Any]] = []
    registration_contexts = _registration_contexts(tree)
    decorator_aliases, _unsafe_aliases = _module_route_decorator_aliases(tree)
    for symbol, function in iter_functions(tree):
        if _conditional_registration_context(registration_contexts, function):
            continue
        for decorator in function.decorator_list:
            for route in extract_route_decorator(
                decorator, resolved_router_prefixes, decorator_aliases
            ):
                if not route_matches_prefix(route["path"], route_prefix):
                    continue
                records.append(
                    {
                        **route,
                        "version": infer_api_version(route["path"])[0],
                        "version_source": infer_api_version(route["path"])[1],
                        "version_selector": None,
                        "route_id": route_id(
                            route["method"], route["path"], relative_path, symbol
                        ),
                        "relative_path": relative_path,
                        "file": relative_path,
                        "symbol": symbol,
                        "line": function.lineno,
                        "end_line": getattr(function, "end_lineno", function.lineno),
                        "async": isinstance(function, ast.AsyncFunctionDef),
                        "parameters": function_parameters(
                            function,
                            import_resolver,
                        ),
                    }
                )
    for record in records:
        record["request_models"] = sorted(
            {
                str(parameter["base_annotation"])
                for parameter in record["parameters"]
                if parameter.get("base_annotation")
                and (
                    not isinstance(parameter.get("binding"), dict)
                    or parameter["binding"].get("name") == "Body"
                )
                and str(parameter["base_annotation"])
                not in {
                    "Any",
                    "BackgroundTasks",
                    "Request",
                    "Response",
                    "UploadFile",
                    "bool",
                    "bytes",
                    "float",
                    "int",
                    "str",
                }
            }
        )
    records.sort(
        key=lambda item: (
            item["method"],
            item["path"],
            item["relative_path"],
            item["symbol"],
        )
    )
    return records

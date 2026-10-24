#!/usr/bin/env python3
"""Build a deterministic Spring MVC source index with the JDK Tree API.

The scanner records framework-declared routes, request bindings, validation metadata,
enums, response-status annotations, and source provenance. It deliberately does not infer
business branches, call chains, scenarios, assertions, ApiCases, or Mermaid diagrams.
"""

from __future__ import annotations

import argparse
import copy
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from _common import (
    SCHEMA_VERSION,
    TOOL_VERSION,
    ToolInputError,
    build_source_snapshot,
    ensure_bounded_scan_root,
    infer_api_version,
    is_sensitive_name,
    raw_evidence_descriptor,
    redact_scalar,
    repository_metadata,
    sha256_text,
)


DEFAULT_EXCLUDED_PARTS = {
    ".git",
    ".gradle",
    ".idea",
    "build",
    "generated",
    "node_modules",
    "out",
    "target",
    "test",
    "tests",
    "vendor",
}

ROUTE_INVENTORY_BLOCKING_CODES = {
    "DYNAMIC_ROUTE_UNRESOLVED",
    "REQUEST_METHOD_CONFLICT",
    "SPRING_ROUTE_ACTIVATION_CONDITIONAL",
    "SPRING_META_MAPPING_UNSUPPORTED",
    "SPRING_MAPPING_ANNOTATION_SOURCE_UNRESOLVED",
    "SPRING_CONTROLLER_ANNOTATION_SOURCE_UNRESOLVED",
    "SPRING_ACTIVATION_ANNOTATION_SOURCE_UNRESOLVED",
}

INTERFACE_ANALYSIS_GAP_CODES = {
    "SPRING_REQUEST_BINDING_ANNOTATION_SOURCE_UNRESOLVED",
    "SPRING_RESPONSE_STATUS_ANNOTATION_SOURCE_UNRESOLVED",
    "SPRING_VALIDATION_ANNOTATION_SOURCE_UNRESOLVED",
    "SPRING_VALIDATION_ACTIVATION_ANNOTATION_SOURCE_UNRESOLVED",
    "SPRING_VALIDATION_GROUP_SEMANTICS_UNRESOLVED",
    "SPRING_VALIDATION_CASCADE_SEMANTICS_UNRESOLVED",
    "SPRING_CUSTOM_CONSTRAINT_SOURCE_UNRESOLVED",
    "SPRING_CUSTOM_CONSTRAINT_SEMANTICS_UNRESOLVED",
}

PROJECT_BLOCKING_CODES = {
    "EVENT_PROTOCOL_WARNING",
}


class ScannerError(RuntimeError):
    """Fatal setup, compiler, process, or event-protocol error."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Index Spring MVC/Spring Boot routes and framework contract metadata with the "
            "JDK Compiler Tree API. The output is input for AI code-chain analysis, not a "
            "completed Case or flow graph."
        )
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Java project or source-tree root",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="directory for the three scan artifacts",
    )
    parser.add_argument(
        "--route-prefix",
        help="only retain statically resolved routes beginning with this prefix, e.g. /v3",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="include relative Java paths matching GLOB; repeat or comma-separate",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="exclude relative Java paths matching GLOB; repeat or comma-separate",
    )
    parser.add_argument(
        "--allow-parse-errors",
        action="store_true",
        help=(
            "exploratory scan only: return success despite javac parse errors; partial "
            "artifacts cannot be treated as a complete interface inventory"
        ),
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help=(
            "exploratory scan only: return success when no Java source or no resolved "
            "endpoint is found; empty output cannot establish interface scope"
        ),
    )
    parser.add_argument(
        "--allow-unresolved-routes",
        action="store_true",
        help=(
            "exploratory scan only: return success despite unresolved dynamic routes or "
            "mapping-method conflicts; unresolved output cannot establish complete API scope"
        ),
    )
    return parser


def parse_patterns(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return result


def matches_pattern(relative_path: str, pattern: str) -> bool:
    normalized = pattern.replace(os.sep, "/")
    return fnmatch.fnmatch(relative_path, normalized) or fnmatch.fnmatch(
        Path(relative_path).name, normalized
    )


def discover_sources(
    root: Path, include: Sequence[str], exclude: Sequence[str]
) -> tuple[list[Path], list[dict[str, str]]]:
    sources: list[Path] = []
    skipped: list[dict[str, str]] = []
    for path in sorted(root.rglob("*.java")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        resolved = path.resolve()
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ScannerError(
                "Java source escapes the authorized --root through a symlink: "
                f"{relative}"
            ) from exc
        parent_parts = {part.lower() for part in Path(relative).parts[:-1]}
        if parent_parts.intersection(DEFAULT_EXCLUDED_PARTS):
            skipped.append({"path": relative, "reason": "default_exclude"})
            continue
        if include and not any(matches_pattern(relative, pattern) for pattern in include):
            skipped.append({"path": relative, "reason": "not_included"})
            continue
        if exclude and any(matches_pattern(relative, pattern) for pattern in exclude):
            skipped.append({"path": relative, "reason": "excluded"})
            continue
        sources.append(resolved)
    return sources, skipped


def executable_or_error(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise ScannerError(
            f"{name!r} was not found on PATH; install a full JDK (JDK 17+ recommended) "
            "and make both javac and java available"
        )
    return path


def command_version(command: str, argument: str) -> str:
    process = subprocess.run(
        [command, argument],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    return process.stdout.strip()


def compile_scanner(javac: str, source: Path, classes_dir: Path) -> None:
    process = subprocess.run(
        [javac, "-encoding", "UTF-8", "-d", str(classes_dir), str(source)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if process.returncode != 0:
        detail = (process.stderr or process.stdout).strip()
        raise ScannerError(
            "failed to compile SpringBootAstScanner.java with the configured JDK"
            + (f":\n{detail}" if detail else "")
        )


def run_scanner(
    java: str,
    classes_dir: Path,
    root: Path,
    file_list: Path,
    route_prefix: str | None,
) -> tuple[list[dict[str, Any]], str]:
    command = [
        java,
        "-cp",
        str(classes_dir),
        "SpringBootAstScanner",
        "--root",
        str(root),
        "--file-list",
        str(file_list),
    ]
    if route_prefix:
        command.extend(["--route-prefix", route_prefix])
    process = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise ScannerError(
            f"JDK AST scanner exited with status {process.returncode}"
            + (f":\n{detail}" if detail else "")
        )

    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(process.stdout.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ScannerError(
                f"invalid scanner JSON event at stdout line {line_number}: {exc.msg}"
            ) from exc
        if not isinstance(event, dict) or not isinstance(event.get("event"), str):
            raise ScannerError(
                f"invalid scanner event at stdout line {line_number}: expected object "
                "with string 'event'"
            )
        events.append(event)
    return events, process.stderr.strip()


def stable_json(value: Any, *, pretty: bool = False) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    )


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def aggregate_events(
    events: Iterable[dict[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    dict[str, Any],
    list[str],
]:
    endpoints: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    protocol_warnings: list[str] = []
    for event in events:
        kind = event["event"]
        data = event.get("data")
        if kind == "endpoint" and isinstance(data, dict):
            endpoints.append(data)
        elif kind == "evidence" and isinstance(data, dict):
            evidence.append(data)
        elif kind == "warning" and isinstance(data, dict):
            warnings.append(data)
        elif kind == "diagnostic" and isinstance(data, dict):
            diagnostics.append(data)
        elif kind == "summary" and isinstance(data, dict):
            summary = data
        else:
            protocol_warnings.append(f"ignored unknown or malformed event type: {kind}")

    endpoints.sort(
        key=lambda item: (
            str(item.get("method")),
            str(item.get("path")),
            str(item.get("relative_path")),
            str(item.get("symbol")),
        )
    )
    evidence.sort(key=lambda item: str(item.get("evidence_id")))
    warnings.sort(
        key=lambda item: (
            str(item.get("code")),
            str(item.get("path")),
            str(item.get("symbol")),
        )
    )
    diagnostics.sort(
        key=lambda item: (
            str(item.get("path")),
            item.get("line") if isinstance(item.get("line"), int) else 2**63,
            str(item.get("kind")),
        )
    )
    return endpoints, evidence, warnings, diagnostics, summary, protocol_warnings


def _redact_java_string(value: str, *, name: str | None = None) -> str:
    common_result = redact_scalar(value, name=name)
    if common_result == "<redacted>":
        return "<redacted>"
    lowered = value.lower()
    if "-----begin " in lowered and "private key-----" in lowered:
        return "<redacted>"
    if "bearer " in lowered:
        return "<redacted>"
    if "eyj" in lowered and value.count(".") >= 2:
        return "<redacted>"
    scheme_index = lowered.find("://")
    at_index = lowered.find("@", scheme_index + 3) if scheme_index >= 0 else -1
    if scheme_index >= 0 and at_index > scheme_index and ":" in value[scheme_index + 3 : at_index]:
        return "<redacted>"
    sensitive_markers = (
        "authorization",
        "cookie",
        "password",
        "passwd",
        "private_key",
        "private-key",
        "privatekey",
        "token",
        "secret",
        "dsn",
    )
    has_literal = '"' in value or "'" in value
    if has_literal and any(marker in lowered for marker in sensitive_markers):
        return "<redacted-sensitive-expression>"
    return value


def _redact_java_value(value: Any, *, name: str | None = None) -> Any:
    if is_sensitive_name(name):
        return "<redacted>"
    if isinstance(value, dict):
        return {
            str(key): _redact_java_value(item, name=str(key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_java_value(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_java_value(item) for item in value]
    if isinstance(value, str):
        return _redact_java_string(value, name=name)
    return value


def _normalize_evidence(
    raw_items: list[dict[str, Any]],
    endpoints: list[dict[str, Any]],
    repository: dict[str, Any],
    content_hashes: dict[str, str],
) -> list[dict[str, Any]]:
    endpoint_by_id = {
        str(endpoint.get("route_id")): endpoint
        for endpoint in endpoints
        if endpoint.get("route_id")
    }
    normalized: list[dict[str, Any]] = []
    for raw_original in raw_items:
        raw = _redact_java_value(copy.deepcopy(raw_original))
        source_evidence_id = str(raw.get("evidence_id") or "")
        kind = str(raw.get("kind") or "unknown")
        relative_path = str(raw.get("relative_path") or "")
        symbol = str(raw.get("symbol") or "")
        content_sha256 = content_hashes.get(relative_path)
        if content_sha256 is None:
            raise ScannerError(
                f"source snapshot is missing a content hash for {relative_path!r}"
            )
        route_ids = sorted({str(value) for value in raw.get("endpoint_ids", [])})
        resolved_route_ids = [route_id for route_id in route_ids if route_id in endpoint_by_id]
        logical_slot = str(raw.get("logical_slot") or kind)
        source_logical_key = raw.get("logical_key")
        if not isinstance(source_logical_key, str) or not source_logical_key:
            material = stable_json([relative_path, symbol, kind, logical_slot])
            source_logical_key = f"evk_{sha256_text(material)[:24]}"

        targets: list[str | None] = resolved_route_ids or [None]
        for route_id in targets:
            endpoint = None
            if route_id is not None:
                endpoint = {
                    "route_id": route_id,
                    "method": endpoint_by_id[route_id].get("method"),
                    "path": endpoint_by_id[route_id].get("path"),
                    "version": endpoint_by_id[route_id].get("version"),
                    "version_source": endpoint_by_id[route_id].get("version_source"),
                    "version_selector": endpoint_by_id[route_id].get("version_selector"),
                }

            evidence_id = source_evidence_id
            logical_key = source_logical_key
            item_logical_slot = logical_slot
            details = (
                copy.deepcopy(raw.get("details"))
                if isinstance(raw.get("details"), dict)
                else {}
            )
            if len(resolved_route_ids) > 1 and route_id is not None:
                evidence_id = "ev_" + sha256_text(
                    stable_json([source_evidence_id, route_id])
                )[:24]
                logical_key = "evk_" + sha256_text(
                    stable_json([source_logical_key, route_id])
                )[:24]
                item_logical_slot = f"{logical_slot}.endpoint[{route_id}]"
                details["source_evidence_id"] = source_evidence_id

            item: dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "tool_version": TOOL_VERSION,
                "evidence_id": evidence_id,
                "logical_key": logical_key,
                "logical_slot": item_logical_slot,
                "evidence_type": kind,
                "kind": kind,
                "framework_adapter": "springboot-jdk-ast-index",
                "relative_path": relative_path,
                "symbol": symbol,
                "source": {
                    "repository": repository.get("repository"),
                    "revision": repository.get("revision"),
                    "dirty": repository.get("dirty"),
                    "snapshot_kind": repository.get("snapshot_kind"),
                    "snapshot_id": repository.get("snapshot_id"),
                    "content_sha256": content_sha256,
                    "file": relative_path,
                    "relative_path": relative_path,
                    "symbol": symbol,
                    "line": raw.get("line"),
                    "end_line": raw.get("line"),
                },
                "endpoint": endpoint,
                "endpoint_ids": [route_id] if route_id is not None else [],
                "details": details,
            }
            normalized.append(item)
    normalized.sort(key=lambda item: str(item.get("evidence_id")))
    return normalized


def failure_manifest(
    output_dir: Path,
    root: Path | None,
    include: Sequence[str],
    exclude: Sequence[str],
    route_prefix: str | None,
    error: str,
) -> None:
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tool": "scan_springboot_ast",
        "tool_version": TOOL_VERSION,
        "framework": "spring-boot",
        "framework_adapter": "springboot-jdk-ast-index",
        "repository": repository_metadata(str(root)) if root is not None else None,
        "status": "failed",
        "analysis_ready": False,
        "case_generation_eligible": False,
        "blocking_reasons": [
            {
                "code": "SCAN_FATAL_ERROR",
                "message": _redact_java_string(error),
                "affected_scope": "全项目",
            }
        ],
        "root": str(root) if root is not None else None,
        "filters": {
            "include": list(include),
            "exclude": list(exclude),
            "route_prefix": route_prefix,
            "default_excluded_parts": sorted(DEFAULT_EXCLUDED_PARTS),
        },
        "fatal_error": _redact_java_string(error),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        write_text(output_dir / "scan-manifest.json", stable_json(manifest, pretty=True) + "\n")
    except OSError:
        pass


def execute(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    include = parse_patterns(args.include)
    exclude = parse_patterns(args.exclude)
    if not root.is_dir():
        raise ScannerError(f"--root is not a directory: {root}")
    ensure_bounded_scan_root(root, label="--root")
    output_dir.mkdir(parents=True, exist_ok=True)

    javac = executable_or_error("javac")
    java = executable_or_error("java")
    scanner_source = Path(__file__).with_name("SpringBootAstScanner.java")
    if not scanner_source.is_file():
        raise ScannerError(f"Java scanner source is missing: {scanner_source}")

    sources, skipped = discover_sources(root, include, exclude)
    repository = repository_metadata(str(root))
    repository, content_hashes = build_source_snapshot(
        repository,
        ((path.relative_to(root).as_posix(), path) for path in sources),
    )
    if sources:
        with tempfile.TemporaryDirectory(prefix="mango-springboot-ast-") as temporary_name:
            temporary = Path(temporary_name)
            classes_dir = temporary / "classes"
            classes_dir.mkdir()
            file_list = temporary / "java-sources.txt"
            file_list.write_text(
                "".join(f"{path}\n" for path in sources), encoding="utf-8"
            )
            compile_scanner(javac, scanner_source, classes_dir)
            events, scanner_stderr = run_scanner(
                java, classes_dir, root, file_list, args.route_prefix
            )
    else:
        events = [
            {
                "event": "summary",
                "data": {
                    "tool_version": TOOL_VERSION,
                    "files_parsed": 0,
                    "endpoint_count": 0,
                    "evidence_count": 0,
                    "model_field_count": 0,
                    "enum_count": 0,
                    "warning_count": 0,
                    "diagnostic_count": 0,
                    "diagnostic_error_count": 0,
                },
            }
        ]
        scanner_stderr = ""

    endpoints, evidence, warnings, diagnostics, scanner_summary, protocol_warnings = (
        aggregate_events(events)
    )
    for endpoint in endpoints:
        version, version_source = infer_api_version(str(endpoint.get("path") or ""))
        endpoint.setdefault("version", version)
        endpoint.setdefault("version_source", version_source)
        endpoint.setdefault("version_selector", None)
    endpoints = _redact_java_value(endpoints)
    evidence = _normalize_evidence(
        evidence,
        endpoints,
        repository,
        content_hashes,
    )
    raw_evidence = raw_evidence_descriptor(evidence)
    if not repository.get("revision") or not isinstance(repository.get("dirty"), bool):
        warnings.append(
            {
                "code": "SOURCE_REVISION_UNAVAILABLE",
                "message": (
                    "Git revision/dirty state is unavailable; provide an immutable source "
                    "snapshot identifier before validating executable cases"
                ),
                "path": None,
                "symbol": None,
            }
        )
    if scanner_stderr:
        warnings.append(
            {
                "code": "SCANNER_STDERR",
                "message": scanner_stderr,
                "path": None,
                "symbol": None,
            }
        )
    for message in protocol_warnings:
        warnings.append(
            {"code": "EVENT_PROTOCOL_WARNING", "message": message, "path": None, "symbol": None}
        )
    warnings = _redact_java_value(warnings)
    diagnostics = _redact_java_value(diagnostics)

    method_counts = Counter(str(endpoint.get("method")) for endpoint in endpoints)
    evidence_counts = Counter(str(item.get("kind")) for item in evidence)
    diagnostic_counts = Counter(str(item.get("kind")) for item in diagnostics)
    endpoint_scope = [
        {
            "method": endpoint.get("method"),
            "path": endpoint.get("path"),
            "version": endpoint.get("version"),
            "version_source": endpoint.get("version_source"),
            "version_selector": endpoint.get("version_selector"),
        }
        for endpoint in endpoints
    ]
    endpoint_scope_sha256 = sha256_text(stable_json(endpoint_scope))
    scan_snapshot = {
        "repository": repository,
        "source_files": [
            {"file": path, "content_sha256": digest}
            for path, digest in sorted(content_hashes.items())
        ],
        "filters": {
            "include": include,
            "exclude": exclude,
            "route_prefix": args.route_prefix,
            "default_excluded_parts": sorted(DEFAULT_EXCLUDED_PARTS),
        },
        "endpoint_scope_sha256": endpoint_scope_sha256,
        "raw_evidence": raw_evidence,
    }
    scan_snapshot_sha256 = sha256_text(stable_json(scan_snapshot))
    blocking_reasons: list[dict[str, Any]] = []
    for option in (
        "allow_parse_errors",
        "allow_empty",
        "allow_unresolved_routes",
    ):
        if bool(getattr(args, option, False)):
            blocking_reasons.append(
                {
                    "code": f"EXPLORATORY_{option.upper()}_ENABLED",
                    "message": (
                        f"{option} is enabled; this run is exploratory and cannot "
                        "be treated as a complete interface inventory"
                    ),
                    "affected_scope": "全项目",
                }
            )
    if diagnostic_counts.get("ERROR", 0):
        blocking_reasons.append(
            {
                "code": "SCAN_PARSE_ERRORS",
                "message": (
                    f"{diagnostic_counts.get('ERROR', 0)} javac parse error(s) "
                    "were reported"
                ),
                "affected_scope": "全项目",
            }
        )
    if not sources:
        blocking_reasons.append(
            {
                "code": "SCAN_SOURCE_SCOPE_EMPTY",
                "message": "no Java source file was scanned",
                "affected_scope": "全项目",
            }
        )
    if not endpoints:
        blocking_reasons.append(
            {
                "code": "SCAN_ENDPOINT_SCOPE_EMPTY",
                "message": "no statically resolved HTTP endpoint was discovered",
                "affected_scope": "全项目",
            }
        )
    blocking_warning_codes = (
        ROUTE_INVENTORY_BLOCKING_CODES | PROJECT_BLOCKING_CODES
    )
    for warning in warnings:
        if not isinstance(warning, dict) or warning.get("code") not in blocking_warning_codes:
            continue
        reason = {
            "code": str(warning.get("code")),
            "message": str(warning.get("message") or "Spring route is unresolved"),
            "affected_scope": (
                warning.get("affected_scope")
                if warning.get("affected_scope")
                in {"当前Case", "当前接口", "共享链路", "全项目"}
                else "全项目"
            ),
            **{
                key: warning[key]
                for key in ("path", "line", "symbol", "interface_key", "endpoint")
                if warning.get(key) is not None
            },
        }
        if not isinstance(reason.get("endpoint"), dict) and not reason.get(
            "interface_key"
        ):
            reason["affected_scope"] = "全项目"
        blocking_reasons.append(reason)

    endpoint_by_id = {
        str(endpoint.get("route_id")): endpoint
        for endpoint in endpoints
        if endpoint.get("route_id")
    }
    interface_analysis_gaps: list[dict[str, Any]] = []
    for warning in warnings:
        if (
            not isinstance(warning, dict)
            or warning.get("code") not in INTERFACE_ANALYSIS_GAP_CODES
        ):
            continue
        endpoint_ids = [
            str(endpoint_id)
            for endpoint_id in warning.get("endpoint_ids", [])
            if str(endpoint_id) in endpoint_by_id
        ]
        if not endpoint_ids:
            continue
        gap = {
            key: copy.deepcopy(value)
            for key, value in warning.items()
            if key not in {"endpoints", "endpoint_ids"}
        }
        gap["endpoint_ids"] = endpoint_ids
        interface_analysis_gaps.append(gap)
        endpoint_gap = {
            key: copy.deepcopy(value)
            for key, value in gap.items()
            if key != "endpoint_ids"
        }
        for endpoint_id in endpoint_ids:
            endpoint_by_id[endpoint_id].setdefault("analysis_gaps", []).append(
                copy.deepcopy(endpoint_gap)
            )
    registrations: dict[str, list[dict[str, Any]]] = {}
    for endpoint in endpoints:
        identity = stable_json(
            [
                str(endpoint.get("method") or "").upper(),
                endpoint.get("path"),
                endpoint.get("version"),
                endpoint.get("version_source"),
                endpoint.get("version_selector"),
            ]
        )
        registrations.setdefault(identity, []).append(endpoint)
    for duplicates in registrations.values():
        if len(duplicates) < 2:
            continue
        first = duplicates[0]
        blocking_reasons.append(
            {
                "code": "DUPLICATE_ROUTE_REGISTRATION",
                "message": (
                    "the same canonical HTTP interface is registered more than once; "
                    "routing precedence cannot be treated as one endpoint"
                ),
                "affected_scope": "当前接口",
                "endpoint": {
                    key: first.get(key)
                    for key in (
                        "method",
                        "path",
                        "version",
                        "version_source",
                        "version_selector",
                    )
                },
                "registration_count": len(duplicates),
                "registrations": [
                    {
                        "file": endpoint.get("file") or endpoint.get("relative_path"),
                        "symbol": endpoint.get("symbol"),
                        "line": endpoint.get("line"),
                    }
                    for endpoint in duplicates
                ],
            }
        )
    blocking_reasons.sort(
        key=lambda item: (
            str(item.get("code") or ""),
            str(item.get("path") or ""),
            int(item.get("line") or 0),
            str(item.get("symbol") or ""),
        )
    )
    analysis_ready = not blocking_reasons
    if not analysis_ready:
        scan_status = "incomplete"
    elif interface_analysis_gaps:
        scan_status = "completed_with_gaps"
    else:
        scan_status = "completed"
    endpoint_inventory = {
        "schema_version": SCHEMA_VERSION,
        "tool": "scan_springboot_ast",
        "tool_version": TOOL_VERSION,
        "framework": "spring-boot",
        "framework_adapter": "springboot-jdk-ast-index",
        "repository": repository,
        "status": scan_status,
        "analysis_ready": analysis_ready,
        # Compatibility alias. This does not mean that Cases or a call chain exist.
        "case_generation_eligible": analysis_ready,
        "exploratory_options": {
            "allow_parse_errors": bool(getattr(args, "allow_parse_errors", False)),
            "allow_empty": bool(getattr(args, "allow_empty", False)),
            "allow_unresolved_routes": bool(
                getattr(args, "allow_unresolved_routes", False)
            ),
        },
        "scan_snapshot_sha256": scan_snapshot_sha256,
        "endpoint_scope_sha256": endpoint_scope_sha256,
        "raw_evidence": raw_evidence,
        "source_files": [
            {"file": path, "content_sha256": digest}
            for path, digest in sorted(content_hashes.items())
        ],
        "root": str(root),
        "route_prefix": args.route_prefix,
        "summary": {
            "endpoint_count": len(endpoints),
            "interface_analysis_gap_count": len(interface_analysis_gaps),
            "endpoint_scope_sha256": endpoint_scope_sha256,
            "by_method": dict(sorted(method_counts.items())),
        },
        "interface_analysis_gaps": interface_analysis_gaps,
        "endpoints": endpoints,
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tool": "scan_springboot_ast",
        "tool_version": TOOL_VERSION,
        "framework": "spring-boot",
        "framework_adapter": "springboot-jdk-ast-index",
        "repository": repository,
        "source_files": [
            {"file": path, "content_sha256": digest}
            for path, digest in sorted(content_hashes.items())
        ],
        "status": scan_status,
        "analysis_ready": analysis_ready,
        # Compatibility alias. This does not mean that Cases or a call chain exist.
        "case_generation_eligible": analysis_ready,
        "exploratory_options": {
            "allow_parse_errors": bool(getattr(args, "allow_parse_errors", False)),
            "allow_empty": bool(getattr(args, "allow_empty", False)),
            "allow_unresolved_routes": bool(
                getattr(args, "allow_unresolved_routes", False)
            ),
        },
        "blocking_reasons": blocking_reasons,
        "interface_analysis_gaps": interface_analysis_gaps,
        "scan_snapshot": scan_snapshot,
        "scan_snapshot_sha256": scan_snapshot_sha256,
        "endpoint_scope_sha256": endpoint_scope_sha256,
        "raw_evidence": raw_evidence,
        "root": str(root),
        "filters": {
            "include": include,
            "exclude": exclude,
            "route_prefix": args.route_prefix,
            "default_excluded_parts": sorted(DEFAULT_EXCLUDED_PARTS),
        },
        "jdk": {
            "javac": javac,
            "javac_version": command_version(javac, "-version"),
            "java": java,
            "java_version": command_version(java, "-version"),
        },
        "files": {
            "discovered": [path.relative_to(root).as_posix() for path in sources],
            "skipped": skipped,
            "discovered_count": len(sources),
            "skipped_count": len(skipped),
        },
        "summary": {
            "endpoint_count": len(endpoints),
            "evidence_count": len(evidence),
            "warning_count": len(warnings),
            "interface_analysis_gap_count": len(interface_analysis_gaps),
            "diagnostic_count": len(diagnostics),
            "diagnostic_error_count": diagnostic_counts.get("ERROR", 0),
            "endpoints_by_method": dict(sorted(method_counts.items())),
            "evidence_by_kind": dict(sorted(evidence_counts.items())),
            "diagnostics_by_kind": dict(sorted(diagnostic_counts.items())),
        },
        "scanner_summary": scanner_summary,
        "warnings": warnings,
        "diagnostics": diagnostics,
        "outputs": {
            "endpoint_inventory": "endpoint-inventory.json",
            "endpoint_scope_sha256": endpoint_scope_sha256,
            "evidence": "evidence.jsonl",
            "manifest": "scan-manifest.json",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_text(
        output_dir / "endpoint-inventory.json",
        stable_json(endpoint_inventory, pretty=True) + "\n",
    )
    evidence_text = "".join(stable_json(item) + "\n" for item in evidence)
    write_text(output_dir / "evidence.jsonl", evidence_text)
    write_text(
        output_dir / "scan-manifest.json", stable_json(manifest, pretty=True) + "\n"
    )

    if diagnostics:
        print(
            "scan_springboot_ast: "
            f"{len(diagnostics)} javac parse diagnostic(s), including "
            f"{diagnostic_counts.get('ERROR', 0)} error(s); see scan-manifest.json",
            file=sys.stderr,
        )
    print(
        "scan_springboot_ast: "
        f"scanned {len(sources)} Java file(s), found {len(endpoints)} endpoint(s) "
        f"and {len(evidence)} evidence item(s); outputs: {output_dir}",
        file=sys.stderr,
    )
    if diagnostic_counts.get("ERROR", 0) and not getattr(
        args, "allow_parse_errors", False
    ):
        return 2
    if (not sources or not endpoints) and not getattr(args, "allow_empty", False):
        return 2
    if any(
        reason.get("code") == "DUPLICATE_ROUTE_REGISTRATION"
        for reason in blocking_reasons
    ):
        return 2
    if any(
        reason.get("code") in PROJECT_BLOCKING_CODES
        for reason in blocking_reasons
    ):
        return 2
    if any(
        reason.get("code") in ROUTE_INVENTORY_BLOCKING_CODES
        for reason in blocking_reasons
    ) and not getattr(args, "allow_unresolved_routes", False):
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir).expanduser().resolve()
    root = Path(args.root).expanduser().resolve()
    include = parse_patterns(args.include)
    exclude = parse_patterns(args.exclude)
    try:
        return execute(args)
    except (ScannerError, ToolInputError, OSError) as exc:
        message = str(exc)
        failure_manifest(
            output_dir, root, include, exclude, args.route_prefix, message
        )
        print(f"scan_springboot_ast: error: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

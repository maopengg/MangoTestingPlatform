#!/usr/bin/env python3
"""Build a deterministic FastAPI/Pydantic endpoint and source index.

This adapter deliberately does not interpret function bodies, infer business
branches, trace calls, design Cases, or generate Mermaid. Codex uses the index
as a bounded and reproducible starting point for source-level chain analysis.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from _common import (
    SCHEMA_VERSION,
    TOOL_VERSION,
    ToolInputError,
    build_source_snapshot,
    collect_fastapi_route_warnings,
    collect_router_prefix_registry,
    discover_python_sources,
    endpoint_records,
    parse_patterns,
    parse_source,
    raw_evidence_descriptor,
    repository_metadata,
    resolve_router_prefixes,
    sha256_text,
    stable_json,
    write_output,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Index FastAPI/Starlette routes and request contracts with Python AST. "
            "The output is source evidence for AI analysis, not a completed call chain."
        )
    )
    parser.add_argument("paths", nargs="*", help="Python files or directories to index")
    parser.add_argument("--root", action="append", default=[], metavar="PATH")
    parser.add_argument("--include", action="append", default=[], metavar="GLOB")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB")
    parser.add_argument("--no-default-excludes", action="store_true")
    parser.add_argument("--route-prefix")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--output-dir")
    parser.add_argument("--manifest-output", default=None)
    parser.add_argument("--inventory-output", default=None)
    parser.set_defaults(fail_on_parse_error=True)
    parser.add_argument(
        "--fail-on-parse-error",
        dest="fail_on_parse_error",
        action="store_true",
    )
    parser.add_argument(
        "--allow-parse-errors",
        dest="fail_on_parse_error",
        action="store_false",
        help="exploratory only; partial output is not a complete module inventory",
    )
    parser.add_argument("--allow-empty", action="store_true", help="exploratory only")
    parser.add_argument(
        "--allow-unresolved-routes",
        action="store_true",
        help="exploratory only; unresolved routes still block complete inventory claims",
    )
    return parser


def _source_record(
    route: Mapping[str, Any],
    repository: Mapping[str, Any],
    content_hashes: Mapping[str, str],
) -> dict[str, Any]:
    relative_path = str(route["relative_path"])
    return {
        "repository": repository.get("repository"),
        "revision": repository.get("revision"),
        "snapshot_kind": repository.get("snapshot_kind"),
        "snapshot_id": repository.get("snapshot_id"),
        "relative_path": relative_path,
        "content_sha256": content_hashes[relative_path],
        "line": route.get("line"),
        "end_line": route.get("end_line"),
        "symbol": route.get("symbol"),
    }


def _index_record(
    *,
    kind: str,
    route: Mapping[str, Any],
    repository: Mapping[str, Any],
    content_hashes: Mapping[str, str],
    slot: str,
    details: Mapping[str, Any],
) -> dict[str, Any]:
    identity = stable_json(
        [
            kind,
            route.get("route_id"),
            route.get("relative_path"),
            route.get("symbol"),
            slot,
            details,
        ]
    )
    logical_identity = stable_json([kind, route.get("route_id"), slot])
    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "framework_adapter": "fastapi-pydantic-index",
        "evidence_type": kind,
        "kind": kind,
        "evidence_id": f"idx_{sha256_text(identity)[:24]}",
        "logical_key": f"idxk_{sha256_text(logical_identity)[:24]}",
        "endpoint_ids": [route.get("route_id")],
        "endpoint": {
            "method": route.get("method"),
            "path": route.get("path"),
            "version": route.get("version"),
        },
        "source": _source_record(route, repository, content_hashes),
        "details": dict(details),
    }


def build_source_index(
    routes: Sequence[Mapping[str, Any]],
    repository: Mapping[str, Any],
    content_hashes: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Return route and request-contract records only.

    Function bodies are intentionally absent. In particular, this function never
    emits if/match branches, calls, returns, raises, business outcomes, or oracles.
    """

    records: list[dict[str, Any]] = []
    for route in routes:
        records.append(
            _index_record(
                kind="endpoint",
                route=route,
                repository=repository,
                content_hashes=content_hashes,
                slot="route",
                details={
                    "declared_path": route.get("declared_path"),
                    "router": route.get("router"),
                    "async": route.get("async"),
                    "request_models": route.get("request_models", []),
                },
            )
        )
        for parameter in route.get("parameters") or []:
            name = str(parameter.get("name") or "")
            if name in {"self", "cls"}:
                continue
            records.append(
                _index_record(
                    kind="endpoint_parameter",
                    route=route,
                    repository=repository,
                    content_hashes=content_hashes,
                    slot=f"parameter:{name}",
                    details=parameter,
                )
            )
    records.sort(key=lambda item: item["evidence_id"])
    return records


def _duplicate_route_reasons(routes: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for route in routes:
        grouped.setdefault(
            (str(route.get("method")), str(route.get("path"))), []
        ).append(route)
    reasons: list[dict[str, Any]] = []
    for (method, path), matches in grouped.items():
        if len(matches) < 2:
            continue
        reasons.append(
            {
                "code": "DUPLICATE_ROUTE_REGISTRATION",
                "message": f"{method} {path} has {len(matches)} static registrations",
                "affected_scope": "当前接口",
                "endpoint": {"method": method, "path": path},
                "sources": [
                    {
                        "path": item.get("relative_path"),
                        "line": item.get("line"),
                        "symbol": item.get("symbol"),
                    }
                    for item in matches
                ],
            }
        )
    return reasons


def _blocking_reasons(
    *,
    parsed_files: Sequence[str],
    parse_errors: Sequence[Mapping[str, str]],
    routes: Sequence[Mapping[str, Any]],
    routing_warnings: Sequence[Mapping[str, Any]],
    exploratory_options: Mapping[str, bool],
) -> list[dict[str, Any]]:
    reasons: list[dict[str, Any]] = []
    if not parsed_files:
        reasons.append(
            {
                "code": "NO_SOURCE_FILES",
                "message": "no parseable Python source file was found",
                "affected_scope": "全项目",
            }
        )
    if not routes:
        reasons.append(
            {
                "code": "NO_ENDPOINTS",
                "message": "no statically resolved HTTP endpoint was discovered",
                "affected_scope": "全项目",
            }
        )
    for item in parse_errors:
        reasons.append(
            {
                "code": "PYTHON_PARSE_ERROR",
                "message": item["error"],
                "path": item["path"],
                "affected_scope": "全项目",
            }
        )
    reasons.extend(_duplicate_route_reasons(routes))
    for warning in routing_warnings:
        reason = {
            "code": str(warning.get("code") or "FASTAPI_ROUTE_UNRESOLVED"),
            "message": str(warning.get("message") or "FastAPI route is unresolved"),
            "affected_scope": warning.get("affected_scope") or "全项目",
        }
        for key in ("path", "line", "symbol", "interface_key", "endpoint"):
            if warning.get(key) is not None:
                reason[key] = warning[key]
        reasons.append(reason)
    for option, enabled in exploratory_options.items():
        if enabled:
            reasons.append(
                {
                    "code": f"EXPLORATORY_{option.upper()}_ENABLED",
                    "message": (
                        f"{option} is enabled; this source index is exploratory and cannot "
                        "be treated as a complete interface inventory"
                    ),
                    "affected_scope": "全项目",
                }
            )
    reasons.sort(
        key=lambda item: (
            str(item.get("code")),
            str(item.get("path")),
            int(item.get("line") or 0),
        )
    )
    return reasons


def run(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any], int]:
    includes = parse_patterns(args.include)
    excludes = parse_patterns(args.exclude)
    scan_paths = [*args.root, *args.paths]
    if not scan_paths:
        raise ToolInputError("at least one --root or path is required")
    sources, skipped = discover_python_sources(
        scan_paths,
        include=includes,
        exclude=excludes,
        default_excludes=not args.no_default_excludes,
    )
    repository = repository_metadata(scan_paths[0])
    repository, content_hashes = build_source_snapshot(
        repository,
        ((source.relative_path, source.path) for source in sources),
    )

    parsed_sources: list[tuple[Any, ast.Module]] = []
    parse_errors: list[dict[str, str]] = []
    for source in sources:
        try:
            _text, tree = parse_source(source)
            parsed_sources.append((source, tree))
        except ToolInputError as exc:
            parse_errors.append({"path": source.relative_path, "error": str(exc)})

    routing_warnings: list[dict[str, Any]] = []
    prefix_registry = collect_router_prefix_registry(
        ((source.relative_path, tree) for source, tree in parsed_sources),
        warnings=routing_warnings,
    )
    routes: list[dict[str, Any]] = []
    for source, tree in parsed_sources:
        router_prefixes = resolve_router_prefixes(
            tree, source.relative_path, prefix_registry
        )
        routing_warnings.extend(
            collect_fastapi_route_warnings(
                tree, source.relative_path, router_prefixes
            )
        )
        routes.extend(
            endpoint_records(
                tree,
                source.relative_path,
                route_prefix=args.route_prefix,
                router_prefixes=router_prefixes,
            )
        )
    routes.sort(
        key=lambda item: (
            str(item.get("method")),
            str(item.get("path")),
            str(item.get("relative_path")),
            str(item.get("symbol")),
        )
    )

    evidence = build_source_index(routes, repository, content_hashes)
    raw_evidence = raw_evidence_descriptor(evidence)
    endpoint_scope = [
        {
            "method": item.get("method"),
            "path": item.get("path"),
            "version": item.get("version"),
            "version_source": item.get("version_source"),
            "version_selector": item.get("version_selector"),
        }
        for item in routes
    ]
    endpoint_scope_sha256 = sha256_text(stable_json(endpoint_scope))
    parsed_files = [source.relative_path for source, _tree in parsed_sources]
    exploratory_options = {
        "allow_parse_errors": not args.fail_on_parse_error,
        "allow_empty": bool(args.allow_empty),
        "allow_unresolved_routes": bool(args.allow_unresolved_routes),
    }
    blocking_reasons = _blocking_reasons(
        parsed_files=parsed_files,
        parse_errors=parse_errors,
        routes=routes,
        routing_warnings=routing_warnings,
        exploratory_options=exploratory_options,
    )
    analysis_ready = not blocking_reasons
    status = "completed" if analysis_ready else "incomplete"
    filters = {
        "paths": scan_paths,
        "include": includes,
        "exclude": excludes,
        "default_excludes": not args.no_default_excludes,
        "route_prefix": args.route_prefix,
    }
    source_files = [
        {"file": path, "content_sha256": digest}
        for path, digest in sorted(content_hashes.items())
    ]
    scan_snapshot = {
        "repository": repository,
        "source_files": source_files,
        "filters": filters,
        "endpoint_scope_sha256": endpoint_scope_sha256,
        "raw_evidence": raw_evidence,
    }
    snapshot_sha256 = sha256_text(stable_json(scan_snapshot))
    summary = {
        "files_scanned": len(parsed_files),
        "files_skipped": len(skipped),
        "parse_error_count": len(parse_errors),
        "endpoint_count": len(routes),
        "evidence_count": len(evidence),
        "by_evidence_type": dict(
            sorted(Counter(item["evidence_type"] for item in evidence).items())
        ),
    }
    shared = {
        "schema_version": SCHEMA_VERSION,
        "tool": "scan_fastapi_ast",
        "tool_version": TOOL_VERSION,
        "framework": "fastapi",
        "framework_adapter": "fastapi-pydantic-index",
        "status": status,
        "analysis_ready": analysis_ready,
        # Compatibility alias. This does not mean that Cases or a call chain exist.
        "case_generation_eligible": analysis_ready,
        "repository": repository,
        "source_files": source_files,
        "scan_snapshot_sha256": snapshot_sha256,
        "endpoint_scope_sha256": endpoint_scope_sha256,
        "raw_evidence": raw_evidence,
        "blocking_reasons": blocking_reasons,
        "exploratory_options": exploratory_options,
        "summary": summary,
    }
    inventory = {
        **shared,
        "route_prefix": args.route_prefix,
        "endpoints": routes,
    }
    manifest = {
        **shared,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scan": {
            **filters,
            "files_scanned": parsed_files,
            "files_skipped": skipped,
            "parse_errors": parse_errors,
        },
        "scan_snapshot": scan_snapshot,
        "warnings": list(routing_warnings),
        "artifacts": {
            "evidence_output": args.output,
            "evidence_sha256": sha256_text(
                "".join(stable_json(item) + "\n" for item in evidence)
            ),
            "endpoint_inventory_output": getattr(args, "inventory_output", None),
        },
    }

    strict_parse_failure = bool(parse_errors and args.fail_on_parse_error)
    strict_empty_failure = bool(not routes and not args.allow_empty)
    strict_route_failure = bool(
        routing_warnings and not args.allow_unresolved_routes
    ) or bool(_duplicate_route_reasons(routes))
    exit_code = 2 if strict_parse_failure or strict_empty_failure or strict_route_failure else 0
    return evidence, inventory, manifest, exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser()
        args.output = args.output or str(output_dir / "evidence.jsonl")
        args.manifest_output = args.manifest_output or str(
            output_dir / "scan-manifest.json"
        )
        args.inventory_output = args.inventory_output or str(
            output_dir / "endpoint-inventory.json"
        )
    args.output = args.output or "evidence.jsonl"
    args.manifest_output = args.manifest_output or "scan-manifest.json"
    args.inventory_output = args.inventory_output or "endpoint-inventory.json"
    if sum(
        value == "-"
        for value in (args.output, args.manifest_output, args.inventory_output)
    ) > 1:
        parser.error("only one artifact may use stdout")
    try:
        evidence, inventory, manifest, exit_code = run(args)
        write_output(
            args.output, "".join(stable_json(item) + "\n" for item in evidence)
        )
        write_output(args.inventory_output, stable_json(inventory, pretty=True) + "\n")
        write_output(args.manifest_output, stable_json(manifest, pretty=True) + "\n")
        return exit_code
    except (ToolInputError, OSError) as exc:
        parser.exit(2, f"scan_fastapi_ast: error: {exc}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())

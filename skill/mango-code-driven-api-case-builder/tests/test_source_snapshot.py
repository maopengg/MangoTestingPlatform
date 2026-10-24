#!/usr/bin/env python3
"""Focused regression tests for immutable scanner source provenance."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from _common import SCHEMA_VERSION, TOOL_VERSION, build_source_snapshot  # noqa: E402
import scan_fastapi_ast  # noqa: E402
import scan_springboot_ast  # noqa: E402


class SourceSnapshotScannerTest(unittest.TestCase):
    def test_content_snapshot_is_deterministic_and_content_addressed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            first = root / "a.py"
            second = root / "b.py"
            first.write_bytes(b"a = 1\n")
            second.write_bytes(b"b = 2\n")
            repository = {
                "repository": "snapshot-only",
                "revision": None,
                "dirty": None,
                "root": "snapshot-only",
            }
            pinned, hashes = build_source_snapshot(
                repository,
                (("b.py", second), ("a.py", first)),
            )
            repeated, repeated_hashes = build_source_snapshot(
                repository,
                (("a.py", first), ("b.py", second)),
            )

            self.assertEqual(pinned, repeated)
            self.assertEqual(hashes, repeated_hashes)
            self.assertEqual(pinned["snapshot_kind"], "content")
            self.assertEqual(pinned["revision"], f"sha256:{pinned['snapshot_id']}")
            self.assertFalse(pinned["dirty"])
            self.assertEqual(
                hashes["a.py"], hashlib.sha256(b"a = 1\n").hexdigest()
            )

            second.write_bytes(b"b = 3\n")
            changed, _ = build_source_snapshot(
                repository,
                (("a.py", first), ("b.py", second)),
            )
            self.assertNotEqual(changed["snapshot_id"], pinned["snapshot_id"])

    def test_fastapi_evidence_carries_aggregate_and_file_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            source = root / "app.py"
            source.write_text(
                textwrap.dedent(
                    """
                    from fastapi import FastAPI
                    app = FastAPI()

                    @app.get('/v3/items')
                    def get_items():
                        return {'items': []}
                    """
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                root=[str(root)],
                paths=[],
                include=[],
                exclude=[],
                no_default_excludes=False,
                route_prefix="/v3",
                output="evidence.jsonl",
                output_dir=None,
                manifest_output="scan-manifest.json",
                inventory_output="endpoint-inventory.json",
                fail_on_parse_error=True,
                allow_empty=False,
                allow_unresolved_routes=False,
            )
            evidence, _inventory, manifest, exit_code = scan_fastapi_ast.run(args)

            self.assertEqual(exit_code, 0)
            self.assertTrue(evidence)
            snapshot = manifest["repository"]
            expected_content_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            self.assertEqual(manifest["source_files"], [
                {"file": "app.py", "content_sha256": expected_content_hash}
            ])
            for item in evidence:
                self.assertEqual(item["schema_version"], SCHEMA_VERSION)
                self.assertEqual(item["tool_version"], TOOL_VERSION)
                self.assertEqual(item["framework_adapter"], "fastapi-pydantic-index")
                source_record = item["source"]
                self.assertEqual(source_record["snapshot_kind"], snapshot["snapshot_kind"])
                self.assertEqual(source_record["snapshot_id"], snapshot["snapshot_id"])
                self.assertEqual(source_record["revision"], snapshot["revision"])
                self.assertEqual(source_record["content_sha256"], expected_content_hash)
                self.assertGreater(source_record["line"], 0)
                self.assertGreaterEqual(source_record["end_line"], source_record["line"])

    def test_spring_normalization_carries_snapshot_provenance(self) -> None:
        repository = {
            "repository": "spring-service",
            "revision": "a" * 40,
            "dirty": False,
            "snapshot_kind": "git",
            "snapshot_id": "b" * 64,
        }
        endpoints = [
            {
                "route_id": "route-1",
                "method": "GET",
                "path": "/v3/items",
                "version": "v3",
                "version_source": "path",
                "version_selector": None,
            }
        ]
        raw = [
            {
                "evidence_id": "ev-1",
                "logical_key": "evk-1",
                "kind": "endpoint",
                "relative_path": "src/main/java/Demo.java",
                "symbol": "Demo.getItems",
                "line": 12,
                "condition": "route is selected",
                "result": "handler is invoked",
                "endpoint_ids": ["route-1"],
            }
        ]
        content_hash = "c" * 64
        normalized = scan_springboot_ast._normalize_evidence(
            raw,
            endpoints,
            repository,
            {"src/main/java/Demo.java": content_hash},
        )

        source = normalized[0]["source"]
        self.assertEqual(normalized[0]["schema_version"], SCHEMA_VERSION)
        self.assertEqual(normalized[0]["tool_version"], TOOL_VERSION)
        self.assertEqual(
            normalized[0]["framework_adapter"],
            "springboot-jdk-ast-index",
        )
        self.assertEqual(source["snapshot_kind"], "git")
        self.assertEqual(source["snapshot_id"], "b" * 64)
        self.assertEqual(source["content_sha256"], content_hash)
        self.assertEqual(source["line"], 12)
        self.assertEqual(source["end_line"], 12)


if __name__ == "__main__":
    unittest.main()

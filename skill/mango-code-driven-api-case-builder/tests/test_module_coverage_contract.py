#!/usr/bin/env python3
"""Keep the Skill examples aligned with the module-coverage MCP contract."""

from __future__ import annotations

import ast
import json
import re
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = SKILL_ROOT.parents[1]
SERVER_ROOT = REPOSITORY_ROOT / "MangoServer"
sys.path.insert(0, str(SERVER_ROOT))
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from src.apps.auto_api.schemas.module_coverage import (  # noqa: E402
    ModuleCoverageCasePayload,
    ModuleCoverageInterfacePayload,
)
from _common import SCHEMA_VERSION as SCANNER_SCHEMA_VERSION  # noqa: E402


def json_example(source: str, payload_field: str) -> dict:
    for block in re.findall(r"```json\s+(.*?)```", source, re.DOTALL):
        item = json.loads(block)
        if isinstance(item, dict) and payload_field in item.get("payload", {}):
            return item
    raise AssertionError(f"Missing JSON payload example for {payload_field}")


class ModuleCoverageSkillContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")

    def test_documented_interface_example_matches_platform_schema(self) -> None:
        item = json_example(self.skill_text, "mermaid")
        payload = ModuleCoverageInterfacePayload.model_validate(item["payload"])

        self.assertEqual(payload.method, "GET")
        self.assertEqual(set(payload.branch_ids), {"condition_yes", "condition_no"})
        for branch_id in payload.branch_ids:
            self.assertIn(f"{branch_id}@", payload.mermaid)

    def test_documented_case_example_matches_platform_schema(self) -> None:
        item = json_example(self.skill_text, "case_title")
        payload = ModuleCoverageCasePayload.model_validate(item["payload"])

        self.assertEqual(payload.current_status, "pending_create")
        self.assertNotIn("case_no", item["payload"])
        self.assertNotIn("automation_decision", item["payload"])
        self.assertNotIn("api_case_id", item)
        self.assertNotIn("api_case_revision_id", item)
        design_payload = ModuleCoverageCasePayload.model_validate({
            **item["payload"],
            "evidence_category": "设计已核验",
        })
        self.assertEqual(design_payload.evidence_category, "设计已核验")

        with self.assertRaises(ValidationError):
            ModuleCoverageCasePayload.model_validate({
                **item["payload"],
                "automation_decision": "automatable",
            })

    def test_mcp_default_and_scanner_versions_remain_independent(self) -> None:
        tool_source = (
            SERVER_ROOT
            / "src/interfaces/mcp/tools/api/module_coverage.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(tool_source)
        create_scan = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "create_module_coverage_scan"
        )
        positional = create_scan.args.args
        defaults = [None] * (len(positional) - len(create_scan.args.defaults))
        defaults.extend(create_scan.args.defaults)
        default_by_name = {
            argument.arg: default
            for argument, default in zip(positional, defaults, strict=True)
        }

        self.assertEqual(ast.literal_eval(default_by_name["schema_version"]), 3)
        self.assertEqual(SCANNER_SCHEMA_VERSION, "3.0")
        self.assertIn("`schema_version=3`", self.skill_text)
        self.assertIn('`"3.0"`', self.skill_text)
        self.assertIn("`completed_with_gaps`", self.skill_text)
        self.assertIn("`valid_with_gaps=true`", self.skill_text)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from src.interfaces.mcp.skill_catalog import McpSkillCatalogService


class McpSkillCatalogServiceTests(SimpleTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.skill_root = Path(self.temp_dir.name)
        (self.skill_root / "introductions.json").write_text(
            json.dumps({
                "sample-skill": {
                    "title": "示例 Skill",
                    "category": "测试",
                    "description": "用于验证 MCP Skill 分发。",
                }
            }, ensure_ascii=False),
            encoding="utf-8",
        )
        skill_dir = self.skill_root / "sample-skill"
        (skill_dir / "references").mkdir(parents=True)
        (skill_dir / "__pycache__").mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: sample-skill\ndescription: sample\n---\n\n# Sample\n",
            encoding="utf-8",
        )
        (skill_dir / "references" / "workflow.md").write_text("# Workflow\n", encoding="utf-8")
        (skill_dir / ".DS_Store").write_bytes(b"hidden")
        (skill_dir / "__pycache__" / "cache.pyc").write_bytes(b"compiled")
        self.env_patch = patch.dict(os.environ, {"MANGO_MCP_SKILL_ROOT": str(self.skill_root)})
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_catalog_uses_introductions_and_excludes_generated_files(self):
        catalog = McpSkillCatalogService.catalog()

        self.assertEqual(catalog["skill_count"], 1)
        skill = catalog["skills"][0]
        self.assertEqual(skill["name"], "sample-skill")
        self.assertEqual(skill["title"], "示例 Skill")
        self.assertEqual(skill["file_count"], 2)
        self.assertEqual(
            [item["path"] for item in skill["files"]],
            ["SKILL.md", "references/workflow.md"],
        )
        self.assertTrue(skill["mcp_enabled"])

    def test_skill_bundle_supports_version_based_update_check(self):
        first = McpSkillCatalogService.get_skill("sample-skill")
        unchanged = McpSkillCatalogService.get_skill(
            "sample-skill",
            known_version=first["version"],
        )
        (self.skill_root / "sample-skill" / "references" / "workflow.md").write_text(
            "# Updated workflow\n",
            encoding="utf-8",
        )
        updated_catalog = McpSkillCatalogService.catalog({"sample-skill": first["version"]})

        self.assertFalse(first["not_modified"])
        self.assertTrue(unchanged["not_modified"])
        self.assertEqual(unchanged["files"], [])
        self.assertTrue(updated_catalog["skills"][0]["update_available"])
        self.assertNotEqual(updated_catalog["skills"][0]["version"], first["version"])

    def test_skill_resource_fragment_is_not_part_of_skill_name(self):
        result = McpSkillCatalogService.get_skill('sample-skill#SKILL.md')

        self.assertEqual(result['name'], 'sample-skill')
        self.assertEqual(result['entrypoint'], 'SKILL.md')

    def test_single_file_read_and_path_traversal_protection(self):
        result = McpSkillCatalogService.get_skill(
            "sample-skill",
            file_path="references/workflow.md",
        )

        self.assertEqual(len(result["files"]), 1)
        self.assertEqual(result["files"][0]["encoding"], "utf-8")
        self.assertEqual(result["files"][0]["content"], "# Workflow\n")
        with self.assertRaises(FileNotFoundError):
            McpSkillCatalogService.get_skill("sample-skill", file_path="../introductions.json")

    def test_unregistered_skill_is_not_exposed(self):
        unregistered = self.skill_root / "unregistered"
        unregistered.mkdir()
        (unregistered / "SKILL.md").write_text("# Hidden\n", encoding="utf-8")

        with self.assertRaises(KeyError):
            McpSkillCatalogService.get_skill("unregistered")

    def test_mcp_disabled_skill_is_hidden_and_cannot_be_read_directly(self):
        introductions_path = self.skill_root / "introductions.json"
        introductions = json.loads(introductions_path.read_text(encoding="utf-8"))
        introductions["restricted-skill"] = {
            "title": "受限 Skill",
            "mcp_enabled": False,
        }
        introductions_path.write_text(
            json.dumps(introductions, ensure_ascii=False),
            encoding="utf-8",
        )
        restricted_dir = self.skill_root / "restricted-skill"
        restricted_dir.mkdir()
        (restricted_dir / "SKILL.md").write_text("# Restricted\n", encoding="utf-8")

        catalog = McpSkillCatalogService.catalog()

        self.assertEqual([item["name"] for item in catalog["skills"]], ["sample-skill"])
        with self.assertRaises(KeyError):
            McpSkillCatalogService.get_skill("restricted-skill")


class RepositorySkillCatalogTests(SimpleTestCase):
    def test_every_introduced_skill_has_entrypoint(self):
        with patch.dict(os.environ, {"MANGO_MCP_SKILL_ROOT": ""}):
            introductions = McpSkillCatalogService.introductions()
            catalog = McpSkillCatalogService.catalog()

        self.assertIn("mango-data-factory-builder", introductions)
        self.assertTrue(introductions["mango-test-case-document-builder"]["mcp_enabled"])
        self.assertTrue(all(metadata["mcp_enabled"] for metadata in introductions.values()))
        self.assertEqual(
            catalog["skill_count"],
            sum(metadata.get("mcp_enabled", True) for metadata in introductions.values()),
        )
        self.assertIn(
            "mango-test-case-document-builder",
            {item["name"] for item in catalog["skills"]},
        )
        self.assertTrue(all(item["file_count"] > 0 for item in catalog["skills"]))

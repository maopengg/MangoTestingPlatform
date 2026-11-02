from importlib import import_module
from types import SimpleNamespace
from unittest.mock import MagicMock
import re

from django.db.backends.mysql.schema import DatabaseSchemaEditor
from django.test import SimpleTestCase


cleanup = import_module("src.apps.system.migrations.0052_remove_retired_ai_tables")


class RetiredAiCleanupTests(SimpleTestCase):
    def editor(self, tables, *, legacy_column=False, constraints=None, vendor="mysql"):
        tables = set(tables)
        constraints = {table: dict(values) for table, values in (constraints or {}).items()}
        columns = {"mcp_tool_id", "binding_snapshot", "mcp_config"} if legacy_column else {"binding_snapshot", "mcp_config"}
        connection = MagicMock(vendor=vendor)
        connection.introspection.table_names.side_effect = lambda cursor: sorted(tables)
        connection.introspection.get_table_description.side_effect = lambda cursor, table: [
            SimpleNamespace(name=name) for name in sorted(columns)
        ]
        connection.introspection.get_constraints.side_effect = lambda cursor, table: dict(constraints.get(table, {}))
        editor = SimpleNamespace(
            connection=connection,
            quote_name=lambda name: "`" + name.replace("`", "``") + "`",
            sql_delete_fk=DatabaseSchemaEditor.sql_delete_fk,
            sql_delete_column=DatabaseSchemaEditor.sql_delete_column,
            sql_delete_table=DatabaseSchemaEditor.sql_delete_table,
        )

        def execute(sql):
            names = re.findall(r"`([^`]+)`", sql)
            if "DROP FOREIGN KEY" in sql:
                constraints[names[0]].pop(names[1])
            elif "DROP COLUMN" in sql:
                columns.remove(names[1])
            elif sql.startswith("DROP TABLE"):
                tables.remove(names[0])

        editor.execute = MagicMock(side_effect=execute)
        return editor, tables, columns

    def test_fresh_database_does_not_issue_any_ddl(self):
        editor, _, _ = self.editor({"api_info_mcp_config", "api_case", "runtime_kv"})
        cleanup.remove_retired_ai_tables(None, editor)
        editor.execute.assert_not_called()

    def test_cleanup_removes_internal_cycles_and_only_the_known_external_column(self):
        retired = set(cleanup.RETIRED_TABLES)
        editor, tables, columns = self.editor(retired | {"api_info_mcp_config", "api_case", "ui_element_ai"},
            legacy_column=True, constraints={
                "ai_agent_task": {"fk_checkpoint": {"columns": ["checkpoint_id"], "foreign_key": ("ai_agent_artifact", "id")}},
                "ai_agent_artifact": {"fk_task": {"columns": ["task_id"], "foreign_key": ("ai_agent_task", "id")}},
                "api_info_mcp_config": {"fk_old_tool": {"columns": ["mcp_tool_id"], "foreign_key": ("ai_mcp_tool", "id")}},
            })
        cleanup.remove_retired_ai_tables(None, editor)
        self.assertEqual(tables, {"api_info_mcp_config", "api_case", "ui_element_ai"})
        self.assertEqual(columns, {"binding_snapshot", "mcp_config"})
        statements = [call.args[0] for call in editor.execute.call_args_list]
        first_drop = next(i for i, sql in enumerate(statements) if sql.startswith("DROP TABLE"))
        self.assertTrue(all("ALTER TABLE" in sql for sql in statements[:first_drop]))
        self.assertFalse(any("FOREIGN_KEY_CHECKS" in sql for sql in statements))
        editor.execute.reset_mock()
        cleanup.remove_retired_ai_tables(None, editor)
        editor.execute.assert_not_called()

    def test_unknown_surviving_reference_stops_before_any_mutation(self):
        editor, _, _ = self.editor({"ai_mcp_tool", "api_info_mcp_config", "other_business"},
            legacy_column=True, constraints={
                "api_info_mcp_config": {"fk_old_tool": {"columns": ["mcp_tool_id"], "foreign_key": ("ai_mcp_tool", "id")}},
                "other_business": {"unexpected_ai_fk": {"columns": ["tool_id"], "foreign_key": ("ai_mcp_tool", "id")}},
            })
        with self.assertRaisesRegex(RuntimeError, "other_business.unexpected_ai_fk"):
            cleanup.remove_retired_ai_tables(None, editor)
        editor.execute.assert_not_called()

    def test_unexpected_legacy_column_relation_stops_before_any_mutation(self):
        editor, _, _ = self.editor({"api_info_mcp_config", "another_tool"}, legacy_column=True, constraints={
            "api_info_mcp_config": {"new_relation": {"columns": ["mcp_tool_id"], "foreign_key": ("another_tool", "id")}},
        })
        with self.assertRaisesRegex(RuntimeError, "api_info_mcp_config.new_relation"):
            cleanup.remove_retired_ai_tables(None, editor)
        editor.execute.assert_not_called()

    def test_interrupted_mysql_ddl_can_resume_without_repeating_removed_tables(self):
        editor, tables, _ = self.editor({"ai_skill", "ai_skill_version", "api_case"})
        execute = editor.execute.side_effect
        attempts = 0

        def interrupt(sql):
            nonlocal attempts
            attempts += 1
            if attempts == 2:
                raise RuntimeError("simulated connection loss")
            execute(sql)

        editor.execute.side_effect = interrupt
        with self.assertRaisesRegex(RuntimeError, "simulated connection loss"):
            cleanup.remove_retired_ai_tables(None, editor)
        self.assertEqual(tables, {"ai_skill_version", "api_case"})
        editor.execute.side_effect = execute
        editor.execute.reset_mock()
        cleanup.remove_retired_ai_tables(None, editor)
        self.assertEqual(tables, {"api_case"})
        self.assertEqual(editor.execute.call_args.args[0], "DROP TABLE `ai_skill_version`")

    def test_non_mysql_cleanup_fails_without_ddl(self):
        editor, _, _ = self.editor({"ai_skill"}, vendor="sqlite")
        with self.assertRaisesRegex(RuntimeError, "MySQL"):
            cleanup.remove_retired_ai_tables(None, editor)
        editor.execute.assert_not_called()

    def test_retry_after_legacy_column_removal_only_drops_remaining_table(self):
        editor, tables, columns = self.editor({"ai_mcp_tool", "api_info_mcp_config"},
            legacy_column=True, constraints={
                "api_info_mcp_config": {"fk_old_tool": {"columns": ["mcp_tool_id"], "foreign_key": ("ai_mcp_tool", "id")}},
            })
        execute = editor.execute.side_effect

        def interrupt(sql):
            if sql.startswith("DROP TABLE"):
                raise RuntimeError("simulated table lock timeout")
            execute(sql)

        editor.execute.side_effect = interrupt
        with self.assertRaisesRegex(RuntimeError, "simulated table lock timeout"):
            cleanup.remove_retired_ai_tables(None, editor)
        self.assertNotIn("mcp_tool_id", columns)
        editor.execute.side_effect = execute
        editor.execute.reset_mock()
        cleanup.remove_retired_ai_tables(None, editor)
        self.assertEqual(tables, {"api_info_mcp_config"})
        editor.execute.assert_called_once_with("DROP TABLE `ai_mcp_tool`")

    def test_migration_is_irreversible_database_only_and_uses_existing_api_baseline(self):
        self.assertFalse(cleanup.Migration.atomic)
        self.assertIn(("auto_api", "0046_apiauthconfig_target_address"), cleanup.Migration.dependencies)
        self.assertFalse(any(app == 'auto_api' and name.startswith('0047')
                             for app, name in cleanup.Migration.dependencies))
        operation, = cleanup.Migration.operations
        self.assertFalse(operation.reversible)
        state = object()
        self.assertIsNone(operation.state_forwards("auto_system", state))

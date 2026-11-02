"""Remove physical tables whose historical AI models have been retired."""

from django.db import migrations


RETIRED_TABLES = frozenset({
    "ai_skill", "ai_skill_version", "ai_agent_definition",
    "ai_mcp_server", "ai_mcp_tool", "ai_mcp_tool_snapshot",
    "ai_agent_task", "ai_agent_task_step", "ai_agent_tool_call", "ai_agent_task_item",
    "ai_agent_artifact", "ai_agent_evaluation", "ai_agent_event", "ai_agent_context",
    "ai_assistant_session", "ai_assistant_message",
    "api_info_mcp_binding",
    # These temporary replacement models were also removed. Most environments
    # never created them; handle environments that did without recreating an App.
    "case_generation_task", "case_generation_step", "case_generation_item",
    "case_generation_tool_call", "case_generation_history",
})
MCP_CONFIG_TABLE = "api_info_mcp_config"
LEGACY_TOOL_COLUMN = "mcp_tool_id"


def remove_retired_ai_tables(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
        retired = tables & RETIRED_TABLES
        has_legacy_column = MCP_CONFIG_TABLE in tables and any(
            field.name == LEGACY_TOOL_COLUMN
            for field in connection.introspection.get_table_description(cursor, MCP_CONFIG_TABLE)
        )
        if not retired and not has_legacy_column:
            return
        if connection.vendor != "mysql":
            raise RuntimeError("旧 AI 表清理仅支持本项目的 MySQL 数据库；未执行任何清理。")

        constraints = {
            table: connection.introspection.get_constraints(cursor, table)
            for table in sorted(tables)
        }

    foreign_keys = []
    blocked = []
    for table, definitions in constraints.items():
        for name, definition in definitions.items():
            target = definition.get("foreign_key")
            if not target:
                continue
            columns = definition.get("columns") or []
            legacy_tool = table == MCP_CONFIG_TABLE and LEGACY_TOOL_COLUMN in columns
            if legacy_tool and (columns != [LEGACY_TOOL_COLUMN] or target != ("ai_mcp_tool", "id")):
                blocked.append(f"{table}.{name}")
                continue
            if target[0] not in retired and not legacy_tool:
                continue
            if table not in retired and not legacy_tool:
                blocked.append(f"{table}.{name}")
                continue
            foreign_keys.append((table, name))

    # Preflight every incoming reference before issuing any DDL. Do not disable
    # foreign-key checks or silently remove a surviving business relationship.
    if blocked:
        raise RuntimeError(
            "存在未约定的旧 AI 表引用，未执行任何清理，请先审查：" + ", ".join(sorted(blocked))
        )

    quote = schema_editor.quote_name
    for table, name in foreign_keys:
        schema_editor.execute(schema_editor.sql_delete_fk % {"table": quote(table), "name": quote(name)})
    if has_legacy_column:
        schema_editor.execute(schema_editor.sql_delete_column % {
            "table": quote(MCP_CONFIG_TABLE), "column": quote(LEGACY_TOOL_COLUMN),
        })
    for table in sorted(retired):
        schema_editor.execute("DROP TABLE " + quote(table))


class Migration(migrations.Migration):
    # MySQL DDL commits independently. Every retry re-introspects the remaining
    # tables/constraints so an interrupted cleanup can continue without fake.
    atomic = False

    dependencies = [
        ("auto_system", "0051_runtimekventry"),
        # 清理仅依赖已存在的协议表，并自行检查旧列；不绑定后续可重新生成的迁移。
        ("auto_api", "0046_apiauthconfig_target_address"),
    ]

    operations = [migrations.RunPython(remove_retired_ai_tables, atomic=False)]

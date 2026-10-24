from __future__ import annotations

from mangotools.enums import StatusEnum

from src.apps.data_factory.selectors.querysets import DataFactoryQuerySelector
from src.apps.data_factory.services.data_source_execution_request import DataSourceExecutionRequestService
from src.apps.data_factory.services.datasource import (
    DataFactoryDatasourceMutationService,
    DataFactoryDatasourceResolver,
    is_missing_value,
)
from src.apps.data_factory.services.datasource_target import DatasourceTargetService
from src.apps.data_factory.services.discover import DataFactoryDiscover
from src.apps.test_center.exceptions import TEST_ENVIRONMENT_REQUIRED, TestCenterError
from src.apps.test_center.services.data_source import DataSourceConnectionService
from src.interfaces.mcp.audit import mcp_current_user_id
from src.interfaces.mcp.common import paginate_list, paginate_queryset
from .helpers import _selected_test_env
from .helpers import (
    current_user,
    ok,
)


def register_datasource_tools(mcp):
    @mcp.tool()
    def list_data_factory_datasource_aliases(
            project_product_id: int | None = None,
            keyword: str | None = None,
            enabled_only: bool = True,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询数据工厂逻辑数据库。"""
        from src.interfaces.mcp.authentication import scope_queryset_for_user

        queryset = scope_queryset_for_user(
            current_user(),
            DataFactoryQuerySelector.data_factory_datasource_alias().select_related("project_product",
                                                                                    "project_product__project").all(),
        )
        if project_product_id is not None:
            queryset = queryset.filter(project_product_id=project_product_id)
        if keyword:
            queryset = queryset.filter(name__contains=keyword)
        if enabled_only:
            queryset = queryset.filter(status=StatusEnum.SUCCESS.value)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("-id"), page, page_size)
        return ok(
            {
                "items": [
                    {
                        "id": item.id,
                        "name": item.name,
                        "source_category": item.source_category,
                        "db_type": item.db_type,
                        "description": item.description,
                        "project_product_id": item.project_product_id,
                        "project_product_name": item.project_product.name,
                        "status": item.status,
                    }
                    for item in queryset
                ],
                "count": count,
                "page": page,
                "page_size": page_size,
            }
        )

    @mcp.tool()
    def create_data_factory_datasource_alias(
            project_product_id: int,
            name: str,
            source_category: int = 0,
            db_type: int = 0,
            description: str | None = None,
            status: int = StatusEnum.SUCCESS.value,
    ) -> dict:
        """创建数据工厂逻辑数据库。"""
        data = DataFactoryDatasourceMutationService.create_alias(
            {
                "project_product": project_product_id,
                "name": name,
                "source_category": source_category,
                "db_type": db_type,
                "description": description,
                "status": status,
            },
            operator_id=mcp_current_user_id(),
        )
        return ok({"datasource_alias_id": data["id"], **data}, "逻辑数据库创建成功")

    @mcp.tool()
    def list_data_factory_datasource_bindings(
            datasource_alias_id: int | None = None,
            environment: int | None = None,
            project_product_id: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询逻辑数据库与环境下全局数据库连接的绑定。"""
        from src.interfaces.mcp.authentication import scope_queryset_for_user

        queryset = scope_queryset_for_user(
            current_user(),
            DataFactoryQuerySelector.data_factory_datasource_binding().select_related(
                "datasource_alias",
                "database",
            ),
            "datasource_alias__project_product_id",
        )
        if datasource_alias_id is not None:
            queryset = queryset.filter(datasource_alias_id=datasource_alias_id)
        if environment is not None:
            queryset = queryset.filter(environment=environment)
        if project_product_id is not None:
            queryset = queryset.filter(datasource_alias__project_product_id=project_product_id)
        queryset, count, page, page_size = paginate_queryset(queryset.order_by("-id"), page, page_size)
        return ok(
            {
                "items": [
                    {
                        "id": item.id,
                        "datasource_alias_id": item.datasource_alias_id,
                        "datasource_alias_name": item.datasource_alias.name,
                        "environment": item.environment,
                        "data_source_id": item.database_id,
                        "database_name": item.database_name,
                        "schema_name": item.schema_name,
                        "redis_db": item.redis_db,
                        "data_source_name": DataSourceConnectionService.connection_name(item.database),
                        "data_source_alias": item.database.display_name or None,
                        "data_source_label": DataSourceConnectionService.display_label(item.database),
                        "allow_query": item.db_c_status == StatusEnum.SUCCESS.value,
                        "allow_write": item.db_rud_status == StatusEnum.SUCCESS.value,
                        "description": item.description,
                    }
                    for item in queryset
                ],
                "count": count,
                "page": page,
                "page_size": page_size,
            }
        )

    @mcp.tool()
    def create_data_factory_datasource_binding(
            datasource_alias_id: int,
            environment: int,
            data_source_id: int,
            allow_query: bool = False,
            allow_write: bool = False,
            description: str | None = None,
            database_name: str = '',
            schema_name: str = '',
            redis_db: int | None = None,
    ) -> dict:
        """创建逻辑数据库到全局数据库连接的环境绑定。"""
        data = DataFactoryDatasourceMutationService.create_binding(
            {
                "datasource_alias": datasource_alias_id,
                "environment": environment,
                "data_source": data_source_id,
                "database_name": database_name,
                "schema_name": schema_name,
                "redis_db": redis_db,
                "db_c_status": StatusEnum.SUCCESS.value if allow_query else StatusEnum.FAIL.value,
                "db_rud_status": StatusEnum.SUCCESS.value if allow_write else StatusEnum.FAIL.value,
                "description": description,
            },
            operator_id=mcp_current_user_id(),
        )
        return ok({"binding_id": data["id"], **data}, "数据库绑定创建成功")

    @mcp.tool()
    def update_data_factory_datasource_binding(
            binding_id: int,
            data_source_id: int | None = None,
            allow_query: bool | None = None,
            allow_write: bool | None = None,
            description: str | None = None,
            database_name: str | None = None,
            schema_name: str | None = None,
            redis_db: int | None = None,
    ) -> dict:
        """编辑已有环境绑定的实际数据库连接和读写权限；不改变逻辑数据库与测试环境。"""
        payload = {}
        if database_name is not None:
            payload['database_name'] = database_name
        if schema_name is not None:
            payload['schema_name'] = schema_name
        if redis_db is not None:
            payload['redis_db'] = redis_db
        if data_source_id is not None:
            payload["data_source"] = data_source_id
        if allow_query is not None:
            payload["db_c_status"] = StatusEnum.SUCCESS.value if allow_query else StatusEnum.FAIL.value
        if allow_write is not None:
            payload["db_rud_status"] = StatusEnum.SUCCESS.value if allow_write else StatusEnum.FAIL.value
        if description is not None:
            payload["description"] = description
        data = DataFactoryDatasourceMutationService.update_binding(
            binding_id,
            payload,
            operator_id=mcp_current_user_id(),
        )
        return ok({"binding_id": data["id"], **data}, "数据库绑定修改成功")

    @mcp.tool()
    def test_data_factory_datasource_connection(
            datasource_alias_id: int,
            project_product_id: int,
            test_env: int | None = None,
            user_id: int | None = None,
    ) -> dict:
        """测试逻辑数据库在指定环境绑定的数据库连接。"""
        env = _selected_test_env(user_id, test_env)
        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
            datasource_alias_id, project_product_id, env,
        )
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
        return ok(DataSourceConnectionService.diagnose_connection(DatasourceTargetService.resolve(binding)),
                  "数据库连接测试完成")

    @mcp.tool()
    def list_data_factory_database_tables(
            datasource_alias_id: int,
            project_product_id: int,
            test_env: int | None = None,
            user_id: int | None = None,
            page: int = 1,
            page_size: int = 10,
    ) -> dict:
        """查询数据工厂数据库中的表列表。"""
        env = _selected_test_env(user_id, test_env)
        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
            datasource_alias_id, project_product_id, env,
        )
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
        items, count, page, page_size = paginate_list(
            DataFactoryDiscover.get_tables(DatasourceTargetService.for_metadata(binding)), page, page_size)
        return ok({"items": items, "count": count, "page": page, "page_size": page_size})

    @mcp.tool()
    def get_data_factory_table_schema(
            table_name: str,
            datasource_alias_id: int,
            project_product_id: int,
            test_env: int | None = None,
            user_id: int | None = None,
            schema_name: str | None = None,
    ) -> dict:
        """查询数据工厂数据库中的单表实时字段 schema。

        可用于修复已停用实体：先与 get_data_factory_entity_detail 返回的 fields
        对比并按字段名合并。同名字段需保留原 generator_type/generator_config，
        新字段才使用 columns.recommend；不得将 columns 原样覆盖到已有实体。
        必须明确指定正确的 test_env。
        """
        env = _selected_test_env(user_id, test_env)
        binding = DataFactoryDatasourceResolver.resolve_binding_by_env(
            datasource_alias_id, project_product_id, env,
        )
        DataFactoryDatasourceResolver.require_binding_permission(binding, write=False)
        return ok(
            DataFactoryDiscover.get_table_schema(DatasourceTargetService.for_metadata(binding, schema_name=schema_name),
                                                 table_name))

    @mcp.tool()
    def query_data_factory_datasource_sql(
            sql: str,
            datasource_alias_id: int,
            project_product_id: int,
            test_env: int,
            limit: int = 10,
    ) -> dict:
        """通过逻辑数据库执行只读 SQL 查询，必须明确传入测试环境，默认返回 10 行。"""
        if is_missing_value(test_env):
            raise TestCenterError(TEST_ENVIRONMENT_REQUIRED)
        try:
            max_rows = max(1, min(int(limit or 10), 100))
        except (TypeError, ValueError):
            max_rows = 10
        result = DataSourceExecutionRequestService.execute_operation(
            datasource_alias_id=datasource_alias_id,
            project_product_id=project_product_id,
            test_env=test_env,
            operation_config=sql,
            confirm_write=False,
            source_context={
                'source_type': 'mcp',
                'source_stage': 'query',
                'source_id': datasource_alias_id,
                'mcp_tool_name': 'query_data_factory_datasource_sql',
            },
        )
        rows = list(result.get('rows') or [])[:max_rows]
        result['rows'] = rows
        result['result'] = rows
        result['row_count'] = len(rows)
        return ok(result, "SQL查询成功")

    @mcp.tool()
    def query_data_factory_datasource_redis(
            command: str,
            datasource_alias_id: int,
            project_product_id: int,
            test_env: int,
    ) -> dict:
        """通过逻辑数据库执行 Redis 只读命令；写命令和高风险命令会被拒绝。"""
        if is_missing_value(test_env):
            raise TestCenterError(TEST_ENVIRONMENT_REQUIRED)
        result = DataSourceExecutionRequestService.execute_operation(
            datasource_alias_id=datasource_alias_id,
            project_product_id=project_product_id,
            test_env=test_env,
            operation_config=command,
            confirm_write=False,
        )
        return ok(result, "Redis查询成功")

    @mcp.tool()
    def query_data_factory_datasource_elasticsearch(
            index: str,
            query: dict,
            datasource_alias_id: int,
            project_product_id: int,
            test_env: int,
    ) -> dict:
        """通过逻辑数据库执行 Elasticsearch 索引 _search 查询，最多返回 100 条。"""
        if is_missing_value(test_env):
            raise TestCenterError(TEST_ENVIRONMENT_REQUIRED)
        result = DataSourceExecutionRequestService.execute_operation(
            datasource_alias_id=datasource_alias_id,
            project_product_id=project_product_id,
            test_env=test_env,
            operation_config={"index": index, "query": query},
            confirm_write=False,
        )
        return ok(result, "Elasticsearch查询成功")

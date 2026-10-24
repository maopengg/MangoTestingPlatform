from typing import Any
import uuid

from src.exceptions import ToolsError
from src.network import HTTP


class UiDataSourceExecutionService:
    """UI 执行器的数据库操作入口；真实连接和权限统一由平台后端处理。"""

    @staticmethod
    def _plain_item(item) -> dict:
        if hasattr(item, 'model_dump'):
            return item.model_dump(mode='json')
        return dict(item or {})

    @staticmethod
    def _operation(item: dict):
        return item.get('value') if 'value' in item else item.get('sql')

    @staticmethod
    def _cache_key(item: dict):
        return item.get('key') if 'key' in item else item.get('key_list')

    @classmethod
    def cache_record(cls, key, result: dict) -> dict | None:
        rows = result.get('rows') or []
        if rows and isinstance(rows[0], dict):
            first = rows[0]
            source = first.get('_source')
            return source if isinstance(source, dict) else first

        value = result.get('result')
        if result.get('command') == 'HGETALL' and isinstance(value, list):
            value = dict(zip(value[::2], value[1::2]))
        if isinstance(value, dict):
            return value

        keys = key if isinstance(key, list) else [part.strip() for part in str(key or '').split(',')]
        keys = [part for part in keys if part]
        if isinstance(value, (list, tuple)):
            return {name: item for name, item in zip(keys, value)}
        return {keys[0]: value} if keys and value is not None else None

    @classmethod
    async def execute(
            cls,
            *,
            item,
            project_product_id,
            test_env,
            test_data,
            require_cache_result: bool = False,
            confirm_write: bool = True,
            source_context: dict | None = None,
            request_id: str | None = None,
    ) -> dict:
        item = cls._plain_item(item)
        operation_config: Any = test_data.replace(cls._operation(item))
        result = await HTTP.data_source.execute(
            datasource_alias_id=item.get('datasource_alias'),
            project_product_id=project_product_id,
            test_env=test_env,
            operation_config=operation_config,
            confirm_write=confirm_write,
            source_context=source_context or {
                'source_type': 'ui_runtime',
                'source_stage': 'database_operation',
            },
            request_id=request_id or uuid.uuid4().hex,
        )
        key = cls._cache_key(item)
        if key not in [None, '', []]:
            cache_record = cls.cache_record(key, result)
            if not cache_record:
                if require_cache_result:
                    raise ToolsError(300, f'数据源查询没有返回可缓存的数据，缓存 Key：{key}')
            else:
                cache_key = ','.join(str(part) for part in key) if isinstance(key, list) else key
                test_data.set_sql_cache(cache_key, cache_record)
        return result


class UiDataSourceExecutionCallback:
    """供第三方自动化库调用的平台数据源异步回调。"""

    def __init__(
            self,
            *,
            project_product_id,
            test_env,
            test_data,
            source_context: dict,
    ):
        self.project_product_id = project_product_id
        self.test_env = test_env
        self.test_data = test_data
        self.source_context = dict(source_context)

    async def __call__(
            self,
            *,
            operation_config,
            datasource_alias_id=None,
            source_context: dict | None = None,
    ):
        merged_context = {**self.source_context, **(source_context or {})}
        result = await UiDataSourceExecutionService.execute(
            item={
                'datasource_alias': datasource_alias_id,
                'value': operation_config,
            },
            project_product_id=self.project_product_id,
            test_env=self.test_env,
            test_data=self.test_data,
            confirm_write=True,
            source_context=merged_context,
        )
        if 'rows' in result:
            return result.get('rows') or []
        if 'result' in result:
            return result.get('result')
        return result.get('affected_rows')

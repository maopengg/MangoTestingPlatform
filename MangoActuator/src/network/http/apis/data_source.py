from src.exceptions import ToolsError
from src.models.socket_model import HttpApiResponse
from src.network.http.apis.base import BaseApi


class DataSourceApi(BaseApi):
    async def execute(
            self,
            *,
            datasource_alias_id,
            project_product_id,
            test_env,
            operation_config,
            confirm_write: bool = True,
            source_context: dict | None = None,
            request_id: str | None = None,
    ) -> dict:
        payload = {
            'action': 'execute',
            'datasource_alias_id': datasource_alias_id,
            'project_product_id': project_product_id,
            'test_env': test_env,
            'operation_config': operation_config,
            'confirm_write': confirm_write,
            'source_context': source_context,
            'request_id': request_id,
        }
        response_data = await self.client.post(
            'data-factory/data-source/execute',
            json=payload,
            headers=self._headers(),
        )
        response = HttpApiResponse(**response_data) if isinstance(response_data, dict) else response_data
        if not isinstance(response, HttpApiResponse):
            raise ToolsError(300, '数据源执行接口返回格式不正确')
        if response.code != 200:
            raise ToolsError(response.code, response.msg)
        return response.data if isinstance(response.data, dict) else {}

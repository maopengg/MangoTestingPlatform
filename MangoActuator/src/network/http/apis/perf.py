from src.network.http.apis.base import ApiError, BaseApi


class PerfApi(BaseApi):
    @staticmethod
    def _require_success(response) -> dict:
        if not isinstance(response, dict) or response.get("code") != 200:
            raise ApiError(str(response.get("msg") if isinstance(response, dict) else "性能接口返回格式错误"))
        return response

    async def ready(self, node_id: int, connection_id: str, data: dict):
        response = await self.client.post(f"perf/run-node/{node_id}/ready", json={**data, "connection_id": connection_id}, headers=self._headers())
        return self._require_success(response)

    async def control(self, node_id: int, connection_id: str):
        response = await self.client.get(f"perf/run-node/{node_id}/control", params={"connection_id": connection_id}, headers=self._headers({"X-Executor-Connection-Id": connection_id}))
        return self._require_success(response)

    async def heartbeat(self, node_id: int, connection_id: str, data: dict):
        response = await self.client.post(f"perf/run-node/{node_id}/heartbeat", json={**data, "connection_id": connection_id}, headers=self._headers())
        return self._require_success(response)

    async def metrics(self, node_id: int, connection_id: str, data: dict):
        response = await self.client.post(f"perf/run-node/{node_id}/metrics/batch", json=data, headers=self._headers({"X-Executor-Connection-Id": connection_id}), timeout=30)
        return self._require_success(response)

    async def errors(self, node_id: int, connection_id: str, data: dict):
        response = await self.client.post(f"perf/run-node/{node_id}/errors/batch", json=data, headers=self._headers({"X-Executor-Connection-Id": connection_id}), timeout=30)
        return self._require_success(response)

    async def secrets(self, node_id: int, connection_id: str):
        response = await self.client.get(f"perf/run-node/{node_id}/secrets", params={"connection_id": connection_id}, headers=self._headers({"X-Executor-Connection-Id": connection_id}), timeout=30)
        return self._require_success(response)

    async def result(self, node_id: int, connection_id: str, data: dict):
        response = await self.client.post(f"perf/run-node/{node_id}/result", json={**data, "connection_id": connection_id}, headers=self._headers(), timeout=30)
        return self._require_success(response)

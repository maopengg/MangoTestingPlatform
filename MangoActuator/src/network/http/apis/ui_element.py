# -*- coding: utf-8 -*-
from src.network.http.apis.base import BaseApi


class UiElementApi(BaseApi):

    async def ai_info(self, element_id: int, test_env: int | None = None):
        params = {'element_id': element_id}
        if test_env is not None:
            params['test_env'] = test_env
        resp = await self.client.get(
            'ui/element/ai/info',
            params=params,
            headers=self._headers(),
        )
        return resp.get('data') if isinstance(resp, dict) else {}

    async def save_snapshot(self, data: dict):
        resp = await self.client.post(
            'ui/element/ai/snapshot',
            json=data,
            headers=self._headers(),
            timeout=30,
        )
        return resp.get('data') if isinstance(resp, dict) else {}

    async def save_heal_record(self, data: dict):
        resp = await self.client.post(
            'ui/element/ai/heal-record',
            json=data,
            headers=self._headers(),
            timeout=30,
        )
        return resp.get('data') if isinstance(resp, dict) else {}

    async def save_runtime_result(self, data: dict):
        resp = await self.client.post(
            'ui/element/runtime-result',
            json=data,
            headers=self._headers(),
            timeout=30,
        )
        return resp.get('data') if isinstance(resp, dict) else {}

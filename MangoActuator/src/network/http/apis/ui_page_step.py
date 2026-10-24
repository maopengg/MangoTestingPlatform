# -*- coding: utf-8 -*-
from src.network.http.apis.base import BaseApi


class UiPageStepApi(BaseApi):
    async def save_heal_report(self, data: dict):
        response = await self.client.post(
            'ui/page/steps/healing/report',
            json=data,
            headers=self._headers(),
            timeout=30,
        )
        return response.get('data') if isinstance(response, dict) else {}

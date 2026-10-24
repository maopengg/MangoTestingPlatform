# -*- coding: utf-8 -*-
from copy import deepcopy

from src.network import HTTP


class PlatformMemoryProvider:
    def __init__(self):
        self._sync_cache: dict[tuple[int, int | None], dict] = {}

    async def load_async(self, element_id: int, test_env: int | None = None) -> dict:
        value = await HTTP.ui_element.ai_info(element_id, test_env)
        value = value if isinstance(value, dict) else {}
        self._sync_cache[(element_id, test_env)] = deepcopy(value)
        return value

    def load_sync(self, element_id: int, test_env: int | None = None) -> dict:
        return deepcopy(self._sync_cache.get((element_id, test_env), {}))


# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2026-06-08 14:20
# @Author : Codex
from dataclasses import dataclass


@dataclass
class AiRuntimeConfig:
    locator_enabled: bool = False
    provider_type: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    timeout: int | None = None

    def can_locate(self) -> bool:
        return self.locator_enabled and bool(self.api_key)


_ai_config = AiRuntimeConfig()


def set_ai_config(config: AiRuntimeConfig):
    global _ai_config
    _ai_config = config


def get_ai_config() -> AiRuntimeConfig:
    return _ai_config

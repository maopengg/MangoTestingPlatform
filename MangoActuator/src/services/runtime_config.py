# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2026-06-08 14:20
# @Author : Codex
from dataclasses import dataclass
from contextvars import ContextVar, Token


@dataclass
class AiRuntimeConfig:
    locator_enabled: bool = True
    locator_mode: int = 2
    locator_semantic_strength: int = 0
    fixed_locator_retry_seconds: int = 10
    smart_locator_timeout_seconds: int = 30
    visual_locator_enabled: bool = False
    provider_type: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None
    timeout: int | None = None
    vision_provider_type: str | None = None
    vision_api_key: str | None = None
    vision_base_url: str | None = None
    vision_model: str | None = None
    vision_timeout: int = 30
    vision_proxy_url: str | None = None

    def can_locate(self) -> bool:
        return self.locator_enabled and bool(self.api_key)


_ai_config = AiRuntimeConfig()
_task_ui_runtime_config: ContextVar[dict | None] = ContextVar(
    'task_ui_runtime_config', default=None,
)


def set_ai_config(config: AiRuntimeConfig):
    global _ai_config
    _ai_config = config


def get_ai_config() -> AiRuntimeConfig:
    return _ai_config


def set_task_ui_runtime_config(value: dict | None) -> Token:
    return _task_ui_runtime_config.set(value if isinstance(value, dict) else None)


def reset_task_ui_runtime_config(token: Token) -> None:
    _task_ui_runtime_config.reset(token)


def get_task_ui_runtime_config() -> dict:
    return dict(_task_ui_runtime_config.get() or {})

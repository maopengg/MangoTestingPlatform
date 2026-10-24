# -*- coding: utf-8 -*-
from src.services.runtime_config import get_ai_config, get_task_ui_runtime_config


class PlatformRuntimeConfig:
    def locator_enabled(self) -> bool:
        return True

    def locator_mode(self) -> int:
        return 2

    def semantic_strength(self) -> int:
        try:
            value = int(get_ai_config().locator_semantic_strength)
        except (TypeError, ValueError):
            value = 0
        return value if value in (0, 20, 50, 80, 100) else 0

    def fixed_locator_retry_seconds(self) -> float:
        value = get_task_ui_runtime_config().get(
            'fixed_locator_retry_seconds', get_ai_config().fixed_locator_retry_seconds,
        )
        return max(0, min(int(value or 0), 60))

    def smart_locator_timeout_seconds(self) -> float:
        value = get_task_ui_runtime_config().get(
            'smart_locator_timeout_seconds', get_ai_config().smart_locator_timeout_seconds,
        )
        return max(5, min(int(value or 30), 120))

    def visual_locator_enabled(self) -> bool:
        value = get_task_ui_runtime_config().get(
            'visual_locator_enabled', get_ai_config().visual_locator_enabled,
        )
        if isinstance(value, str):
            return value.strip().lower() in {'1', 'true', 'yes', 'on'}
        return bool(value)

    def visual_locator_timeout_seconds(self) -> float:
        try:
            value = int(get_ai_config().vision_timeout or 30)
        except (TypeError, ValueError):
            value = 30
        return max(1, min(value, 120))

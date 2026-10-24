# -*- coding: utf-8 -*-
from mangoautomation.element_healing import WebElementHealingHarness

from .platform_event_sink import PlatformEventSink
from .platform_memory_provider import PlatformMemoryProvider
from .platform_model_client import PlatformModelClient
from .platform_vision_model_client import PlatformVisionModelClient
from .runtime_config import PlatformRuntimeConfig


def create_ui_element_healing_harness(test_env: int | None = None):
    return WebElementHealingHarness(
        test_env=test_env,
        memory_provider=PlatformMemoryProvider(),
        event_sink=PlatformEventSink(),
        model_client=PlatformModelClient(),
        vision_model_client=PlatformVisionModelClient(),
        runtime_config=PlatformRuntimeConfig(),
    )

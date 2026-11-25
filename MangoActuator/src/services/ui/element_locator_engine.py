# -*- coding: utf-8 -*-
from mangoautomation.element_healing import WebElementHealingHarness
from src.services.system_error_reporter import ActuatorSystemErrorReporter

from .element_healing import (
    PlatformEventSink,
    PlatformMemoryProvider,
    PlatformModelClient,
    PlatformRuntimeConfig,
    PlatformVisionModelClient,
)


class UiElementLocatorEngine(WebElementHealingHarness):
    """Platform adapter for the reusable Web element-healing Harness."""

    def __init__(self, test_env: int | None = None, logger=None):
        super().__init__(
            test_env=test_env,
            memory_provider=PlatformMemoryProvider(),
            event_sink=PlatformEventSink(),
            model_client=PlatformModelClient(),
            vision_model_client=PlatformVisionModelClient(),
            runtime_config=PlatformRuntimeConfig(),
            logger=logger,
            system_error_callback=ActuatorSystemErrorReporter.report,
        )

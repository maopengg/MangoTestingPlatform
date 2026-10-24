# -*- coding: utf-8 -*-
import json

from src.services.ui.element_healing.platform_model_client import sanitize_debug_payload
from src.tools.executor_task_context import get_executor_task_log_context
from src.tools.log_collector import log


class PlatformEventSink:
    """Trace transport adapter.

    The full trace is already attached to ElementResult.locator_engine and is
    persisted by the existing runtime/heal-record endpoints. The sink remains
    isolated so transport can change without touching the Harness.
    """

    async def emit_async(self, event: str, payload: dict) -> None:
        self._log(event, payload)

    def emit_sync(self, event: str, payload: dict) -> None:
        self._log(event, payload)

    @staticmethod
    def _log(event: str, payload: dict) -> None:
        log.debug(
            '[元素自愈Trace] ' + json.dumps(
                sanitize_debug_payload({
                    'event': event,
                    'task_context': get_executor_task_log_context(),
                    'trace': payload,
                }),
                ensure_ascii=False,
            ),
        )

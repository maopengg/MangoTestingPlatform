# -*- coding: utf-8 -*-
from src.services.system_error_reporter import ActuatorSystemErrorReporter
import json
import re
import uuid

from mangoautomation.element_healing.agent.web import OpenAICompatibleModelClient
from mangoautomation.element_healing.baseline import redact_sensitive_text
from mangoautomation.element_healing.baseline.sanitizer import sanitize_url

from src.services.runtime_config import get_ai_config
from src.settings import settings
from src.tools.executor_task_context import get_executor_task_log_context
from src.tools.log_collector import log


SENSITIVE_LOG_KEY_PATTERN = re.compile(
    r'(password|passwd|pwd|token|secret|authorization|cookie|session|api[-_]?key|access[-_]?key)',
    re.I,
)


def sanitize_debug_payload(value, depth: int = 0):
    """Redact a debug payload without truncating the request being diagnosed."""
    if depth > 12:
        return '[TRUNCATED_DEPTH]'
    if isinstance(value, dict):
        return {
            str(key): (
                '[REDACTED]'
                if SENSITIVE_LOG_KEY_PATTERN.search(str(key))
                else sanitize_debug_payload(item, depth + 1)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_debug_payload(item, depth + 1) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value


class PlatformModelClient:
    def __init__(self, log_scope: str = '元素智能定位', max_timeout_seconds: float | None = None):
        self._client_key = None
        self._client = None
        self.log_scope = log_scope
        self.max_timeout_seconds = max_timeout_seconds

    @property
    def available(self) -> bool:
        config = get_ai_config()
        return bool(config.locator_enabled and config.api_key and config.base_url and config.model)

    @property
    def model_name(self) -> str | None:
        return get_ai_config().model

    async def complete_async(self, messages: list[dict], *, max_tokens: int, temperature: float,
                             response_format: dict | None = None) -> str:
        client = self._get_client()
        if client is None:
            return ''
        request_id = self._debug_request(messages, max_tokens, temperature, response_format)
        try:
            content = await client.complete_async(
                messages, max_tokens=max_tokens, temperature=temperature,
                response_format=response_format,
            )
        except Exception as error:
            await ActuatorSystemErrorReporter.report(error, 'services/ui/element_healing/platform_model_client:complete_async')
            self._debug_response(request_id, error=error)
            raise
        self._debug_response(request_id, content=content)
        return content

    def complete_sync(self, messages: list[dict], *, max_tokens: int, temperature: float,
                      response_format: dict | None = None) -> str:
        client = self._get_client()
        if client is None:
            return ''
        request_id = self._debug_request(messages, max_tokens, temperature, response_format)
        try:
            content = client.complete_sync(
                messages, max_tokens=max_tokens, temperature=temperature,
                response_format=response_format,
            )
        except Exception as error:
            ActuatorSystemErrorReporter.schedule(error, 'services/ui/element_healing/platform_model_client:complete_sync')
            self._debug_response(request_id, error=error)
            raise
        self._debug_response(request_id, content=content)
        return content

    def _debug_request(self, messages, max_tokens, temperature, response_format) -> str | None:
        if not settings.IS_DEBUG:
            return None
        request_id = uuid.uuid4().hex[:12]
        config = get_ai_config()
        payload = sanitize_debug_payload({
            'request_id': request_id,
            'task_context': get_executor_task_log_context(),
            'provider_type': config.provider_type,
            'base_url': sanitize_url(config.base_url),
            'model': config.model,
            'timeout_seconds': config.timeout,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'response_format': response_format,
            # WebLocatorPrompt has already removed input values and sensitive page data;
            # sanitize again at the final logging boundary as defence in depth.
            'messages': messages,
        })
        log.debug(
            f'[{self.log_scope}AI请求] ' + json.dumps(payload, ensure_ascii=False, indent=2),
        )
        return request_id

    def _debug_response(self, request_id: str | None, *, content: str | None = None,
                        error: Exception | None = None) -> None:
        if not settings.IS_DEBUG or request_id is None:
            return
        payload = {
            'request_id': request_id,
            'task_context': get_executor_task_log_context(),
            'model': get_ai_config().model,
            'content': content,
        }
        if error is not None:
            payload['error_type'] = type(error).__name__
            payload['error'] = str(error)
        log.debug(
            f'[{self.log_scope}AI响应] ' + json.dumps(
                sanitize_debug_payload(payload), ensure_ascii=False, indent=2,
            ),
        )

    def _get_client(self):
        if not self.available:
            return None
        config = get_ai_config()
        key = (
            config.api_key, config.base_url, config.model, config.timeout,
            self.max_timeout_seconds,
        )
        if key != self._client_key:
            self._client = OpenAICompatibleModelClient(
                config.api_key,
                config.base_url,
                config.model,
                config.timeout,
                max_timeout_seconds=self.max_timeout_seconds,
            )
            self._client_key = key
        return self._client

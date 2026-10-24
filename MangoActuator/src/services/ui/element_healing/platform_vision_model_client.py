# -*- coding: utf-8 -*-
import json
import uuid

from mangoautomation.element_healing.agent.web import OpenAICompatibleModelClient
from mangoautomation.element_healing.baseline.sanitizer import sanitize_url

from src.services.runtime_config import get_ai_config
from src.settings import settings
from src.tools.executor_task_context import get_executor_task_log_context
from src.tools.log_collector import log

from .platform_model_client import sanitize_debug_payload


SUPPORTED_VISION_PROVIDER_TYPES = {'openai_compatible', 'openai', 'azure_openai'}


class PlatformVisionModelClient:
    def __init__(self):
        self._client_key = None
        self._client = None

    @property
    def available(self) -> bool:
        config = get_ai_config()
        return bool(
            config.visual_locator_enabled and config.vision_api_key and
            config.vision_base_url and config.vision_model and
            str(config.vision_provider_type or '').strip().lower() in
            SUPPORTED_VISION_PROVIDER_TYPES
        )

    @property
    def model_name(self) -> str | None:
        return get_ai_config().vision_model

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
            'provider_type': config.vision_provider_type,
            'base_url': sanitize_url(config.vision_base_url),
            'model': config.vision_model,
            'timeout_seconds': config.vision_timeout,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'response_format': response_format,
            # Never write the screenshot's base64 content to disk. Text context
            # remains available after the standard sensitive-value redaction.
            'messages': self._summarize_messages(messages),
        })
        log.debug(
            '[元素视觉定位AI请求] ' + json.dumps(payload, ensure_ascii=False, indent=2),
        )
        return request_id

    @staticmethod
    def _summarize_messages(messages: list[dict]) -> list[dict]:
        summarized = []
        for message in messages:
            row = dict(message)
            content = row.get('content')
            if isinstance(content, list):
                row['content'] = []
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'image_url':
                        image_url = item.get('image_url') or {}
                        url = image_url.get('url') if isinstance(image_url, dict) else ''
                        row['content'].append({
                            'type': 'image_url',
                            'image_url': '[IMAGE_DATA_REDACTED]',
                            'encoded_length': len(str(url or '')),
                        })
                    else:
                        row['content'].append(item)
            summarized.append(row)
        return summarized

    @staticmethod
    def _debug_response(request_id: str | None, *, content: str | None = None,
                        error: Exception | None = None) -> None:
        if not settings.IS_DEBUG or request_id is None:
            return
        payload = {
            'request_id': request_id,
            'task_context': get_executor_task_log_context(),
            'model': get_ai_config().vision_model,
            'content': content,
        }
        if error is not None:
            payload['error_type'] = type(error).__name__
            payload['error'] = str(error)
        log.debug(
            '[元素视觉定位AI响应] ' + json.dumps(
                sanitize_debug_payload(payload), ensure_ascii=False, indent=2,
            ),
        )

    def _get_client(self):
        if not self.available:
            return None
        config = get_ai_config()
        key = (
            config.vision_provider_type, config.vision_api_key,
            config.vision_base_url, config.vision_model,
            config.vision_timeout, config.vision_proxy_url,
        )
        if key != self._client_key:
            self._client = OpenAICompatibleModelClient(
                config.vision_api_key,
                config.vision_base_url,
                config.vision_model,
                config.vision_timeout,
                proxy_url=config.vision_proxy_url,
                max_timeout_seconds=config.vision_timeout,
            )
            self._client_key = key
        return self._client

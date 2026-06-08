# -*- coding: utf-8 -*-
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

from src.apps.auto_system.service.system_config import SystemConfigService


@dataclass
class AiConfig:
    provider_type: str
    api_key: str
    base_url: str
    model: str
    timeout: int


class AiConfigError(Exception):
    pass


class AiService:
    @classmethod
    def load_config(cls) -> AiConfig:
        return AiConfig(
            provider_type=(SystemConfigService.get("AI_PROVIDER_TYPE", default="openai_compatible") or "openai_compatible").strip(),
            api_key=(SystemConfigService.get("AI_API_KEY", default="") or "").strip(),
            base_url=(SystemConfigService.get("AI_BASE_URL", default="") or "").strip(),
            model=(SystemConfigService.get("AI_MODEL", default="") or "").strip(),
            timeout=int(SystemConfigService.get("AI_TIMEOUT", default=60) or 60),
        )

    @classmethod
    def test_config(cls):
        config = cls.load_config()
        cls._validate_base_config(config)
        if config.provider_type in ("openai", "openai_compatible", "azure_openai"):
            return OpenAiCompatibleClient(config).test()
        raise AiConfigError(f"暂不支持的AI供应商类型：{config.provider_type}")

    @staticmethod
    def _validate_base_config(config: AiConfig):
        if not config.api_key:
            raise AiConfigError("AI的APIKey未配置")
        if not config.base_url:
            raise AiConfigError("AI接口地址未配置")
        if not config.model:
            raise AiConfigError("AI模型名称未配置")
        parsed_url = urlparse(config.base_url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            raise AiConfigError("AI接口地址格式不正确")


class OpenAiCompatibleClient:
    def __init__(self, config: AiConfig):
        self.config = config

    def test(self):
        response = requests.post(
            self._chat_completions_url(),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.config.model,
                "messages": [
                    {"role": "user", "content": "Reply with OK."},
                ],
                "temperature": 0,
                "max_tokens": 8,
                "stream": False,
            },
            timeout=max(1, min(self.config.timeout, 60)),
            proxies={"http": None, "https": None},
        )
        if response.status_code >= 400:
            raise AiConfigError(self._response_error_message(response))
        data = response.json()
        content = self._extract_content(data)
        return {
            "provider_type": self.config.provider_type,
            "model": self.config.model,
            "reply": content,
        }

    def _chat_completions_url(self):
        base_url = self.config.base_url.rstrip("/")
        if base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/chat/completions"

    @staticmethod
    def _extract_content(data):
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content[:120]
        return ""

    @staticmethod
    def _response_error_message(response):
        try:
            data = response.json()
        except ValueError:
            return f"AI接口返回异常，HTTP状态码：{response.status_code}"
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            message = error.get("message") or error.get("code")
        else:
            message = error
        if not message:
            message = f"AI接口返回异常，HTTP状态码：{response.status_code}"
        return str(message)[:300]

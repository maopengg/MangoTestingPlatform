# -*- coding: utf-8 -*-
from dataclasses import dataclass
from urllib.parse import urlparse

import requests
import json
import time
from requests.exceptions import ChunkedEncodingError, ConnectionError as RequestsConnectionError, ReadTimeout

from src.apps.system.service.system_config import SystemConfigService


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
            timeout=int(SystemConfigService.get("AI_TIMEOUT", default=600) or 600),
        )

    @classmethod
    def test_config(cls):
        config = cls.load_config()
        cls._validate_base_config(config)
        if config.provider_type in ("openai", "openai_compatible", "azure_openai"):
            return OpenAiCompatibleClient(config).test()
        raise AiConfigError(f"暂不支持的AI供应商类型：{config.provider_type}")

    @classmethod
    def chat(
        cls,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
    ) -> dict:
        config = cls.load_config()
        cls._validate_base_config(config)
        if config.provider_type in ("openai", "openai_compatible", "azure_openai"):
            return OpenAiCompatibleClient(config).chat(
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        raise AiConfigError(f"暂不支持的AI供应商类型：{config.provider_type}")

    @classmethod
    def json_chat(cls, messages: list[dict], temperature: float = 0, max_tokens: int | None = None) -> dict:
        return cls.chat(
            messages=messages,
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @classmethod
    def stream_json_chat(
        cls,
        messages: list[dict],
        temperature: float = 0,
        max_tokens: int | None = None,
        on_chunk=None,
    ) -> dict:
        config = cls.load_config()
        cls._validate_base_config(config)
        if config.provider_type in ("openai", "openai_compatible", "azure_openai"):
            return OpenAiCompatibleClient(config).collect_stream_chat(
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=max_tokens,
                on_chunk=on_chunk,
            )
        raise AiConfigError(f"暂不支持的AI供应商类型：{config.provider_type}")

    @classmethod
    def chat_with_tools(
        cls,
        messages: list[dict],
        tools: list[dict],
        tool_choice: str | dict | None = "auto",
        temperature: float = 0,
        max_tokens: int | None = None,
    ) -> dict:
        return cls.chat(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @classmethod
    def stream_chat(
        cls,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
    ):
        config = cls.load_config()
        cls._validate_base_config(config)
        if config.provider_type in ("openai", "openai_compatible", "azure_openai"):
            yield from OpenAiCompatibleClient(config).stream_chat(
                messages=messages,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return
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
        data = self.chat(
            messages=[{"role": "user", "content": "Reply with OK."}],
            temperature=0,
            max_tokens=8,
        )
        content = self._extract_content(data)
        return {
            "provider_type": self.config.provider_type,
            "model": self.config.model,
            "reply": content,
        }

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
    ) -> dict:
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if response_format:
            payload["response_format"] = response_format
        retried_without_response_format = False
        while True:
            try:
                response = requests.post(
                    self._chat_completions_url(),
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=max(1, self.config.timeout),
                    proxies={"http": None, "https": None},
                )
            except ReadTimeout as exc:
                raise AiConfigError(f"AI请求超时：{self.config.timeout}秒内未返回完整结果，请调大AI请求超时时间或减少本次选择的上下文资料") from exc
            except (ChunkedEncodingError, RequestsConnectionError) as exc:
                raise AiConfigError(f"AI连接异常：{exc}") from exc
            if response.status_code < 400:
                return response.json()
            error_message = self._response_error_message(response)
            if (
                response_format
                and not retried_without_response_format
                and self._is_response_format_unsupported(error_message)
            ):
                payload.pop("response_format", None)
                retried_without_response_format = True
                continue
            raise AiConfigError(error_message)

    def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
    ):
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if response_format:
            payload["response_format"] = response_format
        idle_timeout = max(1, self.config.timeout)
        last_chunk_time = time.monotonic()
        retried_without_response_format = False
        while True:
            try:
                with requests.post(
                    self._chat_completions_url(),
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=max(1, self.config.timeout),
                    proxies={"http": None, "https": None},
                    stream=True,
                ) as response:
                    if response.status_code >= 400:
                        error_message = self._response_error_message(response)
                        if (
                            response_format
                            and not retried_without_response_format
                            and self._is_response_format_unsupported(error_message)
                        ):
                            payload.pop("response_format", None)
                            retried_without_response_format = True
                            continue
                        raise AiConfigError(error_message)
                    for raw_line in response.iter_lines(decode_unicode=False):
                        if time.monotonic() - last_chunk_time > idle_timeout:
                            raise AiConfigError("AI流式响应长时间没有返回有效分片，请重试；如果反复出现，请减少本次选择的上下文资料或调大AI超时时间")
                        line = raw_line.decode("utf-8", errors="replace") if isinstance(raw_line, bytes) else raw_line
                        if not line:
                            continue
                        if line.startswith("data:"):
                            line = line[5:].strip()
                        if line == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line)
                            last_chunk_time = time.monotonic()
                            yield chunk
                        except ValueError:
                            continue
                return
            except (ChunkedEncodingError, RequestsConnectionError) as exc:
                message = str(exc)
                if "Response ended prematurely" in message:
                    raise AiConfigError("AI流式响应提前中断，请重试；如果反复出现，请减少本次选择的上下文资料") from exc
                raise AiConfigError(f"AI流式响应连接中断：{message[:200]}") from exc
            except ReadTimeout as exc:
                raise AiConfigError("AI流式响应超时，请重试；如果反复出现，请减少本次选择的上下文资料或调大AI超时时间") from exc

    def collect_stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | dict | None = None,
        response_format: dict | None = None,
        temperature: float = 0,
        max_tokens: int | None = None,
        on_chunk=None,
    ) -> dict:
        content_parts = []
        finish_reason = None
        for chunk in self.stream_chat(
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            choices = chunk.get("choices") or []
            if not choices:
                continue
            if on_chunk:
                on_chunk(chunk)
            choice = choices[0]
            finish_reason = choice.get("finish_reason") or finish_reason
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if isinstance(content, str):
                content_parts.append(content)
        return {
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "message": {
                        "role": "assistant",
                        "content": "".join(content_parts),
                    },
                }
            ]
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

    @staticmethod
    def _is_response_format_unsupported(message: str) -> bool:
        normalized = (message or "").lower()
        return (
            "response_format" in normalized
            and (
                "not supported" in normalized
                or "unsupported" in normalized
                or "not valid" in normalized
                or "invalid" in normalized
                or "不支持" in normalized
            )
        )

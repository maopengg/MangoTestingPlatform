# -*- coding: utf-8 -*-
import json
from typing import Any

from mangoautomation.uidrives import AsyncWebRuntime, BaseData
from playwright._impl._errors import TargetClosedError

from src.services.runtime.session import AutomationSessionManager, WebContextRegistry
from src.tools.log_collector import log
from src.tools.send_global_msg import send_global_msg


class UiAuthCacheApplier:
    def __init__(self, base_data: BaseData, web_runtime: AsyncWebRuntime, auth_cache: Any):
        self.base_data = base_data
        self.web_runtime = web_runtime
        self.auth_cache = auth_cache

    async def apply(self):
        if not self.auth_cache:
            return
        if not self.base_data.context or not self.base_data.page:
            return
        try:
            await self._apply()
        except TargetClosedError as error:
            log.warning(f'UI授权缓存注入时浏览器Page已关闭，正在重建后重试，失败详情：{error}')
            await self._reopen_web_page()
            await self._apply()

    async def _apply(self):
        auth_cache = self.auth_cache
        if auth_cache.cookies:
            await self.base_data.context.add_cookies([self._normalize_cookie(cookie) for cookie in auth_cache.cookies])
        if auth_cache.headers:
            await self._install_header_init_script(auth_cache.headers)
        await self._install_storage_init_script('localStorage', auth_cache.local_storage)
        await self._install_storage_init_script('sessionStorage', auth_cache.session_storage)
        send_global_msg(
            f'UI-授权缓存注入完成，Cookie:{len(auth_cache.cookies or [])}，'
            f'localStorage:{len(auth_cache.local_storage or [])}，'
            f'sessionStorage:{len(auth_cache.session_storage or [])}，'
            f'Header:{len(auth_cache.headers or {})}'
        )

    async def _reopen_web_page(self):
        WebContextRegistry.unregister_base(self.base_data, "auth-cache-reopen")
        try:
            if self.base_data.page and not self.base_data.page.is_closed():
                await self.base_data.page.close()
        except Exception as error:
            log.warning(f'重建浏览器Page前关闭旧Page失败，类型：{type(error)}，失败详情：{error}')
        try:
            if self.base_data.context:
                await self.base_data.context.close()
        except Exception as error:
            log.warning(f'重建浏览器Page前关闭旧Context失败，类型：{type(error)}，失败详情：{error}')
        self.base_data.context = None
        self.base_data.page = None
        await AutomationSessionManager.ensure_web_page(
            self.base_data,
            self.web_runtime,
            owner_type=getattr(self.base_data, "_web_owner_type", "auth_cache"),
            owner_id=getattr(self.base_data, "_web_owner_id", None),
            purpose="auth-cache-reopen",
        )

    async def _install_header_init_script(self, headers: dict):
        header_rows = {
            str(key): str(value)
            for key, value in (headers or {}).items()
            if key is not None and value is not None
        }
        if not header_rows:
            return
        await self.base_data.context.add_init_script(
            f"""(() => {{
                const authHeaders = {json.dumps(header_rows, ensure_ascii=False)};
                const shouldAttach = (url) => {{
                    try {{
                        return new URL(url, window.location.href).origin === window.location.origin;
                    }} catch (error) {{
                        return false;
                    }}
                }};

                const oldFetch = window.fetch;
                window.fetch = function(input, init = {{}}) {{
                    const url = typeof input === 'string' ? input : input && input.url;
                    if (shouldAttach(url || window.location.href)) {{
                        const headers = new Headers(init.headers || (input && input.headers) || {{}});
                        Object.entries(authHeaders).forEach(([key, value]) => headers.set(key, value));
                        init = {{ ...init, headers }};
                    }}
                    return oldFetch.call(this, input, init);
                }};

                const oldOpen = XMLHttpRequest.prototype.open;
                const oldSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
                XMLHttpRequest.prototype.open = function(method, url) {{
                    this.__mangoShouldAttachAuthHeaders = shouldAttach(url || window.location.href);
                    return oldOpen.apply(this, arguments);
                }};
                XMLHttpRequest.prototype.setRequestHeader = function(key, value) {{
                    this.__mangoHeaderKeys = this.__mangoHeaderKeys || {{}};
                    this.__mangoHeaderKeys[String(key).toLowerCase()] = true;
                    return oldSetRequestHeader.apply(this, arguments);
                }};
                const oldSend = XMLHttpRequest.prototype.send;
                XMLHttpRequest.prototype.send = function() {{
                    if (this.__mangoShouldAttachAuthHeaders) {{
                        this.__mangoHeaderKeys = this.__mangoHeaderKeys || {{}};
                        Object.entries(authHeaders).forEach(([key, value]) => {{
                            if (!this.__mangoHeaderKeys[String(key).toLowerCase()]) {{
                                oldSetRequestHeader.call(this, key, value);
                            }}
                        }});
                    }}
                    return oldSend.apply(this, arguments);
                }};
            }})()""",
        )

    async def _install_storage_init_script(self, storage_name: str, items: list[dict]):
        if not items:
            return
        rows = [
            {
                'origin': plain_item.get('origin'),
                'key': plain_item.get('key'),
                'value': str(plain_item.get('value', '')),
            }
            for plain_item in [self._to_plain_data(item) for item in items]
            if plain_item.get('origin') and plain_item.get('key') is not None
        ]
        if not rows:
            return
        await self.base_data.context.add_init_script(
            f"""(() => {{
                const storageName = {json.dumps(storage_name, ensure_ascii=False)};
                const rows = {json.dumps(rows, ensure_ascii=False)};
                const matchedRows = rows.filter((item) => item.origin === window.location.origin);
                if (!matchedRows.length) return;
                const storage = window[storageName];
                matchedRows.forEach((item) => storage.setItem(item.key, item.value));
            }})()""",
        )

    @staticmethod
    def _to_plain_data(value):
        if hasattr(value, 'model_dump'):
            return value.model_dump(mode='json')
        if isinstance(value, dict):
            return value
        return value

    @classmethod
    def _normalize_cookie(cls, cookie):
        cookie_data = cls._to_plain_data(cookie)
        if not isinstance(cookie_data, dict):
            return cookie_data
        cookie_data = {
            key: value
            for key, value in cookie_data.items()
            if value is not None
        }
        expires = cookie_data.get('expires')
        if expires in [None, '']:
            cookie_data.pop('expires', None)
        elif not isinstance(expires, (int, float)):
            try:
                cookie_data['expires'] = float(expires)
            except (TypeError, ValueError):
                cookie_data.pop('expires', None)
        return cookie_data

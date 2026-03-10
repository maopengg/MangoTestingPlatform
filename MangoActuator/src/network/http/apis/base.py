# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: API 基类 —— 持有客户端与鉴权信息，子类统一通过 self 访问
# @Time   : 2024-09-12
# @Author : 毛鹏
try:
    from mangoui.widgets.network import BaseHttpClient
except ImportError:
    import httpx

    class ApiError(Exception):
        pass


    class BaseHttpClient:

        def __init__(
                self,
                base_url: str = "",
                headers: dict | None = None,
                timeout: int = 15,
                logger=None
        ):

            self.base_url = base_url
            self.log = logger

            self.client = httpx.AsyncClient(
                base_url=base_url,
                headers=headers or {},
                timeout=httpx.Timeout(timeout)
            )

        def _log(self, msg):

            if self.log:
                self.log.debug(msg)

        async def request(
                self,
                method: str,
                url: str,
                *,
                params: dict | None = None,
                data=None,
                json=None,
                headers: dict | None = None,
                timeout: int | None = None,
                return_json: bool = True,
                **kwargs
        ):

            self._log(f"[HTTP] {method} {url} params={params} json={json}")

            try:

                r = await self.client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                    json=json,
                    headers=headers,
                    timeout=timeout,
                    **kwargs
                )

                self._log(f"[HTTP] response {r.status_code} {url}")

                r.raise_for_status()

                if return_json:
                    return r.json()

                return r.text

            except httpx.HTTPStatusError as e:

                self._log(
                    f"[HTTP ERROR] {e.response.status_code} {url} {e.response.text}"
                )

                raise ApiError(e.response.text)

            except Exception as e:

                self._log(f"[HTTP EXCEPTION] {url} {str(e)}")

                raise

        async def get(self, url, **kwargs):
            return await self.request("GET", url, **kwargs)

        async def post(self, url, **kwargs):
            return await self.request("POST", url, **kwargs)

        async def put(self, url, **kwargs):
            return await self.request("PUT", url, **kwargs)

        async def delete(self, url, **kwargs):
            return await self.request("DELETE", url, **kwargs)

        async def close(self):
            await self.client.aclose()

        async def raw_request(
                self,
                method: str,
                url: str,
                *,
                params: dict | None = None,
                data=None,
                json=None,
                headers: dict | None = None,
                timeout: int | None = None,
                return_json: bool = True,
                return_bytes: bool = False,
                **kwargs
        ):
            """不依赖 base_url 的原始请求，url 必须是完整地址（含 http://）"""
            self._log(f"[HTTP RAW] {method} {url} params={params} json={json}")
            try:
                async with httpx.AsyncClient(
                        timeout=httpx.Timeout(timeout or self.client.timeout.read or 15)
                ) as raw:
                    r = await raw.request(
                        method=method,
                        url=url,
                        params=params,
                        data=data,
                        json=json,
                        headers=headers or {},
                        **kwargs
                    )
                self._log(f"[HTTP RAW] response {r.status_code} {url}")
                r.raise_for_status()
                if return_bytes:
                    return r.content, r.status_code
                if return_json:
                    return r.json()
                return r.text
            except httpx.HTTPStatusError as e:
                self._log(f"[HTTP RAW ERROR] {e.response.status_code} {url} {e.response.text}")
                raise ApiError(e.response.text)
            except Exception as e:
                self._log(f"[HTTP RAW EXCEPTION] {url} {str(e)}")
                raise


class AuthManager:
    """仅用于类型提示，实际单例在 http/__init__.py 中定义"""
    def get_headers(self) -> dict: ...


class BaseApi:
    """所有业务 API 的基类

    self.client  — 带 base_url + token 的全局客户端，所有请求统一走这里
    self.auth    — 鉴权管理器，通过 self._headers() 注入请求头
    """

    def __init__(self, client: BaseHttpClient, auth):
        self.client = client
        self.auth = auth

    def _headers(self, extra: dict | None = None) -> dict:
        """获取鉴权头，可追加额外自定义头"""
        headers = self.auth.get_headers()
        if extra:
            headers.update(extra)
        return headers

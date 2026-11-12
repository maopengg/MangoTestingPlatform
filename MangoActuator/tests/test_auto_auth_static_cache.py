import asyncio
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from playwright.async_api import async_playwright

from mangoautomation.uidrives.web.async_web._new_browser import AsyncWebNewBrowser
from mangoautomation.uidrives.web.static_cache import StaticResourceCache
from src.services.ui.test_page_steps import TestPageSteps


CHROME = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')


@unittest.skipUnless(CHROME.is_file(), '需要本机 Chrome 执行浏览器集成回归')
class AutoAuthStaticCacheIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_slow_script_does_not_break_auth_cache_extraction(self):
        async def serve(reader, writer):
            try:
                request = await reader.readuntil(b'\r\n\r\n')
                script = request.split(b' ')[1] == b'/sdk.js'
                if script:
                    await asyncio.sleep(0.3)
                    body = b'window.sdkLoaded = true;'
                    extra = b'Content-Type: text/javascript\r\n'
                else:
                    body = b'<script>localStorage.setItem("sample", "saved");</script><script async src="/sdk.js"></script>'
                    extra = b'Content-Type: text/html\r\nSet-Cookie: sample_auth=synthetic; Path=/; HttpOnly\r\n'
                writer.write(b'HTTP/1.1 200 OK\r\nConnection: close\r\n' + extra +
                             f'Content-Length: {len(body)}\r\n\r\n'.encode() + body)
                await writer.drain()
            except (ConnectionError, asyncio.IncompleteReadError):
                pass
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except ConnectionError:
                    pass

        server = await asyncio.start_server(serve, '127.0.0.1', 0)
        origin = f'http://127.0.0.1:{server.sockets[0].getsockname()[1]}'
        try:
            with tempfile.TemporaryDirectory() as cache_dir, patch.object(StaticResourceCache, 'FETCH_TIMEOUT_MS', 100):
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(executable_path=str(CHROME), headless=True)
                    try:
                        context = await browser.new_context()
                        context.set_default_timeout(50)
                        page = await context.new_page()
                        owner = object.__new__(AsyncWebNewBrowser)
                        owner.static_cache = StaticResourceCache(cache_dir, Mock())
                        owner.is_header_intercept = False
                        routed = asyncio.Event()

                        async def route_request(route, request):
                            await owner.route_request(route, request)
                            if request.resource_type == 'script':
                                routed.set()

                        await page.route('**/*', route_request)
                        await page.goto(origin, wait_until='domcontentloaded', timeout=5000)
                        await asyncio.wait_for(routed.wait(), 5)
                        data = SimpleNamespace(cookie_domains=[], origin=origin, local_storage_keys=['sample'],
                                               session_storage_keys=[], headers={})
                        result = await TestPageSteps._collect_auth_cache(
                            object.__new__(TestPageSteps), data, SimpleNamespace(page=page, context=context))
                        self.assertTrue(any(row['name'] == 'sample_auth' for row in result['cookies']))
                        self.assertTrue(result['local_storage'])
                        self.assertTrue(owner.static_cache.log.debug.called)
                    finally:
                        await browser.close()
        finally:
            server.close()
            await server.wait_closed()

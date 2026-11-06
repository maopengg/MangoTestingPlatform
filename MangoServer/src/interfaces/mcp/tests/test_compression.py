import gzip
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from src.interfaces.mcp.server import mcp_router_asgi_app


class McpCompressionTests(SimpleTestCase):
    payload = {"jsonrpc": "2.0", "id": 1, "result": {"text": "工具响应内容" * 1000}}

    def endpoint(self, domain=None):
        async def respond(request):
            if request.url.path.endswith("/small"):
                return JSONResponse({"ok": True})
            if request.url.path.endswith("/encoded"):
                return Response(b"already-encoded", headers={"Content-Encoding": "gzip"})
            return JSONResponse(self.payload)

        app = Starlette(routes=[Route("/{path:path}", respond)])
        app.fastmcp_server = object()
        return app

    async def test_large_json_is_compressed_on_root_and_domain_endpoints(self):
        with patch("src.interfaces.mcp.server.mcp_asgi_app", side_effect=self.endpoint):
            app = mcp_router_asgi_app()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://mcp.example.com") as client:
            for path in ("/", "/api/", "/ui/", "/data-factory/"):
                with self.subTest(path=path):
                    async with client.stream("GET", path, headers={"Accept-Encoding": "gzip"}) as response:
                        raw = b"".join([chunk async for chunk in response.aiter_raw()])
                        self.assertEqual(response.headers["Content-Encoding"], "gzip")
                        self.assertIn("Accept-Encoding", response.headers["Vary"])
                        self.assertEqual(len(raw), int(response.headers["Content-Length"]))
                        self.assertEqual(gzip.decompress(raw), JSONResponse(self.payload).body)
                        self.assertLess(len(raw), len(gzip.decompress(raw)))

    async def test_http_client_automatically_decodes_json(self):
        with patch("src.interfaces.mcp.server.mcp_asgi_app", side_effect=self.endpoint):
            app = mcp_router_asgi_app()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://mcp.example.com") as client:
            response = await client.get("/", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(response.json(), self.payload)

    async def test_clients_without_gzip_support_get_original_json(self):
        with patch("src.interfaces.mcp.server.mcp_asgi_app", side_effect=self.endpoint):
            app = mcp_router_asgi_app()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://mcp.example.com") as client:
            for encoding in ("", "identity", "br"):
                with self.subTest(encoding=encoding):
                    response = await client.get("/", headers={"Accept-Encoding": encoding})
                    self.assertNotIn("Content-Encoding", response.headers)
                    self.assertEqual(response.json(), self.payload)

    async def test_small_response_is_not_compressed(self):
        with patch("src.interfaces.mcp.server.mcp_asgi_app", side_effect=self.endpoint):
            app = mcp_router_asgi_app()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://mcp.example.com") as client:
            response = await client.get("/small", headers={"Accept-Encoding": "gzip"})
        self.assertNotIn("Content-Encoding", response.headers)
        self.assertEqual(response.json(), {"ok": True})

    async def test_already_encoded_response_is_not_compressed_again(self):
        with patch("src.interfaces.mcp.server.mcp_asgi_app", side_effect=self.endpoint):
            app = mcp_router_asgi_app()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="https://mcp.example.com") as client:
            async with client.stream("GET", "/encoded", headers={"Accept-Encoding": "gzip"}) as response:
                raw = b"".join([chunk async for chunk in response.aiter_raw()])
        self.assertEqual(raw, b"already-encoded")

    async def test_sse_chunks_are_sent_immediately_without_compression(self):
        messages = []
        chunks = [b"data: " + b"x" * 2048 + b"\n\n", b"data: done\n\n"]

        class EventEndpoint:
            fastmcp_server = object()

            async def __call__(self, scope, receive, send):
                await send({"type": "http.response.start", "status": 200,
                            "headers": [(b"content-type", b"text/event-stream; charset=utf-8")]})
                for index, chunk in enumerate(chunks):
                    await send({"type": "http.response.body", "body": chunk, "more_body": index == 0})
                    # 第一帧必须在下一帧产生前发出，不能缓存到流结束。
                    self_test.assertEqual(messages[-1]["body"], chunk)

        self_test = self
        with patch("src.interfaces.mcp.server.mcp_asgi_app", side_effect=lambda domain=None: EventEndpoint()):
            app = mcp_router_asgi_app()

        async def send(message):
            messages.append(message)

        async def receive():
            return {"type": "http.request", "body": b""}

        await app({"type": "http", "asgi": {"version": "3.0"}, "method": "GET", "path": "/",
                   "root_path": "", "query_string": b"", "headers": [(b"accept-encoding", b"gzip")]},
                  receive, send)
        self.assertNotIn(b"content-encoding", dict(messages[0]["headers"]))
        self.assertEqual([message["body"] for message in messages[1:]], chunks)

    async def test_real_mcp_client_parses_compressed_tool_result(self):
        def endpoint(domain=None):
            server = FastMCP("compression-test")

            @server.tool()
            def large_result() -> dict:
                return self.payload

            app = server.http_app(path="/", json_response=True)
            app.fastmcp_server = server
            return app

        with patch("src.interfaces.mcp.server.mcp_asgi_app", side_effect=endpoint):
            app = mcp_router_asgi_app()
        encodings = []

        async def record_response(response):
            encodings.append(response.headers.get("Content-Encoding"))

        def client_factory(**kwargs):
            kwargs.pop("follow_redirects", None)
            return httpx.AsyncClient(transport=httpx.ASGITransport(app), follow_redirects=True,
                                     event_hooks={"response": [record_response]}, **kwargs)

        transport = StreamableHttpTransport("https://mcp.example.com/api/",
                                           httpx_client_factory=client_factory)
        async with app.router.lifespan_context(app):
            async with Client(transport) as client:
                tools = await client.list_tools()
                result = await client.call_tool("large_result", {})
        self.assertEqual([tool.name for tool in tools], ["large_result"])
        self.assertEqual(result.data, self.payload)
        self.assertIn("gzip", encodings)

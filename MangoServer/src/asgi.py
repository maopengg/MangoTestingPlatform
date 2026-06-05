"""
ASGI settings for src project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os
import django
import asyncio
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')

django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from . import routing
from src.services.mcp_server.app import mcp_asgi_app

django_channels_application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns))
})

mcp_application = mcp_asgi_app()


class LifespanManagedApp:
    def __init__(self, app):
        self.app = app
        self.receive_queue = None
        self.send_queue = None
        self.lifespan_task = None
        self.started = False
        self.lock = asyncio.Lock()

    async def ensure_started(self, from_lifespan=False):
        if self.started or not hasattr(self.app, 'router'):
            return
        async with self.lock:
            if self.started:
                return
            self.receive_queue = asyncio.Queue()
            self.send_queue = asyncio.Queue()

            async def receive():
                return await self.receive_queue.get()

            async def send(message):
                await self.send_queue.put(message)

            self.lifespan_task = asyncio.create_task(self.app(
                {'type': 'lifespan', 'asgi': {'version': '3.0', 'spec_version': '2.0'}},
                receive,
                send,
            ))
            await self.receive_queue.put({'type': 'lifespan.startup'})
            message = await self.send_queue.get()
            if message['type'] == 'lifespan.startup.failed':
                await self.lifespan_task
                raise RuntimeError(message.get('message') or 'MCP lifespan startup failed')
            self.started = True

    async def stop(self):
        if not self.started or self.receive_queue is None or self.send_queue is None:
            return
        await self.receive_queue.put({'type': 'lifespan.shutdown'})
        message = await self.send_queue.get()
        if message['type'] == 'lifespan.shutdown.failed':
            raise RuntimeError(message.get('message') or 'MCP lifespan shutdown failed')
        if self.lifespan_task is not None:
            await self.lifespan_task
        self.receive_queue = None
        self.send_queue = None
        self.lifespan_task = None
        self.started = False

    async def __call__(self, scope, receive, send):
        if scope.get('type') == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    try:
                        await self.ensure_started(from_lifespan=True)
                    except BaseException as exc:
                        await send({'type': 'lifespan.startup.failed', 'message': str(exc)})
                        raise
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    await self.stop()
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
            return
        await self.ensure_started()
        return await self.app(scope, receive, send)


mcp_lifespan_managed_application = LifespanManagedApp(mcp_application)

MCP_PATH = '/mcp'


def _mount_mcp_scope(scope, mount_path):
    scope = dict(scope)
    path = scope.get('path') or ''
    scope['path'] = path[len(mount_path):] or '/'
    scope['root_path'] = scope.get('root_path', '') + mount_path
    return scope


async def application(scope, receive, send):
    if scope.get('type') == 'lifespan':
        return await mcp_lifespan_managed_application(scope, receive, send)
    path = scope.get('path') or ''
    if path == MCP_PATH or path.startswith(f'{MCP_PATH}/'):
        scope = _mount_mcp_scope(scope, MCP_PATH)
        return await mcp_lifespan_managed_application(scope, receive, send)
    return await django_channels_application(scope, receive, send)

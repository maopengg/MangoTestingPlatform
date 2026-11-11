import os

import django
from django.apps import apps

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
if not apps.ready:
    django.setup()

from src.interfaces.mcp.server import mcp_router_asgi_app

mcp_application = mcp_router_asgi_app()

MCP_PATH = '/mcp'


def _mount_mcp_scope(scope, mount_path):
    scope = dict(scope)
    path = scope.get('path') or ''
    scope['path'] = path[len(mount_path):] or '/'
    scope['root_path'] = scope.get('root_path', '') + mount_path
    return scope


async def application(scope, receive, send):
    if scope.get('type') == 'lifespan':
        return await mcp_application(scope, receive, send)
    path = scope.get('path') or ''
    if scope.get('type') == 'http' and path == '/health/ready':
        from src.apps.system.services.runtime_center.mcp_execution import McpExecutionLifecycle
        ready = McpExecutionLifecycle.snapshot()['draining_at'] is None
        await send({'type': 'http.response.start', 'status': 200 if ready else 503,
                    'headers': [(b'content-type', b'text/plain')]})
        return await send({'type': 'http.response.body', 'body': b'ready' if ready else b'draining'})
    if path == MCP_PATH or path.startswith(f'{MCP_PATH}/'):
        scope = _mount_mcp_scope(scope, MCP_PATH)
    return await mcp_application(scope, receive, send)

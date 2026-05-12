"""
ASGI settings for src project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')

django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from . import routing
from src.mcp_server.app import mcp_asgi_app

django_channels_application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns))
})

mcp_application = mcp_asgi_app()


async def application(scope, receive, send):
    if scope.get('type') == 'lifespan':
        return await mcp_application(scope, receive, send)
    path = scope.get('path') or ''
    if path == '/mcp':
        scope = dict(scope)
        scope['path'] = '/'
        scope['root_path'] = scope.get('root_path', '') + '/mcp'
        return await mcp_application(scope, receive, send)
    if path.startswith('/mcp/'):
        scope = dict(scope)
        scope['path'] = path[len('/mcp'):] or '/'
        scope['root_path'] = scope.get('root_path', '') + '/mcp'
        return await mcp_application(scope, receive, send)
    return await django_channels_application(scope, receive, send)

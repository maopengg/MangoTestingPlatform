"""
ASGI settings for PyAutoTest project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""
# 处理路由

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from . import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PyAutoTest.settings.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns))
})

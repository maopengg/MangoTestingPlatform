"""
ASGI settings for src project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""
import os
import django
from django.core.asgi import get_asgi_application

# 必须在最前面设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')

# 初始化 Django
django.setup()

# 现在导入其他模块
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from . import routing

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns))
})

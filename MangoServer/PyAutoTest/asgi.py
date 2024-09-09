"""
ASGI settings for PyAutoTest project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""
# 处理路由

import os

import sys
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.core.management import call_command

from . import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PyAutoTest.settings')

# 添加项目路径到系统路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


# 检查并执行迁移
def migrate():
    from django import setup
    setup()
    call_command('migrate')


migrate()

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns))
})

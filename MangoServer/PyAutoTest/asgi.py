"""
ASGI config for PyAutoTest project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""
# 处理路由

import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

#
from PyAutoTest.auto_test.auto_system.service.scheduled_tasks.tasks import create_jobs
from PyAutoTest.auto_test.auto_system.service.socket_link.interface_reflection import ServerInterfaceReflection
from PyAutoTest.auto_test.auto_system.service.socket_link.socket_user_redis import SocketUserRedis
from script.nuw_logs import __nuw_dir
from . import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PyAutoTest.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns))
})
__nuw_dir()

# django启动完成后执行
django.setup()

# 定时任务
create_jobs()
#

SocketUserRedis().all_delete()
ServerInterfaceReflection().while_get_data()

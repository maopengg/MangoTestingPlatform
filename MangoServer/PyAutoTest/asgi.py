"""
ASGI config for PyAutoTest project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/asgi/
"""

import os

import django
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from PyAutoTest.auto_test.auto_system.scheduled_tasks.tasks import create_jobs
from . import routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PyAutoTest.settings')
django.setup()

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns))
})
create_jobs()

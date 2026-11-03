"""DjangoAutoTest URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from asgiref.sync import sync_to_async
from django.conf import settings
from django.conf.urls.static import static
from django.db import connection
from django.http import JsonResponse
from django.urls import path, include, re_path

from src.apps.auto_api.api.views.api_mock import ApiMockRuntimeView
from src.apps.task_center.api.views.actuator_tasks import ActuatorTaskViews
from src.apps.user.api.views.user import LoginViews, MenuViews, UserViews
from src.settings import OBJECT_STORAGE_ENABLED


def _check_database_connection():
    # 检查数据库连接是否可用
    with connection.cursor() as cursor:
        cursor.execute('SELECT 1')
        cursor.fetchone()


async def management_health(request):
    try:
        await sync_to_async(_check_database_connection, thread_sensitive=True)()
    except Exception:
        return JsonResponse({"status": "error", "database": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    re_path(
        r"^api/mock/(?P<mock_key>[a-z0-9]+(?:-[a-z0-9]+)*)(?P<remaining_path>/.*)?$",
        ApiMockRuntimeView.as_view(),
    ),
    path("management/health", management_health),
    path("api/login", LoginViews.as_view({'post': 'login'})),
    path("api/cli/auth/authorize", UserViews.as_view({'post': 'cli_authorize'})),
    path("api/cli/auth/token", LoginViews.as_view({'post': 'cli_token'})),
    path("api/cli/auth/version", LoginViews.as_view({'get': 'cli_version'})),
    path("api/register", LoginViews.as_view({'post': 'register'})),
    path("api/reset-password", LoginViews.as_view({'post': 'reset_password_by_email'})),
    path("api/menu", MenuViews.as_view({'post': 'menu'})),
    path("api/test", LoginViews.as_view({'get': 'test'})),
    path("api/test2", LoginViews.as_view({'get': 'test2'})),
    path("api/download", LoginViews.as_view({'get': 'get_download'})),
    path("api/actuator/tasks/pull", ActuatorTaskViews.as_view({'post': 'pull'})),
    path("api/actuator/tasks/pytest-git-credentials", ActuatorTaskViews.as_view({'post': 'pytest_git_credentials'})),
    path("api/actuator/tasks/ack", ActuatorTaskViews.as_view({'post': 'ack'})),
    path("api/actuator/tasks/claim", ActuatorTaskViews.as_view({'post': 'claim'})),
    path("api/actuator/tasks/draining", ActuatorTaskViews.as_view({'post': 'draining'})),
    path("api/actuator/tasks/<int:task_id>/running", ActuatorTaskViews.as_view({'post': 'running'})),
    path("api/actuator/tasks/<int:task_id>/heartbeat", ActuatorTaskViews.as_view({'post': 'heartbeat'})),
    path("api/actuator/tasks/<int:task_id>/progress", ActuatorTaskViews.as_view({'post': 'progress'})),
    path("api/actuator/tasks/<int:task_id>/result", ActuatorTaskViews.as_view({'post': 'result'})),
    path("api/actuator/tasks/system-errors", ActuatorTaskViews.as_view({'post': 'report_system_error'})),
    path('api/system/', include("src.apps.system.api.urls")),
    path('api/data-factory/', include("src.apps.data_factory.api.urls")),
    path('api/api/', include("src.apps.auto_api.api.urls")),
    path('api/ui/', include("src.apps.auto_ui.api.urls")),
    path('api/perf/', include("src.apps.perf.api.urls")),
    path('api/user/', include("src.apps.user.api.urls")),
    path('api/pytest/', include("src.apps.auto_pytest.api.urls")),
    path('api/monitoring/', include("src.apps.monitoring.api.urls")),
    path('api/functional-test/', include("src.apps.functional_test.api.urls")),
    path('api/gray/', include("src.apps.gray_config.api.urls")),
    path('api/evaluation/', include("src.apps.evaluation.api.urls")),
]

try:
    import coreapi  # noqa: F401
    import coreschema  # noqa: F401
    from rest_framework.documentation import include_docs_urls
except ImportError:
    pass
else:
    urlpatterns.insert(0, path('api/docs', include_docs_urls(title='src', authentication_classes=[])))

if not OBJECT_STORAGE_ENABLED:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

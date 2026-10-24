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
from src.apps.system.services.runtime_center.diagnostics import DiagnosticsService
from src.apps.system.services.runtime_center.heartbeat import ServiceHeartbeatService
from src.apps.system.services.runtime_center.overview import RuntimeOverviewService
from src.apps.system.services.runtime_center.queue_stats import QueueStatsService
from src.apps.system.services.runtime_center.recent_errors import RecentErrorsService
from src.apps.task_center.api.views.actuator_tasks import ActuatorTaskViews
from src.apps.user.api.views.user import LoginViews, MenuViews, UserViews
from src.common.responses.response_msg import RESPONSE_MSG_0001
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


def _management_success(data, total_size=None):
    payload = {
        "code": RESPONSE_MSG_0001[0],
        "msg": RESPONSE_MSG_0001[1],
        "data": data,
    }
    if total_size is not None:
        payload['totalSize'] = total_size
    return JsonResponse(payload)


async def management_runtime_overview(request):
    return _management_success(await RuntimeOverviewService.aget_overview())


async def management_runtime_services(request):
    await RuntimeOverviewService.areport_core_api()
    return _management_success(await ServiceHeartbeatService.alist_service_groups(RuntimeOverviewService.SERVICE_NAMES))


async def management_runtime_queues(request):
    return _management_success(await QueueStatsService.aget_stats())


async def management_runtime_diagnostics(request):
    return _management_success(await DiagnosticsService.alist_diagnostics())


async def management_runtime_recent_errors(request):
    try:
        page = max(int(request.GET.get('page') or 1), 1)
        page_size = int(request.GET.get('pageSize') or request.GET.get('limit') or RecentErrorsService.DEFAULT_LIMIT)
    except (TypeError, ValueError):
        page = 1
        page_size = RecentErrorsService.DEFAULT_LIMIT
    page_size = min(max(page_size, 1), 100)
    rows, total = await RecentErrorsService.apaginate_errors(page, page_size)
    return _management_success(rows, total)


urlpatterns = [
    re_path(
        r"^api/mock/(?P<mock_key>[a-z0-9]+(?:-[a-z0-9]+)*)(?P<remaining_path>/.*)?$",
        ApiMockRuntimeView.as_view(),
    ),
    path("management/health", management_health),
    path("management/runtime/overview", management_runtime_overview),
    path("management/runtime/services", management_runtime_services),
    path("management/runtime/queues", management_runtime_queues),
    path("management/runtime/diagnostics", management_runtime_diagnostics),
    path("management/runtime/recent-errors", management_runtime_recent_errors),
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
    path('api/ai/', include("src.apps.ai.api.urls")),
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

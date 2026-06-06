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
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

from src.apps.auto_user.views.user import LoginViews
from src.settings import IS_MINIO

urlpatterns = [
    path("api/login", LoginViews.as_view({'post': 'login'})),
    path("api/register", LoginViews.as_view({'post': 'register'})),
    path("api/menu", LoginViews.as_view({'post': 'menu'})),
    path("api/test", LoginViews.as_view({'get': 'test'})),
    path("api/download", LoginViews.as_view({'get': 'get_download'})),
    path('api/system/', include("src.apps.auto_system.urls")),
    path('api/data-factory/', include("src.apps.auto_data_factory.urls")),
    path('api/api/', include("src.apps.auto_api.urls")),
    path('api/ui/', include("src.apps.auto_ui.urls")),
    path('api/perf/', include("src.apps.auto_perf.urls")),
    path('api/user/', include("src.apps.auto_user.urls")),
    path('api/pytest/', include("src.apps.auto_pytest.urls")),
    path('api/monitoring/', include("src.apps.monitoring.urls")),
]

try:
    import coreapi  # noqa: F401
    import coreschema  # noqa: F401
except ImportError:
    pass
else:
    from rest_framework.documentation import include_docs_urls

    urlpatterns.insert(0, path('api/docs', include_docs_urls(title='src', authentication_classes=[])))

if not IS_MINIO:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

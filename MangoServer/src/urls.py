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
from django.contrib import admin
from django.urls import path, include
from rest_framework.documentation import include_docs_urls

from src.auto_test.auto_user.views.user import LoginViews

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('docs', include_docs_urls(title='src', authentication_classes=[])),
                  #
                  path("login", LoginViews.as_view({'post': 'login'})),  # 登录
                  path("register", LoginViews.as_view({'post': 'register'})),  # 登录
                  path("menu", LoginViews.as_view({'post': 'menu'})),
                  path("test", LoginViews.as_view({'get': 'test'})),
                  #
                  path('system/', include("src.auto_test.auto_system.urls")),
                  path('api/', include("src.auto_test.auto_api.urls")),
                  path('ui/', include("src.auto_test.auto_ui.urls")),
                  path('perf/', include("src.auto_test.auto_perf.urls")),
                  path('user/', include("src.auto_test.auto_user.urls")),
                  path('pytest/', include("src.auto_test.auto_pytest.urls")),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

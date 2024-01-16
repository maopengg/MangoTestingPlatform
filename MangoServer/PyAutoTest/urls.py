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
from django.contrib import admin
from django.urls import path, include
from rest_framework.documentation import include_docs_urls

from PyAutoTest.auto_test.auto_user.views.user import LoginViews

urlpatterns = [
    path('admin/', admin.site.urls),
    path('docs/', include_docs_urls(title='PyAutoTest', authentication_classes=[])),
    #
    path("login", LoginViews.as_view({'post': 'login'})),  # 登录
    # path("test1", LoginViews.as_view({'post': 'test1'})),  # 登录
    # path("test2", LoginViews.as_view({'post': 'test2'})),  # 登录
    # path("test3", LoginViews.as_view({'post': 'test3'})),  # 登录
    # path("login1", LoginViews.as_view({'get': 'login1'})),  # 登录
    path("menu/", LoginViews.as_view({'get': 'menu'})),
    #
    path('system/', include("PyAutoTest.auto_test.auto_system.urls")),
    path('api/', include("PyAutoTest.auto_test.auto_api.urls")),
    path('ui/', include("PyAutoTest.auto_test.auto_ui.urls")),
    path('data_producer/', include("PyAutoTest.auto_test.auto_perf.urls")),
    path('user/', include("PyAutoTest.auto_test.auto_user.urls")),
]

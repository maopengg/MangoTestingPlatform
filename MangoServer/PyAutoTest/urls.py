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
    path('docs/', include_docs_urls(title='PyAutoTest')),
    #
    path("login", LoginViews.as_view({'post': 'login'})),  # 登录
    path("menu/", LoginViews.as_view({'get': 'menu'})),
    #
    path('system/', include("PyAutoTest.auto_test.auto_system.urls")),
    path('api/', include("PyAutoTest.auto_test.auto_api.urls")),
    path('ui/', include("PyAutoTest.auto_test.auto_ui.urls")),
    path('perf/', include("PyAutoTest.auto_test.auto_perf.urls")),
    path('user/', include("PyAutoTest.auto_test.auto_user.urls")),
]

# # This class provides a way to replace text with values from a Redis client
# class RedisReplace:
#     # Initialize the class with a Redis client
#     def __init__(self, redis_client):
#         self.redis_client = redis_client
#
#     # Replace text with values from the Redis client
#     def replace(self, text):
#         while True:
#             # Find the start index of the key
#             start_index = text.find('${')
#             # If no key is found, break out of the loop
#             if start_index == -1:
#                 break
#             # Find the end index of the key
#             end_index = text.find('}', start_index)
#             # Get the key from the text
#             key = text[start_index + 2:end_index]
#             # Get the value from the Redis client
#             value = self.redis_client.get(key)
#             # Replace the key with the value in the text
#             text = text[:start_index] + value + text[end_index + 1:]
#         # Return the replaced text
#         return text

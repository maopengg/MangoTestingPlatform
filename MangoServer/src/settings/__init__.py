# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-12 14:15
# @Author : 毛鹏
import os
from pathlib import Path

from ..enums.tools_enum import SystemEnvEnum

VERSION = '5.6.9'
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# **********************************************************************************************************************
DJANGO_ENV = os.getenv('DJANGO_ENV', 'master')
if DJANGO_ENV == SystemEnvEnum.DEV.value:
    from .dev import *
elif DJANGO_ENV == SystemEnvEnum.PROD.value:
    from .prod import *
elif DJANGO_ENV == SystemEnvEnum.MASTER.value:
    from .master import *
elif DJANGO_ENV == SystemEnvEnum.TEST.value:
    from .test import *
else:
    print(f'测试环境：{DJANGO_ENV}')
    raise Exception(
        '你选择的环境不在系统默认的环境中，无法启动！！！如果你有能力修改代码请自行解决，如果没有能力请使用master即可')
# **********************************************************************************************************************

if not IS_MINIO:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/mango-file/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'mango-file')
else:
    DEFAULT_FILE_STORAGE = 'minio_storage.storage.MinioMediaStorage'
# **********************************************************************************************************************

USE_TZ = True

TIME_ZONE = 'Asia/Shanghai'
# **********************************************************************************************************************
ALLOWED_HOSTS = ["*"]
# **********************************************************************************************************************

SECRET_KEY = 'django-insecure-)7248+$v^i-e@u$=+jzwl1u(vvw0d$n5mepritgniru(&8gmu1'
# **********************************************************************************************************************

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',

    'src.auto_test.auto_ui',
    'src.auto_test.auto_api',
    'src.auto_test.auto_system',
    'src.auto_test.auto_perf',
    'src.auto_test.auto_user',
    'src.auto_test.auto_pytest',
    'rest_framework',  # 前后端分离
    'corsheaders',  # 跨域
    'channels',  # 验证
    'minio_storage',
]
# **********************************************************************************************************************

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # 跨域
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'src.middleware.log_collector.LogMiddleWare',
    'src.middleware.is_delete.IsDeleteMiddleWare',
]
# **********************************************************************************************************************

ROOT_URLCONF = 'src.urls'
# **********************************************************************************************************************

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
# **********************************************************************************************************************

ASGI_APPLICATION = 'src.asgi.application'
# **********************************************************************************************************************

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}
# **********************************************************************************************************************

if not IS_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': MYSQL_DB_NAME,
            'USER': MYSQL_USER,
            'PASSWORD': MYSQL_PASSWORD,
            'HOST': MYSQL_IP,
            'PORT': MYSQL_PORT,
            'TEST': {
                'NAME': MYSQL_DB_NAME,
                'CHARSET': 'utf8mb4',
                'COLLATION': 'utf8mb4_general_ci'
            },
            'OPTIONS': {
                "init_command": "SET foreign_key_checks = 0;",
            }
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
# **********************************************************************************************************************

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]
# **********************************************************************************************************************

LANGUAGE_CODE = 'en-us'
# **********************************************************************************************************************

USE_I18N = True
# **********************************************************************************************************************

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_URL = '/static/'
# **********************************************************************************************************************

# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": f"{redis}0",
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#             "CONNECTION_POOL_KWARGS": {
#                 "max_connections": 1000,
#                 "decode_responses": True,
#                 "encoding": 'utf-8'
#             }
#         }
#     },
#     "socket": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": f"{redis}1",
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#             "CONNECTION_POOL_KWARGS": {
#                 "max_connections": 1000,
#                 "decode_responses": True,
#                 "encoding": 'utf-8'
#             }
#         }
#     }
# }
# **********************************************************************************************************************

LOGGING = {
    'version': 1,  # 指明dictConnfig的版本
    'disable_existing_loggers': False,  # 表示是否禁用所有的已经存在的日志配置
    'formatters': {  # 格式器
        'colored': {
            '()': 'colorlog.ColoredFormatter',  # 使用 colorlog 的彩色格式化器
            'format': '%(log_color)s[%(asctime)s] [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'log_colors': {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'purple',
            },
        },
        'verbose': {  # 详细
            'format': '[%(asctime)s] [%(levelname)s] %(module)s %(process)s %(thread)s %(message)s',
        },

    },
    # 'filters':{}, 过滤器
    'handlers': {
        # 处理器，在这里定义了两个个处理器. 用来定义具体处理日志的方式，可以定义多种，"default"就是默认方式，"console"就是打印到控制台方式。files是写入到文件的方式，注意使用的class不同
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'colored',  # 使用彩色格式化器
        },
        'api': {  # 文件
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_api/log.log',  # 日志输出文件
            'formatter': 'verbose',  # 指定formatters日志格式
            'maxBytes': 1024 * 1024 * 10,  # 文件大小.50MB
            'backupCount': 30,
            'encoding': 'utf-8',
        },
        'ui': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_ui/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 30,
            'encoding': 'utf-8',
        },

        'system': {  # 文件
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_system/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 30,
            'encoding': 'utf-8',
        },
        'data_producer': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_perf/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 30,
            'encoding': 'utf-8',
        },
        'pytest': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_pytest/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 10,
            'backupCount': 30,
            'encoding': 'utf-8',
        },
    },
    'loggers': {  # log记录器，配置之后就会对应的输出日志
        'console': {  # django记录器，它将所有 INFO 或更高等级的消息传递给3个处理程序——files、console 和 default
            'handlers': ['console'],  # 同时输出到console和文件
            'level': 'DEBUG',
            'propagate': True,  # 向上接受更高级别日志
        },
        'api': {
            'handlers': ['api', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'ui': {
            'handlers': ['ui', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'system': {
            'handlers': ['system', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'data_producer': {
            'handlers': ['data_producer', 'console'],
            'level': 'INFO',
            'propagate': True,
        }
    }
}
# **********************************************************************************************************************

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['src.middleware.auth.JwtQueryParamsAuthentication', ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'
}
# **********************************************************************************************************************

# ************************ 接口文档 ************************ #
APPEND_SLASH = False

# ************************ 允许跨域设置 ************************  跨域增加忽略
CORS_ALLOW_CREDENTIALS = True  # 指明在跨域访问中，后端是否支持对cookie的操作
CORS_ORIGIN_ALLOW_ALL = True  # 设置支持所有域名访问,如果为False,需要指定域名
CORS_ALLOW_HEADERS = ('*',)
CORS_ORIGIN_WHITELIST = (
    'http://localhost:5173',
)  # 白名单，"*"支持所有域名进行访问，也可写成("域名1","域名")
CORS_ALLOW_METHODS = (
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
    'VIEW',
)

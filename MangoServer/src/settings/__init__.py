# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-07-12 14:15
# @Author : 毛鹏
"""
芒果测试平台 Django 通用配置入口。

普通部署和二次开发一般无需修改本文件。
请优先修改对应环境配置：
- 本地开发：src/settings/dev.py
- 测试环境：src/settings/test.py
- 默认/演示环境：src/settings/master.py

本文件只负责：
1. 选择并加载当前环境配置。
2. 读取 docker-compose、K8s 或服务器环境变量中的覆盖项。
3. 定义 Django 各环境共用的应用、中间件、数据库、缓存、日志等基础配置。
"""
import os
from pathlib import Path

import sys

from src.common.enums.tools_enum import SystemEnvEnum


def set_env():
    """支持通过 manage.py --env=dev/test/master 临时指定 Django 环境。"""
    for i, arg in enumerate(sys.argv):
        if '--env=' in arg:
            os.environ['DJANGO_ENV'] = arg.split('=')[1]
            del sys.argv[i]
            break


set_env()

# 当前平台版本号，会用于页面展示、接口返回以及 SECRET_KEY 生成。
VERSION = '6.2.1'

# 项目根目录：MangoServer。
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_bool(name: str, default: bool) -> bool:
    """读取布尔型环境变量，便于 docker-compose、K8s 或服务器配置覆盖默认值。"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def apply_object_storage_env_overrides() -> None:
    """
    读取文件存储相关环境变量。

    FILE_STORAGE_BACKEND 支持：
    - local：文件保存到本机 MangoServer/mango-file，适合本地开发。
    - minio：文件保存到 MinIO，适合开源 Docker Compose 演示部署。
    - tos：文件保存到火山 TOS 等兼容 S3 的对象存储，适合公司测试环境。
    """
    global FILE_STORAGE_BACKEND
    global MINIO_STORAGE_ENDPOINT
    global MINIO_STORAGE_MEDIA_BUCKET_NAME
    global MINIO_STORAGE_ACCESS_KEY
    global MINIO_STORAGE_SECRET_KEY
    global MINIO_PUBLIC_BASE_URL
    global MINIO_STORAGE_REGION
    global MINIO_STORAGE_USE_HTTPS
    global MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET
    global MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE
    global MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS
    global MINIO_STORAGE_MEDIA_USE_PRESIGNED

    FILE_STORAGE_BACKEND = os.getenv("FILE_STORAGE_BACKEND", globals().get("FILE_STORAGE_BACKEND", "local"))
    if FILE_STORAGE_BACKEND == "local":
        return

    # 对象存储使用同一组 S3 兼容配置；MinIO 和 TOS 只需要在环境配置中填入不同地址和密钥。
    string_overrides = {
        "MINIO_STORAGE_ENDPOINT": "MINIO_STORAGE_ENDPOINT",
        "MINIO_STORAGE_MEDIA_BUCKET_NAME": "MINIO_STORAGE_MEDIA_BUCKET_NAME",
        "MINIO_STORAGE_ACCESS_KEY": "MINIO_STORAGE_ACCESS_KEY",
        "MINIO_STORAGE_SECRET_KEY": "MINIO_STORAGE_SECRET_KEY",
        "MINIO_PUBLIC_BASE_URL": "MINIO_PUBLIC_BASE_URL",
        "MINIO_STORAGE_REGION": "MINIO_STORAGE_REGION",
    }
    for setting_name, env_name in string_overrides.items():
        value = os.getenv(env_name)
        if value:
            globals()[setting_name] = value

    MINIO_STORAGE_USE_HTTPS = env_bool(
        "MINIO_STORAGE_USE_HTTPS",
        globals().get("MINIO_STORAGE_USE_HTTPS", False),
    )
    MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = env_bool(
        "MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET",
        globals().get("MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET", True),
    )
    MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE = env_bool(
        "MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE",
        globals().get("MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE", False),
    )
    MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS = env_bool(
        "MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS",
        globals().get("MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS", False),
    )
    MINIO_STORAGE_MEDIA_USE_PRESIGNED = env_bool(
        "MINIO_STORAGE_MEDIA_USE_PRESIGNED",
        globals().get("MINIO_STORAGE_MEDIA_USE_PRESIGNED", False),
    )


# ======================================================================================================================
# 环境选择
# ----------------------------------------------------------------------------------------------------------------------
# DJANGO_ENV 默认使用 master，方便开源版本直接通过 docker-compose 启动。
# 可选值：
# - dev：本地开发环境
# - test：测试环境
# - master：默认/演示环境
DJANGO_ENV = os.getenv('DJANGO_ENV', 'master')
# 只在主进程（实际运行服务器的进程）中打印，避免Django自动重载导致的重复打印
# RUN_MAIN 是 Django runserver 自动重载器设置的，只有在实际运行服务器的子进程中才会是 'true'
# 如果使用其他方式启动（如 uvicorn），RUN_MAIN 可能不存在，此时也打印一次
run_main = os.environ.get('RUN_MAIN')
# 只在主进程中打印：RUN_MAIN == 'true'（runserver 的实际运行进程）或 RUN_MAIN 不存在（其他启动方式）
if run_main == 'true' or (run_main is None and 'runserver' not in sys.argv):
    # 使用模块级别的标志来确保每个进程只打印一次
    if not hasattr(sys.modules[__name__], '_env_printed'):
        sys.modules[__name__]._env_printed = True
if DJANGO_ENV == SystemEnvEnum.DEV.value:
    from .dev import *
elif DJANGO_ENV == SystemEnvEnum.MASTER.value:
    from .master import *
elif DJANGO_ENV == SystemEnvEnum.TEST.value:
    from .test import *
else:
    print(f'测试环境：{DJANGO_ENV}')
    raise Exception(
        '你选择的环境不在系统默认的环境中，无法启动！！！如果你有能力修改代码请自行解决，如果没有能力请使用master即可')

# 环境文件加载完成后，再允许系统环境变量覆盖文件存储配置。
apply_object_storage_env_overrides()
FILE_STORAGE_BACKEND = globals().get('FILE_STORAGE_BACKEND', 'local')
if FILE_STORAGE_BACKEND not in {'local', 'minio', 'tos'}:
    raise Exception('FILE_STORAGE_BACKEND 只支持 local、minio、tos')
OBJECT_STORAGE_ENABLED = FILE_STORAGE_BACKEND in {'minio', 'tos'}
# ======================================================================================================================

# ======================================================================================================================
# 监控模块动态导入路径
# ----------------------------------------------------------------------------------------------------------------------
# 监控基类（MonitorBase）在作为第三方库使用时，通过以下配置动态导入 Django 项目中的模型和类。
# 目前在本项目中默认指向自身的实现路径；如果将来拆分为独立库，其他项目只需在自己的 settings 中配置相同名称即可。
MONITORING_REPORT_MODEL = "src.apps.monitoring.models.MonitoringReport"
MONITORING_TASK_MODEL = "src.apps.monitoring.models.MonitoringTask"
MONITORING_LOG_STATUS_ENUM = "src.common.enums.monitoring_enum.MonitoringLogStatusEnum"
MONITORING_NOTICE_MAIN = "src.apps.auto_system.service.notice.NoticeMain"

RETRY_FREQUENCY = 3
# ======================================================================================================================

# ======================================================================================================================
# 日志和上传文件目录
# ----------------------------------------------------------------------------------------------------------------------
# 容器和本地运行都会自动创建这些目录，不需要提前手工创建。
for log_dir in [
    BASE_DIR / 'logs',
    BASE_DIR / 'logs/auto_api',
    BASE_DIR / 'logs/auto_ui',
    BASE_DIR / 'logs/auto_system',
    BASE_DIR / 'logs/auto_perf',
    BASE_DIR / 'logs/auto_pytest',
    BASE_DIR / 'logs/monitoring',
]:
    os.makedirs(log_dir, exist_ok=True)

# 文件存储策略：
# - local：使用 Django 本地文件存储，文件位于 MangoServer/mango-file。
# - minio/tos：使用项目封装的对象存储，实际连接信息由环境配置或环境变量提供。
if not OBJECT_STORAGE_ENABLED:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_URL = '/mango-file/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'mango-file')
else:
    DEFAULT_FILE_STORAGE = 'src.common.tools.storage.MangoMinioMediaStorage'

# ======================================================================================================================

# ======================================================================================================================
# Django 基础配置
USE_TZ = False

TIME_ZONE = 'Asia/Shanghai'

# ALLOWED_HOSTS 目前放开给网关、容器网络和多环境域名统一接入。
# MCP 服务有独立的允许访问域名配置，见各环境文件中的 MCP_ALLOWED_HOSTS / MCP_ALLOWED_ORIGINS。
ALLOWED_HOSTS = ["*"]

# 如需正式生产使用，建议通过环境变量或安全配置中心替换为固定强随机密钥。
SECRET_KEY = f'django-insecure-)7248+$v^i-e@u$=+jzwl1u(vvw0d$n5mepritgniru(&8gmu1{VERSION}'
# ======================================================================================================================

# ======================================================================================================================
# Django 应用
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',

    'src.apps.auto_ui',
    'src.apps.auto_api',
    'src.apps.auto_system',
    'src.apps.auto_data_factory',
    'src.apps.auto_perf',
    'src.apps.auto_user',
    'src.apps.auto_pytest',
    'src.apps.monitoring',
    'src.apps.task_center',
    'rest_framework',  # 前后端分离
    'corsheaders',  # 跨域
    'channels',  # 验证
    'minio_storage',
]
# ======================================================================================================================

# ======================================================================================================================
# Django 中间件
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # 跨域
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # 添加Gzip压缩支持
    # 'src.common.middleware.log_collector.LogMiddleWare',
    'src.common.middleware.user_logs.UserLogsMiddleWare',
    # 'src.common.middleware.operation_log.OperationLogMiddleware',
    'src.common.middleware.is_delete.IsDeleteMiddleWare',
]
# ======================================================================================================================

# ======================================================================================================================
# 路由、模板和 ASGI
ROOT_URLCONF = 'src.urls'

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

ASGI_APPLICATION = 'src.asgi.application'

# WebSocket/Channels 默认使用进程内内存通道，适合单机部署。
# 如果后续需要多节点 WebSocket 广播，可替换为 RedisChannelLayer。
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
        'CONFIG': {
            'capacity': 1000,
        }
    }
}
# ======================================================================================================================

# ======================================================================================================================
# 数据库
# ----------------------------------------------------------------------------------------------------------------------
# 各环境文件只负责提供 MYSQL_* 和 IS_SQLITE，本文件统一生成 Django DATABASES。
# 默认推荐 MySQL；SQLite 仅适合本地轻量验证。
if not IS_SQLITE:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': MYSQL_DB_NAME,
            'USER': MYSQL_USER,
            'PASSWORD': MYSQL_PASSWORD,
            'HOST': MYSQL_IP,
            'PORT': MYSQL_PORT,
            'OPTIONS': {
                'charset': 'utf8mb4',
                'connect_timeout': 20,
                'read_timeout': 60,
                'write_timeout': 60,
                # 保持严格模式，避免脏数据静默写入。
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES', wait_timeout=300",
                'isolation_level': 'READ COMMITTED',
                'autocommit': True,
            },
            # Django 自身业务库连接复用 5 分钟，降低接口频繁建连成本。
            'CONN_MAX_AGE': 300,
            'CONN_HEALTH_CHECKS': True,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
# ======================================================================================================================

# ======================================================================================================================
# 认证、国际化和静态资源
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

LANGUAGE_CODE = 'en-us'
USE_I18N = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
STATIC_URL = '/static/'
# ======================================================================================================================

# ======================================================================================================================
# 缓存
# ----------------------------------------------------------------------------------------------------------------------
# REDIS 在各环境文件中配置：
# - True：使用 Redis 缓存。
# - False：使用 Django 数据库缓存表 django_cache。
if REDIS:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/0',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'django_cache',  # 数据库表名
        }
    }

# ======================================================================================================================

# ======================================================================================================================
# 日志
# ----------------------------------------------------------------------------------------------------------------------
# 业务日志统一写入 MangoServer/logs，容器部署时可通过 docker logs 查看控制台关键日志。
# 文件日志使用 RotatingFileHandler，避免单个日志文件无限增长。
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'colored': {
            '()': 'colorlog.ColoredFormatter',
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
        'verbose': {
            'format': '[%(asctime)s] [%(levelname)s] %(module)s %(process)d %(thread)d %(message)s',
        },
        'standard': {  # 添加标准格式化器
            'format': '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s'
        }
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'colored',
        },
        'api': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_api/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 50,  # 增加到50MB
            'backupCount': 10,  # 减少备份数量
            'encoding': 'utf-8',
        },
        'ui': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_ui/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 50,
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'system': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_system/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 50,
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'data_producer': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_perf/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 50,
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'pytest': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/auto_pytest/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 50,
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'monitoring': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/monitoring/log.log',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 50,
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'django': {  # 添加Django核心日志处理器
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs/django.log',
            'formatter': 'standard',
            'maxBytes': 1024 * 1024 * 50,
            'backupCount': 5,
            'encoding': 'utf-8',
        }
    },
    'loggers': {
        'console': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,  # 防止重复日志
        },
        'api': {
            'handlers': ['api', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'ui': {
            'handlers': ['ui', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'system': {
            'handlers': ['system', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'data_producer': {
            'handlers': ['data_producer', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django': {  # Django核心日志记录器
            'handlers': ['django'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {  # Django请求错误
            'handlers': ['django'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apscheduler': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'apscheduler.executors.default': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        }
    }
}
# ======================================================================================================================

# ======================================================================================================================
# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['src.common.middleware.auth.JwtQueryParamsAuthentication', ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'
}
# ======================================================================================================================

# ======================================================================================================================
# API 路由和跨域
APPEND_SLASH = False

# 开源演示和本地开发默认允许跨域，方便前后端分离调试。
# 若用于更严格的生产环境，可改为 CORS_ORIGIN_ALLOW_ALL=False，并维护 CORS_ORIGIN_WHITELIST。
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = ('*',)
CORS_ORIGIN_WHITELIST = (
    'http://localhost:5173',
)
CORS_ALLOW_METHODS = (
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
    'VIEW',
)
# ======================================================================================================================

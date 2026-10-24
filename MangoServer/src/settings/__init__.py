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
import socket
from pathlib import Path

import sys

from src.apps.system.enums.deployment import SystemEnvEnum
from src.common.logging.config import build_logging_config, normalize_log_level


def set_env():
    """支持通过 manage.py --env=dev/test/master 临时指定 Django 环境。"""
    for i, arg in enumerate(sys.argv):
        if '--env=' in arg:
            os.environ['DJANGO_ENV'] = arg.split('=')[1]
            del sys.argv[i]
            break


set_env()

# 当前平台版本号，会用于页面展示、接口返回以及 SECRET_KEY 生成。
VERSION = '7.2.2'

# 项目根目录：MangoServer。
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env_bool(name: str, default: bool) -> bool:
    """读取布尔型环境变量，便于 docker-compose、K8s 或服务器配置覆盖默认值。"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return BASE_DIR / path


# 断言结果 actual、ass_msg 等诊断字段的单项保存和页面展示字符数上限。
# 断言执行过程仍使用完整数据；完整接口响应继续保存在 response.json 中。
ASSERTION_RESULT_DISPLAY_MAX_LENGTH = max(
    1,
    env_int('ASSERTION_RESULT_DISPLAY_MAX_LENGTH', 500),
)

RUNTIME_DIR = env_path('MANGO_RUNTIME_DIR', BASE_DIR / 'runtime')
STATIC_RESOURCE_DIR = env_path('MANGO_STATIC_RESOURCE_DIR', BASE_DIR / 'static_resources')
LOG_ROOT_DIR = env_path('MANGO_LOG_ROOT_DIR', RUNTIME_DIR / 'logs')
MEDIA_ROOT_DIR = env_path('MANGO_MEDIA_ROOT', RUNTIME_DIR / 'media')
DOWNLOAD_DIR = env_path('MANGO_DOWNLOAD_DIR', RUNTIME_DIR / 'download')
UPLOAD_DIR = env_path('MANGO_UPLOAD_DIR', RUNTIME_DIR / 'upload')
FAILED_SCREENSHOT_DIR = env_path('MANGO_FAILED_SCREENSHOT_DIR', RUNTIME_DIR / 'failed_screenshot')
GIT_WORKSPACE_DIR = env_path('MANGO_GIT_WORKSPACE_DIR', RUNTIME_DIR / 'git_workspace')
MONITORING_RUNTIME_DIR = env_path('MANGO_MONITORING_RUNTIME_DIR', RUNTIME_DIR / 'monitoring')
MONITORING_SCRIPT_DIR = MONITORING_RUNTIME_DIR / 'scripts'
MONITORING_LOG_DIR = MONITORING_RUNTIME_DIR / 'logs'


def apply_object_storage_env_overrides() -> None:
    """
    读取文件存储相关环境变量。

    FILE_STORAGE_BACKEND 支持：
    - local：文件保存到本机 MangoServer/runtime/media，适合本地开发。
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
# - prod：生产部署别名，复用 master 配置。
DJANGO_ENV = os.getenv('DJANGO_ENV', 'master')
if DJANGO_ENV == 'prod':
    DJANGO_ENV = SystemEnvEnum.MASTER.value
    os.environ['DJANGO_ENV'] = DJANGO_ENV
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
    from .dev import (
        DEBUG,
        FILE_STORAGE_BACKEND,
        IS_DEBUG_LOG,
        IS_SQLITE,
        IS_TRUE,
        MCP_ALLOWED_HOSTS,
        MCP_ALLOWED_ORIGINS,
        MYSQL_DB_NAME,
        MYSQL_IP,
        MYSQL_PASSWORD,
        MYSQL_PORT,
        MYSQL_USER,
        REDIS,
        file_name,
        json,
        os,
    )
elif DJANGO_ENV == SystemEnvEnum.MASTER.value:
    from .master import (
        DEBUG,
        FILE_STORAGE_BACKEND,
        IS_DEBUG_LOG,
        IS_SQLITE,
        MCP_ALLOWED_HOSTS,
        MCP_ALLOWED_ORIGINS,
        MINIO_PUBLIC_BASE_URL,
        MINIO_STORAGE_ACCESS_KEY,
        MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS,
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET,
        MINIO_STORAGE_ENDPOINT,
        MINIO_STORAGE_MEDIA_BUCKET_NAME,
        MINIO_STORAGE_MEDIA_USE_PRESIGNED,
        MINIO_STORAGE_SECRET_KEY,
        MINIO_STORAGE_USE_HTTPS,
        MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE,
        MYSQL_DB_NAME,
        MYSQL_IP,
        MYSQL_PASSWORD,
        MYSQL_PORT,
        MYSQL_USER,
        REDIS,
    )
elif DJANGO_ENV == SystemEnvEnum.TEST.value:
    from .test import (
        DEBUG,
        FILE_STORAGE_BACKEND,
        IS_DEBUG_LOG,
        IS_SQLITE,
        MCP_ALLOWED_HOSTS,
        MCP_ALLOWED_ORIGINS,
        MINIO_PUBLIC_BASE_URL,
        MINIO_STORAGE_ACCESS_KEY,
        MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS,
        MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET,
        MINIO_STORAGE_ENDPOINT,
        MINIO_STORAGE_MEDIA_BUCKET_NAME,
        MINIO_STORAGE_MEDIA_USE_PRESIGNED,
        MINIO_STORAGE_SECRET_KEY,
        MINIO_STORAGE_USE_HTTPS,
        MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE,
        MYSQL_DB_NAME,
        MYSQL_IP,
        MYSQL_PASSWORD,
        MYSQL_PORT,
        MYSQL_USER,
        REDIS,
    )
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
FILE_STORAGE_ROOT = os.getenv(
    'FILE_STORAGE_ROOT',
    globals().get('FILE_STORAGE_ROOT', 'mango-testing-platform/master'),
).strip('/\\')
# 环境无关的执行结果存储默认值集中在此；部署时仍可通过环境变量覆盖。
RESULT_DATA_TO_FILE = env_bool('RESULT_DATA_TO_FILE', True)
RESULT_DATA_FILE_PREFIX = os.getenv('RESULT_DATA_FILE_PREFIX', 'result')
RESULT_DATA_DETAIL_INLINE_MAX_SIZE = env_int(
    'RESULT_DATA_DETAIL_INLINE_MAX_SIZE',
    5 * 1024 * 1024,
)
# UI 存储子目录属于部署配置；截图和录屏分别放在其 screenshot/、videos/ 下。
# 保留天数统一由配置管理的 UI_ARTIFACT_RETENTION_DAYS 控制，不在 settings 中重复定义。
UI_EXECUTION_ARTIFACT_ROOT_DIR = os.getenv('UI_EXECUTION_ARTIFACT_ROOT_DIR', 'uitest')
# ======================================================================================================================

# ======================================================================================================================
# 监控模块动态导入路径
# ----------------------------------------------------------------------------------------------------------------------
# 监控基类（MonitorBase）在作为第三方库使用时，通过以下配置动态导入 Django 项目中的模型和类。
# 目前在本项目中默认指向自身的实现路径；如果将来拆分为独立库，其他项目只需在自己的 settings 中配置相同名称即可。
MONITORING_REPORT_MODEL = "src.apps.monitoring.models.MonitoringReport"
MONITORING_TASK_MODEL = "src.apps.monitoring.models.MonitoringTask"
MONITORING_LOG_STATUS_ENUM = "src.apps.monitoring.enums.MonitoringLogStatusEnum"
MONITORING_NOTICE_MAIN = "src.apps.system.services.notice.NoticeMain"
# ======================================================================================================================

# ======================================================================================================================
# 运行时目录
# ----------------------------------------------------------------------------------------------------------------------
# 容器和本地运行都会自动创建这些目录，不需要提前手工创建。代码资源仍放在 static_resources，
# 日志、上传/下载临时文件、本地媒体文件、Git 缓存等运行时产物统一收口到 runtime。
for runtime_dir in [
    RUNTIME_DIR,
    LOG_ROOT_DIR,
    MEDIA_ROOT_DIR,
    DOWNLOAD_DIR,
    UPLOAD_DIR,
    FAILED_SCREENSHOT_DIR,
    GIT_WORKSPACE_DIR,
    MONITORING_SCRIPT_DIR,
    MONITORING_LOG_DIR,
]:
    os.makedirs(runtime_dir, exist_ok=True)

# 文件存储策略：
# - local：使用 Django 本地文件存储，文件位于 MangoServer/runtime/media。
# - minio/tos：使用项目封装的对象存储，实际连接信息由环境配置或环境变量提供。
MEDIA_URL = '/mango-file/'
MEDIA_ROOT = str(MEDIA_ROOT_DIR)
STORAGES = {
    'default': {
        'BACKEND': (
            'src.common.storage.MangoMinioMediaStorage'
            if OBJECT_STORAGE_ENABLED
            else 'django.core.files.storage.FileSystemStorage'
        ),
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# ======================================================================================================================

# ======================================================================================================================
# Django 基础配置
USE_TZ = False

TIME_ZONE = 'Asia/Shanghai'

# ALLOWED_HOSTS 目前放开给网关、容器网络和多环境域名统一接入。
# MCP 服务有独立的允许访问域名配置，见各环境文件中的 MCP_ALLOWED_HOSTS / MCP_ALLOWED_ORIGINS。
ALLOWED_HOSTS = ["*"]

# 如需正式生产使用，建议通过环境变量或安全配置中心替换为固定强随机密钥。
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or f'django-insecure-)7248+$v^i-e@u$=+jzwl1u(vvw0d$n5mepritgniru(&8gmu1{VERSION}'
LIVE_STREAM_SIGNING_KEY = os.getenv('LIVE_STREAM_SIGNING_KEY') or f'{SECRET_KEY}:ui-live-stream'
LIVE_STREAM_PREVIOUS_SIGNING_KEY = os.getenv('LIVE_STREAM_PREVIOUS_SIGNING_KEY') or ''
REALTIME_MESSAGE_BATCH_SIZE = int(os.getenv('REALTIME_MESSAGE_BATCH_SIZE', '100'))
REALTIME_MESSAGE_ACTIVE_INTERVAL = float(os.getenv('REALTIME_MESSAGE_ACTIVE_INTERVAL', '0.2'))
REALTIME_MESSAGE_IDLE_INTERVAL = float(os.getenv('REALTIME_MESSAGE_IDLE_INTERVAL', '1'))
REALTIME_MESSAGE_SEND_TIMEOUT = float(os.getenv('REALTIME_MESSAGE_SEND_TIMEOUT', '5'))
REALTIME_MESSAGE_LEASE_SECONDS = int(os.getenv('REALTIME_MESSAGE_LEASE_SECONDS', '30'))
REALTIME_MESSAGE_MAX_RETRIES = int(os.getenv('REALTIME_MESSAGE_MAX_RETRIES', '7'))
# ======================================================================================================================

# ======================================================================================================================
# Django 应用
INSTALLED_APPS = [
    'daphne',
    'django.contrib.staticfiles',

    'src.apps.auto_ui',
    'src.apps.auto_api',
    'src.apps.system.apps.SystemConfig',
    'src.apps.test_center.apps.TestCenterConfig',
    'src.apps.data_factory.apps.DataFactoryConfig',
    'src.apps.perf.apps.PerfConfig',
    'src.apps.user.apps.UserConfig',
    'src.apps.auto_pytest',
    'src.apps.gray_config',
    'src.apps.monitoring',
    'src.apps.task_center',
    'src.apps.ai.apps.AiConfig',
    'src.apps.functional_test',
    'src.apps.evaluation.apps.EvaluationConfig',
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
    'corsheaders.middleware.CorsMiddleware',  # 跨域
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',  # 添加Gzip压缩支持
    # 'src.common.middleware.log_collector.LogMiddleWare',
    'src.apps.user.middleware.user_logs.UserLogsMiddleWare',
    # 'src.common.middleware.operation_log.OperationLogMiddleware',
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
            ],
        },
    },
]

ASGI_APPLICATION = 'src.asgi.application'
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

# ID 号段必须独立提交，不能复用可能被业务事务回滚的 default 连接。
DATABASES['id_allocator'] = {
    **DATABASES['default'],
    'ATOMIC_REQUESTS': False,
    'AUTOCOMMIT': True,
    'CONN_MAX_AGE': 0,
    'TEST': {'MIRROR': 'default'},
}
SNOWFLAKE_BLOCK_ALLOCATOR = 'src.apps.system.services.id_sequence.reserve_snowflake_block'

# ======================================================================================================================
# 国际化和静态资源
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
# 业务 logger 仍按 api/ui/system/pytest 等业务域分类，运行服务由环境变量注入：
# - MANGO_SERVICE_NAME：core-api、scheduler-service、api-worker、mcp-service 等。
# - MANGO_SERVICE_INSTANCE：本地实例名、容器名或 K8s Pod 名。
# 文件日志按服务写入 logs/{service}/，容器部署时仍可通过 docker logs 查看控制台日志。
def infer_service_name_from_command() -> str:
    command = ' '.join(sys.argv)
    command_map = {
        'run_scheduler': 'scheduler-service',
        'run_api_worker': 'api-worker',
        'run_mcp_service': 'mcp-service',
        'run_realtime_service': 'realtime-service',
        'run_monitoring_service': 'monitoring-service',
    }
    for command_name, service_name in command_map.items():
        if command_name in command:
            return service_name
    return 'core-api'


MANGO_SERVICE_NAME = os.getenv('MANGO_SERVICE_NAME') or infer_service_name_from_command()
MANGO_SERVICE_INSTANCE = os.getenv('MANGO_SERVICE_INSTANCE', socket.gethostname())
ACCESS_LOG_LEVEL = 'INFO' if DJANGO_ENV == SystemEnvEnum.DEV.value else 'WARNING'
SERVICE_LOG_DIR = LOG_ROOT_DIR / MANGO_SERVICE_NAME
BUSINESS_LOG_LEVEL = normalize_log_level(
    os.getenv('MANGO_LOG_LEVEL'),
    debug_default=IS_DEBUG_LOG,
)
# The effective level is the source of truth when MANGO_LOG_LEVEL overrides
# the legacy debug switch. Runtime status APIs must report the real behavior.
IS_DEBUG_LOG = BUSINESS_LOG_LEVEL == 'DEBUG'
LOG_MAX_BYTES = max(1024, env_int('MANGO_LOG_MAX_BYTES', 50 * 1024 * 1024))
LOG_BACKUP_COUNT = max(1, env_int('MANGO_LOG_BACKUP_COUNT', 10))
DJANGO_LOG_BACKUP_COUNT = max(1, env_int('MANGO_DJANGO_LOG_BACKUP_COUNT', 5))
LOGGING = build_logging_config(
    service_name=MANGO_SERVICE_NAME,
    service_instance=MANGO_SERVICE_INSTANCE,
    service_log_dir=SERVICE_LOG_DIR,
    business_level=BUSINESS_LOG_LEVEL,
    access_log_level=ACCESS_LOG_LEVEL,
    max_bytes=LOG_MAX_BYTES,
    backup_count=LOG_BACKUP_COUNT,
    django_backup_count=DJANGO_LOG_BACKUP_COUNT,
)
# ======================================================================================================================

# ======================================================================================================================
# Django REST Framework
SYSTEM_ERROR_REPORTER = (
    "src.apps.system.services.runtime_center.system_error_event."
    "record_system_error"
)
MODEL_CRUD_DATA_SCOPE_POLICY = "src.apps.user.services.model_crud_scope.ModelCrudDataScopePolicy"
MODEL_CRUD_MODULE_VALIDATOR = (
    "src.apps.test_center.services.product_module.validate_crud_module_binding"
)
MODEL_CRUD_CONFIG_AUDIT_ADAPTER = (
    "src.apps.auto_api.services.config.audit_adapter.ModelCrudConfigAuditAdapter"
)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['src.apps.user.middleware.auth.JwtQueryParamsAuthentication', ],
    'DEFAULT_PERMISSION_CLASSES': ['src.apps.user.middleware.permission.MenuActionPermission', ],
    # 项目使用自定义 User + JWT，未认证请求不创建 Django auth.AnonymousUser。
    'UNAUTHENTICATED_USER': None,
    'UNAUTHENTICATED_TOKEN': None,
    'DEFAULT_THROTTLE_CLASSES': ['src.common.middleware.throttle.MangoScopedRateThrottle', ],
    'DEFAULT_THROTTLE_RATES': {
        'login': '20/min',
        'credential_email': '5/hour',
        'ai': '60/min',
        'execute': '120/min',
        'export': '30/min',
        'download': '120/min',
    },
    'EXCEPTION_HANDLER': 'src.apps.system.middleware.exception_handler.mango_exception_handler',
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

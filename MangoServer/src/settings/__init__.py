# -*- coding: utf-8 -*-
"""公共配置。"""
import os
import socket
from pathlib import Path

import sys
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured

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

# ── 1. 公共参数与目录 ─────────────────────────────────────────
VERSION = '7.2.6'  # 平台版本号

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # 后端根目录 MangoServer


def env_bool(name: str, default: bool) -> bool:
    """读取布尔型环境变量。"""
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


ASSERTION_RESULT_DISPLAY_MAX_LENGTH = max(  # 断言诊断字段保存与展示字符上限，最小为 1
    1,
    env_int('ASSERTION_RESULT_DISPLAY_MAX_LENGTH', 500),
)

RUNTIME_DIR = env_path('MANGO_RUNTIME_DIR', BASE_DIR / 'runtime')  # 运行文件根目录
STATIC_RESOURCE_DIR = env_path('MANGO_STATIC_RESOURCE_DIR', BASE_DIR / 'static_resources')  # 内置资源目录
LOG_ROOT_DIR = env_path('MANGO_LOG_ROOT_DIR', RUNTIME_DIR / 'logs')  # 服务日志根目录
MEDIA_ROOT_DIR = env_path('MANGO_MEDIA_ROOT', RUNTIME_DIR / 'media')  # 本地文件存储目录
DOWNLOAD_DIR = env_path('MANGO_DOWNLOAD_DIR', RUNTIME_DIR / 'download')  # 下载临时目录
UPLOAD_DIR = env_path('MANGO_UPLOAD_DIR', RUNTIME_DIR / 'upload')  # 上传临时目录
FAILED_SCREENSHOT_DIR = env_path('MANGO_FAILED_SCREENSHOT_DIR', RUNTIME_DIR / 'failed_screenshot')  # 失败截图临时目录
GIT_WORKSPACE_DIR = env_path('MANGO_GIT_WORKSPACE_DIR', RUNTIME_DIR / 'git_workspace')  # Git 仓库工作目录
MONITORING_RUNTIME_DIR = env_path('MANGO_MONITORING_RUNTIME_DIR', RUNTIME_DIR / 'monitoring')  # 监控运行目录
MONITORING_SCRIPT_DIR = MONITORING_RUNTIME_DIR / 'scripts'  # 监控脚本目录
MONITORING_LOG_DIR = MONITORING_RUNTIME_DIR / 'logs'  # 监控日志目录


def apply_object_storage_env_overrides() -> None:
    """读取文件存储环境变量。"""
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

    FILE_STORAGE_BACKEND = os.getenv("FILE_STORAGE_BACKEND", globals().get("FILE_STORAGE_BACKEND", "local"))  # 可选：local / minio / tos
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

    MINIO_STORAGE_USE_HTTPS = env_bool(  # 可选：True / False；是否通过 HTTPS 连接
        "MINIO_STORAGE_USE_HTTPS",
        True,
    )
    MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET = env_bool(  # 可选：True / False；桶不存在时是否自动创建
        "MINIO_STORAGE_AUTO_CREATE_MEDIA_BUCKET",
        False,
    )
    MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE = env_bool(  # 可选：True / False；是否使用“桶名.服务地址”访问文件
        "MINIO_STORAGE_USE_VIRTUAL_HOST_STYLE",
        FILE_STORAGE_BACKEND == 'tos',
    )
    MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS = env_bool(  # 可选：True / False；是否跳过桶存在检查
        "MINIO_STORAGE_ASSUME_MEDIA_BUCKET_EXISTS",
        True,
    )
    MINIO_STORAGE_MEDIA_USE_PRESIGNED = env_bool(  # 可选：True / False；是否生成带临时访问凭证的下载链接
        "MINIO_STORAGE_MEDIA_USE_PRESIGNED",
        True,
    )


# ── 2. 环境选择与连接配置 ─────────────────────────────────────────
DJANGO_ENV = os.getenv('DJANGO_ENV', 'master')  # 可选：dev / test / master / prod；prod 等同 master
if DJANGO_ENV == 'prod':
    DJANGO_ENV = SystemEnvEnum.MASTER.value
    os.environ['DJANGO_ENV'] = DJANGO_ENV
# runserver 重载子进程与 uvicorn 等入口分别保留初始化标记。
run_main = os.environ.get('RUN_MAIN')
if run_main == 'true' or (run_main is None and 'runserver' not in sys.argv):
    if not hasattr(sys.modules[__name__], '_env_printed'):
        sys.modules[__name__]._env_printed = True
ENVIRONMENT_SETTING_NAMES = (
    # 环境开关与 MCP 白名单。
    'DEBUG', 'FILE_STORAGE_BACKEND', 'IS_DEBUG_LOG',
    'MCP_ALLOWED_HOSTS', 'MCP_ALLOWED_ORIGINS',
    # MySQL 连接。
    'MYSQL_DB_NAME', 'MYSQL_IP', 'MYSQL_PASSWORD', 'MYSQL_PORT', 'MYSQL_USER',
    # 对象存储连接。
    'MINIO_PUBLIC_BASE_URL', 'MINIO_STORAGE_ACCESS_KEY', 'MINIO_STORAGE_SECRET_KEY',
    'MINIO_STORAGE_ENDPOINT', 'MINIO_STORAGE_MEDIA_BUCKET_NAME', 'MINIO_STORAGE_REGION',
)
if DJANGO_ENV not in {SystemEnvEnum.DEV.value, SystemEnvEnum.TEST.value, SystemEnvEnum.MASTER.value}:
    raise ImproperlyConfigured('DJANGO_ENV 只支持 dev、test、master、prod')
environment_settings = import_module(f'.{DJANGO_ENV}', __name__)
for setting_name in ENVIRONMENT_SETTING_NAMES:
    if not hasattr(environment_settings, setting_name):
        raise ImproperlyConfigured(f'{DJANGO_ENV} 环境缺少配置项：{setting_name}')
    globals()[setting_name] = getattr(environment_settings, setting_name)

MYSQL_DB_NAME = os.getenv('MYSQL_DATABASE', MYSQL_DB_NAME)  # 必填：平台使用的数据库名称
MYSQL_USER = os.getenv('MYSQL_USER', MYSQL_USER)  # 必填：数据库用户名
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', MYSQL_PASSWORD)  # 必填：数据库用户密码
MYSQL_IP = os.getenv('MYSQL_HOST', MYSQL_IP)  # 必填：数据库服务器 IP 或域名
MYSQL_PORT = int(os.getenv('MYSQL_PORT', MYSQL_PORT))  # 必填：数据库端口，通常为 3306

apply_object_storage_env_overrides()
FILE_STORAGE_BACKEND = globals().get('FILE_STORAGE_BACKEND', 'local')  # 可选：local / minio / tos
if FILE_STORAGE_BACKEND not in {'local', 'minio', 'tos'}:
    raise ImproperlyConfigured('FILE_STORAGE_BACKEND 只支持 local、minio、tos')
OBJECT_STORAGE_ENABLED = FILE_STORAGE_BACKEND in {'minio', 'tos'}  # 是否使用对象存储
if OBJECT_STORAGE_ENABLED:
    missing_storage_settings = [
        name for name in ('MINIO_STORAGE_ENDPOINT', 'MINIO_STORAGE_MEDIA_BUCKET_NAME',
                          'MINIO_STORAGE_ACCESS_KEY', 'MINIO_STORAGE_SECRET_KEY')
        if not str(globals().get(name) or '').strip()
    ]
    if missing_storage_settings:
        raise ImproperlyConfigured(
            f'{DJANGO_ENV} 的 {FILE_STORAGE_BACKEND} 存储缺少必填配置：'
            + '、'.join(missing_storage_settings)
            + '；请填写对应环境配置文件或同名环境变量。'
        )
FILE_STORAGE_ROOT = os.getenv(  # 存储空间内的平台文件根目录
    'FILE_STORAGE_ROOT',
    globals().get('FILE_STORAGE_ROOT', 'mango-testing-platform/master'),
).strip('/\\')
RESULT_DATA_TO_FILE = env_bool('RESULT_DATA_TO_FILE', True)  # 可选：True / False；是否将执行结果正文保存为文件
RESULT_DATA_FILE_PREFIX = os.getenv('RESULT_DATA_FILE_PREFIX', 'result')  # 执行结果文件目录前缀
RESULT_DATA_DETAIL_INLINE_MAX_SIZE = env_int(  # 结果详情内联内容大小上限，单位：字节
    'RESULT_DATA_DETAIL_INLINE_MAX_SIZE',
    5 * 1024 * 1024,
)
UI_EXECUTION_ARTIFACT_ROOT_DIR = os.getenv('UI_EXECUTION_ARTIFACT_ROOT_DIR', 'uitest')  # UI 截图、录屏的存储目录前缀

# ── 3. 监控模块扩展入口 ─────────────────────────────────────────
MONITORING_REPORT_MODEL = "src.apps.monitoring.models.MonitoringReport"  # 监控报告模型
MONITORING_TASK_MODEL = "src.apps.monitoring.models.MonitoringTask"  # 监控任务模型
MONITORING_LOG_STATUS_ENUM = "src.apps.monitoring.enums.MonitoringLogStatusEnum"  # 监控日志状态枚举
MONITORING_NOTICE_MAIN = "src.apps.system.services.notice.NoticeMain"  # 监控通知服务

# ── 4. 运行产物与文件存储 ─────────────────────────────────────────
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

MEDIA_URL = '/mango-file/'  # 本地文件访问路径前缀
MEDIA_ROOT = str(MEDIA_ROOT_DIR)  # 本地文件存储目录
STORAGES = {  # 文件存储与静态资源存储实现
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


# ── 5. Django 基础与实时服务 ─────────────────────────────────────────
USE_TZ = False  # 可选：True / False；是否启用时区感知时间

TIME_ZONE = 'Asia/Shanghai'  # 平台使用的时区

ALLOWED_HOSTS = ["*"]  # 允许访问后端的主机；* 表示不限主机

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or f'django-insecure-)7248+$v^i-e@u$=+jzwl1u(vvw0d$n5mepritgniru(&8gmu1{VERSION}'  # 平台签名密钥
LIVE_STREAM_SIGNING_KEY = os.getenv('LIVE_STREAM_SIGNING_KEY') or f'{SECRET_KEY}:ui-live-stream'  # 可选：直播凭证签名密钥；留空使用平台派生密钥
LIVE_STREAM_PREVIOUS_SIGNING_KEY = os.getenv('LIVE_STREAM_PREVIOUS_SIGNING_KEY') or ''  # 可选：轮换前的直播签名密钥；留空不启用旧密钥
REALTIME_MESSAGE_BATCH_SIZE = int(os.getenv('REALTIME_MESSAGE_BATCH_SIZE', '100'))  # 每批实时消息条数
REALTIME_MESSAGE_ACTIVE_INTERVAL = float(os.getenv('REALTIME_MESSAGE_ACTIVE_INTERVAL', '0.2'))  # 有消息时的轮询间隔，单位：秒
REALTIME_MESSAGE_IDLE_INTERVAL = float(os.getenv('REALTIME_MESSAGE_IDLE_INTERVAL', '1'))  # 无消息时的轮询间隔，单位：秒
REALTIME_MESSAGE_SEND_TIMEOUT = float(os.getenv('REALTIME_MESSAGE_SEND_TIMEOUT', '5'))  # 单次实时消息发送超时，单位：秒
REALTIME_MESSAGE_LEASE_SECONDS = int(os.getenv('REALTIME_MESSAGE_LEASE_SECONDS', '30'))  # 实时消息处理租约时长，单位：秒
REALTIME_MESSAGE_MAX_RETRIES = int(os.getenv('REALTIME_MESSAGE_MAX_RETRIES', '7'))  # 实时消息最大重试次数

# ── 6. Django 应用 ─────────────────────────────────────────
INSTALLED_APPS = [  # Django 应用列表
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
    'src.apps.monitoring',
    'src.apps.task_center',
    'src.apps.functional_test',
    'src.apps.evaluation.apps.EvaluationConfig',
    'rest_framework',  # REST 接口框架
    'corsheaders',  # 跨域
    'channels',  # 实时通信
    'minio_storage',
]

# ── 7. Django 中间件 ─────────────────────────────────────────
MIDDLEWARE = [  # 请求处理中间件，按列表顺序执行
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

# ── 8. 路由、模板与 ASGI ─────────────────────────────────────────
ROOT_URLCONF = 'src.urls'  # HTTP 路由入口

TEMPLATES = [  # 页面模板引擎与模板目录
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

ASGI_APPLICATION = 'src.asgi.application'  # ASGI 服务入口

# ── 9. MySQL 业务数据库 ─────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'src.common.database.mysql',
        'NAME': MYSQL_DB_NAME,
        'USER': MYSQL_USER,
        'PASSWORD': MYSQL_PASSWORD,
        'HOST': MYSQL_IP,
        'PORT': MYSQL_PORT,
        'OPTIONS': {
            'charset': 'utf8mb4',  # 数据库连接字符集
            'connect_timeout': 20,  # 连接超时，单位：秒
            'read_timeout': 60,  # 读取超时，单位：秒
            'write_timeout': 60,  # 写入超时，单位：秒
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES', wait_timeout=300",  # 严格写入模式；空闲连接超时 300 秒
            'isolation_level': 'READ COMMITTED',  # 事务隔离级别：读已提交
            'autocommit': True,  # 可选：True / False；是否启用驱动自动提交
        },
        'CONN_MAX_AGE': 300,  # 数据库连接复用时长，单位：秒
        'CONN_HEALTH_CHECKS': True,  # 可选：True / False；复用连接前是否检查连接可用性
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
SNOWFLAKE_BLOCK_ALLOCATOR = 'src.apps.system.services.coordination.id_sequence.reserve_snowflake_block'  # 雪花 ID 号段分配服务

# ── 10. 国际化与静态资源 ──────────────────────────────────────
LANGUAGE_CODE = 'en-us'  # Django 默认语言
USE_I18N = True  # 可选：True / False；是否启用多语言翻译

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'  # 默认自增主键类型
STATIC_URL = '/static/'  # 静态资源访问路径前缀

# ── 11. 数据库缓存 ─────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',  # Django 查询缓存表名
    }
}


# ── 12. 日志与服务标识 ─────────────────────────────────────────
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


MANGO_SERVICE_NAME = os.getenv('MANGO_SERVICE_NAME') or infer_service_name_from_command()  # 当前运行服务名称
MANGO_SERVICE_INSTANCE = os.getenv('MANGO_SERVICE_INSTANCE', socket.gethostname())  # 当前服务实例名称
ACCESS_LOG_LEVEL = 'INFO' if DJANGO_ENV == SystemEnvEnum.DEV.value else 'WARNING'  # HTTP 访问日志级别
SERVICE_LOG_DIR = LOG_ROOT_DIR / MANGO_SERVICE_NAME  # 当前服务日志目录
BUSINESS_LOG_LEVEL = normalize_log_level(  # 业务日志级别：DEBUG / INFO / WARNING / ERROR / CRITICAL
    os.getenv('MANGO_LOG_LEVEL'),
    debug_default=IS_DEBUG_LOG,
)
IS_DEBUG_LOG = BUSINESS_LOG_LEVEL == 'DEBUG'  # 是否开启业务调试日志，以最终日志级别为准
LOG_MAX_BYTES = max(1024, env_int('MANGO_LOG_MAX_BYTES', 50 * 1024 * 1024))  # 单个日志文件大小上限，单位：字节，最小 1024
LOG_BACKUP_COUNT = max(1, env_int('MANGO_LOG_BACKUP_COUNT', 10))  # 业务日志备份文件数，最小为 1
DJANGO_LOG_BACKUP_COUNT = max(1, env_int('MANGO_DJANGO_LOG_BACKUP_COUNT', 5))  # Django 日志备份文件数，最小为 1
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

# ── 13. REST 认证、权限与限流 ──────────────────────────────────
SYSTEM_ERROR_REPORTER = (  # 系统异常记录服务
    "src.apps.system.services.runtime_center.system_error_event."
    "record_system_error"
)
MODEL_CRUD_DATA_SCOPE_POLICY = "src.apps.user.services.authorization.model_crud_scope.ModelCrudDataScopePolicy"  # 数据范围校验策略
LIVE_STREAM_PERMISSION_SELECTOR = "src.apps.auto_ui.selectors.live_stream_permission.LiveStreamPermissionSelector"
MODEL_CRUD_MODULE_VALIDATOR = (  # 产品模块归属校验服务
    "src.apps.test_center.services.project.product_module.validate_crud_module_binding"
)
MODEL_CRUD_CONFIG_AUDIT_ADAPTER = (  # 用例配置变更审计适配器
    "src.apps.auto_api.services.configuration.audit_adapter.ModelCrudConfigAuditAdapter"
)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['src.apps.user.middleware.auth.JwtQueryParamsAuthentication', ],
    'DEFAULT_PERMISSION_CLASSES': ['src.apps.user.middleware.permission.MenuActionPermission', ],
    # 项目使用自定义 User + JWT，未认证请求不创建 Django auth.AnonymousUser。
    'UNAUTHENTICATED_USER': None,
    'UNAUTHENTICATED_TOKEN': None,
    'DEFAULT_THROTTLE_CLASSES': ['src.common.middleware.throttle.MangoScopedRateThrottle', ],
    'DEFAULT_THROTTLE_RATES': {  # 请求频率上限；20/min 表示每分钟 20 次
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

# ── 14. API 路由与跨域 ─────────────────────────────────────────
APPEND_SLASH = False  # 可选：True / False；是否自动补全 URL 末尾斜杠

CORS_ALLOW_CREDENTIALS = True  # 可选：True / False；跨域请求是否允许携带凭证
CORS_ORIGIN_ALLOW_ALL = True  # 可选：True / False；是否允许所有来源跨域访问
CORS_ALLOW_HEADERS = ('*',)  # 允许的跨域请求头；* 表示全部
CORS_ORIGIN_WHITELIST = (  # 允许的跨域来源，仅允许所有来源关闭时生效
    'http://localhost:5173',
)
CORS_ALLOW_METHODS = (  # 允许的跨域请求方法
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
    'VIEW',
)

# Optional environment-only HTTP overrides; Python environment configuration is preserved.
from .deployment import apply_http_environment
apply_http_environment(globals())

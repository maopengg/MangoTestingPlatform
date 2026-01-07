# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: Uvicorn启动脚本
# @Time   : 2025/12/3
# @Author :
import django
import uvicorn
import os
import sys

# os.environ["DJANGO_ENV"] = "dev"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
try:
    django.setup()
    from django.core.management import call_command

    call_command('migrate', '--noinput')
    call_command('createcachetable', 'django_cache')
except Exception as e:
    print(f"Django初始化失败: {e}")
    sys.exit(1)

os.environ.pop('DJANGO_NO_SCHEDULER', None)

# 启动 Uvicorn 服务器
host = os.environ.get("UVICORN_HOST", "0.0.0.0")
port = int(os.environ.get("UVICORN_PORT", 8000))
workers = int(os.environ.get("UVICORN_WORKERS", 1))
log_level = os.environ.get("UVICORN_LOG_LEVEL", "info")
access_log = os.environ.get("UVICORN_ACCESS_LOG", "false").lower() == "true"

uvicorn.run(
    "src.asgi:application",
    host=host,
    port=port,
    workers=workers,
    log_level=log_level,
    access_log=access_log,
    log_config=None
)

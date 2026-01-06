# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: Uvicorn启动脚本
# @Time   : 2025/12/3
# @Author : 
import uvicorn
import os
import subprocess
import sys

if __name__ == "__main__":
    os.environ["DJANGO_ENV"] = "dev"
    # os.environ["RUN_MAIN"] = "true"

    try:
        result = subprocess.run([sys.executable, "manage.py", "createcachetable", "django_cache"],
                                capture_output=True, text=True, encoding='utf-8', )
        if result.returncode != 0 and "already exists" not in result.stderr:
            print(f"创建缓存表失败: {result.stderr}")
        result = subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"],
                                capture_output=True, text=True, encoding='utf-8', )
        if result.returncode != 0:
            print(f"数据库迁移失败: {result.stderr}")
            print(f"数据库迁移输出: {result.stdout}")
    except Exception as e:
        print(f"初始化任务出现异常: {e}")

    host = os.environ.get("UVICORN_HOST", "0.0.0.0")
    port = int(os.environ.get("UVICORN_PORT", 8000))
    workers = int(os.environ.get("UVICORN_WORKERS", 1))
    log_level = os.environ.get("UVICORN_LOG_LEVEL", "info")  # 修改默认日志级别为 warning
    access_log = os.environ.get("UVICORN_ACCESS_LOG", "false").lower() == "true"  # 修改默认不显示访问日志

    uvicorn.run(
        "src.asgi:application",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
        access_log=access_log,
        log_config=None
    )
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
    # 执行Django初始化任务
    try:
        # 创建缓存表
        subprocess.run([sys.executable, "manage.py", "createcachetable", "django_cache"], 
                      check=False, capture_output=True)
        # 执行数据库迁移
        subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], 
                      check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"初始化任务失败: {e}")
        sys.exit(1)
    
    # 获取环境变量
    # os.environ["DJANGO_ENV"] = "dev"
    host = os.environ.get("UVICORN_HOST", "0.0.0.0")
    port = int(os.environ.get("UVICORN_PORT", 8000))
    workers = int(os.environ.get("UVICORN_WORKERS", 1))
    log_level = os.environ.get("UVICORN_LOG_LEVEL", "info")
    access_log = os.environ.get("UVICORN_ACCESS_LOG", "true").lower() == "true"

    # 启动Uvicorn服务器
    uvicorn.run(
        "src.asgi:application",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
        access_log=access_log
    )

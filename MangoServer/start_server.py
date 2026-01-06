# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: Uvicorn启动脚本
# @Time   : 2025/12/3
# @Author : 
import uvicorn
import os

from src.tools import project_dir

if __name__ == "__main__":
    # os.environ["DJANGO_ENV"] = "dev"
    # os.environ["RUN_MAIN"] = "true"
    project_dir.init_folder()

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

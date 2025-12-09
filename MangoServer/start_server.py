# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: Daphne启动脚本
# @Time   : 2025/12/3
# @Author : 

import os
import sys

if __name__ == "__main__":
    # 获取环境变量
    # os.environ["DJANGO_ENV"] = "dev"
    host = os.environ.get("DAPHNE_HOST", "0.0.0.0")
    port = int(os.environ.get("DAPHNE_PORT", 8000))
    log_level = os.environ.get("DAPHNE_LOG_LEVEL", "info")
    
    # 构建Daphne命令行参数
    cmd = [
        sys.executable, "-m", "daphne",
        "--bind", host,
        "--port", str(port),
        "--verbosity", "1" if log_level == "info" else "2" if log_level == "debug" else "0"
    ]
    
    # 添加应用路径
    cmd.append("src.asgi:application")
    
    # 执行Daphne服务器
    os.execv(sys.executable, cmd)
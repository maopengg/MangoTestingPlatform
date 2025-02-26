# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-26 9:51
# @Author : 毛鹏
import argparse
import asyncio

from src.consumer import SocketConsumer
from src.network import WebSocketClient
from src.network.http import HTTP
from src.settings import settings
from src.tools.log_collector import log


class LinuxLoop:

    def __init__(self):
        pass

    def set_tips_info(self, value):
        log.debug(value)


async def main(ip, port, username, password):
    settings.IP = ip
    settings.PORT = port
    settings.USERNAME = username
    settings.PASSWORD = password
    HTTP.api.public.set_host(settings.IP, settings.PORT)
    HTTP.not_auth.login(username, password)

    loop = LinuxLoop()
    s = WebSocketClient()
    s.parent = loop
    r = SocketConsumer(loop)
    await s.client_run()


# 创建参数解析器
parser = argparse.ArgumentParser(description="启动Linux服务脚本")

# 添加参数
parser.add_argument("--ip", type=str, help="服务器IP地址", required=True)
parser.add_argument("--port", type=str, help="服务器端口", required=True)
parser.add_argument("--username", type=str, help="用户名", required=True)
parser.add_argument("--password", type=str, help="密码", required=True)

# 解析参数
args = parser.parse_args()

# 调用主函数
asyncio.run(main(args.ip, args.port, args.username, args.password))

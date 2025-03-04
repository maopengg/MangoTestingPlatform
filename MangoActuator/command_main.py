# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-02-26 9:51
# @Author : 毛鹏
import argparse
import asyncio

from mangokit import Mango, EncryptionTool

from src.consumer import SocketConsumer
from src.network import WebSocketClient
from src.network.http import HTTP
from src.settings import settings
from src.tools.log_collector import log


class LinuxLoop:

    def __init__(self):
        self.loop = Mango.t()

    def set_tips_info(self, value):
        log.debug(value)


async def main(ip, port, username, password):
    settings.IP = ip
    settings.PORT = port
    settings.USERNAME = username
    settings.PASSWORD = password
    HTTP.api.public.set_host(settings.IP, settings.PORT)
    HTTP.not_auth.login(username, EncryptionTool.md5_32_small(**{'data': settings.PASSWORD}))

    loop = LinuxLoop()
    s = WebSocketClient()
    s.parent = loop
    r = SocketConsumer(loop)
    await s.client_run()


parser = argparse.ArgumentParser(description="启动Linux服务脚本")

parser.add_argument("--ip", type=str, help="服务器IP地址", required=True)
parser.add_argument("--port", type=str, help="服务器端口", required=True)
parser.add_argument("--username", type=str, help="用户名", required=True)
parser.add_argument("--password", type=str, help="密码", required=True)

args = parser.parse_args()

asyncio.run(main(args.ip, args.port, args.username, args.password))

# python command_main.py --ip= --port= --username= --password=

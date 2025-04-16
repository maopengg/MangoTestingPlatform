# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-04-16 15:07
# @Author : 毛鹏
import argparse
import asyncio

from mangokit.mangos import Mango

from src import process
from src.settings import settings


class LinuxLoop:

    def __init__(self):
        self.loop = Mango.t()

    def set_tips_info(self, value):
        print(value)


async def main():
    parser = argparse.ArgumentParser(description="接收命令行参数示例")
    parser.add_argument("--ip", required=True, help="服务器IP地址")
    parser.add_argument("--port", required=True, type=int, help="服务器端口")
    parser.add_argument("--username", required=True, help="用户名")
    parser.add_argument("--password", required=True, help="密码")
    args = parser.parse_args()
    settings.IP = args.ip
    settings.PORT = args.port
    settings.USERNAME = args.username
    settings.PASSWORD = args.password
    settings.IS_OPEN = True
    await process(LinuxLoop())
    while True:
        await asyncio.sleep(1)


asyncio.run(main())

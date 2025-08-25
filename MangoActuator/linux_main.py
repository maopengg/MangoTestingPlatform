# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-04-16 15:07
# @Author : 毛鹏
import asyncio
import json

from mangotools.mangos import Mango

from src import process
from src.enums.tools_enum import CacheKeyEnum
from src.settings import settings
from src.tools.set_config import SetConfig
from src.tools.url import is_valid_url, http_to_ws_url


class LinuxLoop:

    def __init__(self):
        self.loop = Mango.t()

    def set_tips_info(self, value):
        print(value)


async def main():
    settings.IS_OPEN = True
    await asyncio.sleep(5)
    with open('device_config.json', 'r', encoding='utf-8') as f:
        for key, value in json.load(f).items():
            if value:
                method_name = f"set_{key}"
                set_method = getattr(SetConfig, method_name, None)
                if set_method:
                    if key == CacheKeyEnum.HOST.value:
                        if is_valid_url(value):
                            SetConfig.set_host(is_valid_url(value))  # type: ignore
                            SetConfig.set_ws(http_to_ws_url(value))  # type: ignore
                        else:
                            raise Exception('请设置正确的HOST')
                    else:
                        set_method(value)
                else:
                    raise Exception(f"Warning: Method '{method_name}' not found in SetConfig")
    SetConfig.set_web_default(True)  # type: ignore
    await process(LinuxLoop(), True)
    while True:
        await asyncio.sleep(0.1)


asyncio.run(main())
# docker build -t mango_actuator .
# docker run -it mango_actuator

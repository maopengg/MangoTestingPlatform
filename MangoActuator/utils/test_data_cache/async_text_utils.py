# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-05-24 23:22
# @Author : 毛鹏
import re

from utils.test_data_cache.memory_cache import MemoryCache
from utils.test_data_cache.random_data import RandomData


class AsyncTextUtils(MemoryCache, RandomData):

    @classmethod
    async def replace_text(cls, data: str) -> str:
        """
        用来替换包含${}文本信息，通过读取缓存中的内容，完成替换（可以是任意格式的文本）
        @param data: 需要替换的文本
        @return: 返回替换完成的文本
        """
        data1 = data
        while True:
            rrr = re.findall(r"\${.*?}", data1)
            if not rrr:
                return data1
            res1 = rrr[0].replace("${", "")
            res2 = res1.replace("}", "")
            # 获取随机数据，完成替换
            if "()" in res2:
                value = RandomData().regular(res2)
                res3 = res2.replace("()", "")
                data1 = re.sub(pattern=r"\${}".format("{" + res3 + r"\(\)" + "}"), repl=value, string=data1)
            # 获取缓存数据，完成替换
            else:
                # value = Cache().read_data_from_cache(res2)
                value = await cls.get(res2)
                data1 = re.sub(pattern=r"\${}".format("{" + res2 + "}"), repl=value, string=data1)

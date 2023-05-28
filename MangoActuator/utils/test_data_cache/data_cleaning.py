# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-07 21:47
# @Author : 毛鹏
import re

from utils.test_data_cache.memory_cache import MemoryCache
from utils.test_data_cache.random_data import RandomData


class DataCleaning(RandomData, MemoryCache):

    def case_input_data(self, case_id: int, ope_value: str, key: str = None):
        """ 取出缓存或写入 """
        if key:
            key_value = str(id(self)) + str(case_id) + str(key)
            value = self.get(key_value)
        else:
            key_value = str(id(self)) + str(case_id)
            value = None
        # 缓存为空的时候进行读取数据并写入缓存
        if value is None:
            if "()" in ope_value:
                value = self.regular(ope_value)
            elif ope_value:
                value = ope_value
            if key:
                self.set(key_value, value)
        return value

    async def replace_text(self, data: str) -> str:
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
                value = self.regular(res2)
                res3 = res2.replace("()", "")
                data1 = re.sub(pattern=r"\${}".format("{" + res3 + r"\(\)" + "}"), repl=value, string=data1)
            # 获取缓存数据，完成替换
            else:
                # value = Cache().read_data_from_cache(res2)
                value = await self.get(res2)
                data1 = re.sub(pattern=r"\${}".format("{" + res2 + "}"), repl=value, string=data1)


if __name__ == '__main__':
    func = 'goods_name_int()'
    r = DataCleaning()
    print(r.case_input_data(1, '商品名称', func, 'spu_name'))

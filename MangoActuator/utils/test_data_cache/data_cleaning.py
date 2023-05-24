# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-07 21:47
# @Author : 毛鹏
from utils.test_data_cache.memory_cache import MemoryCache
from utils.test_data_cache.random_data import RandomData


class DataCleaning(RandomData, MemoryCache):

    def case_input_data(self, case_id: int, ope_value: str, key: str = None):
        """ 取出缓存 """
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


if __name__ == '__main__':
    func = 'goods_name_int()'
    r = DataCleaning()
    print(r.case_input_data(1, '商品名称', func, 'spu_name'))

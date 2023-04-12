# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-07 21:47
# @Author : 毛鹏
from utlis.random_data import RandomData
from utlis.cache.cache import CacheDB


class DataCleaning(RandomData):
    def __init__(self):
        self.ca = CacheDB()
        super().__init__()

    def case_input_data(self, case_id: str, ele_name: str, key, ope_value: str):
        """ 取出缓存 """
        key_value = case_id + ele_name + str(key)
        value = CacheDB().get(key_value)
        # 缓存为空的时候进行读取数据并写入缓存
        if value is None:
            if "()" in ope_value:
                value = self.regular(ope_value)
            elif ope_value:
                value = ope_value
            CacheDB().set(key_value, value)
        return value


if __name__ == '__main__':
    func = 'goods_name_int()'
    r = DataCleaning()
    print(r.case_input_data(1, '测1试1', 1, func, ))

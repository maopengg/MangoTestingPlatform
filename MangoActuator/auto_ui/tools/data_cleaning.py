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

    def case_input_data(self, case_id: int, ele_name: str, ope_value: str):
        """ 取出缓存 """
        value = CacheDB().get(str(case_id) + ele_name)
        # 缓存为空的时候进行读取数据并写入缓存
        if value is None:
            if "()" in ope_value:
                value = self.regular(ope_value)
            elif ope_value:
                value = ope_value
            CacheDB().set(str(case_id) + ele_name, value)
        return value


if __name__ == '__main__':
    func = 'goods_name_int()'
    r = DataCleaning()
    print(r.case_input_data(1, '测1试1', func))

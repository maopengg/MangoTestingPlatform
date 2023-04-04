# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: json数据处理类
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

import json

from PyAutoTest.utils.log_utils.log_control import ERROR


class DataFilePath:

    def get_json_value(self, json_data, key, json_list=None):
        """
        递归遍历json所有的key对应的value,通过key值获取value，并输出为list
        :param json_data:json数据
        :param key: 目标key值
        :param json_list: 用于存储获取的数据
        """
        # noinspection PyBroadException
        if json_list is None:
            json_list = []
        # noinspection PyBroadException
        try:
            # 传入数据存在则存入json_list
            if key in json_data.keys():
                json_list.append(json_data[key])
            # 传入数据不符合则对其value值进行遍历
            for value in json_data.values():
                # 传入数据的value值是字典，则直接调用自身
                if isinstance(value, dict):
                    self.get_json_value(value, key, json_list)
                # 传入数据的value值是列表或者元组，则调用get_value
                elif isinstance(value, (list, tuple)):
                    self.get_value(value, key, json_list)
            return json_list
        except BaseException as e:
            ERROR.logger.error('get_json_value function: {}'.format(e))

    def get_value(self, json_data, key, json_list):
        """
        子方法：递归遍历json所有的key对应的value,通过key值获取value，并输出为list
        @param json_data:
        @param key:
        @param json_list:
        @return:
        """
        for val in json_data:
            # 传入数据的value值是字典，则调用get_json_value
            if isinstance(val, dict):
                self.get_json_value(val, key, json_list)
            # 传入数据的value值是列表或者元组，则调用自身
            elif isinstance(val, (list, tuple)):
                self.get_value(val, key, json_list)

    def set_json_value(self, json_data, key, target_value):
        """
        递归遍历json所有的key对应的value,通过key值修改value
        仅支持单个key，且会将所有相同key对应的value值进行修改
        :param key: 目标key值
        :param json_data:json数据
        :param target_value: 目标替换值
        """
        # noinspection PyBroadException
        try:
            if isinstance(json_data, str):
                json_data = json.loads(json_data)
            # 传入数据存在则修改字典
            if key in json_data.keys():
                json_data[key] = target_value
            # 传入数据不符合则对其value值进行遍历
            for value in json_data.values():
                # 传入数据的value值是字典，则直接调用自身,将value作为字典传进来
                if isinstance(value, dict):
                    self.set_json_value(value, key, target_value)
                    value[key] = target_value
                # 传入数据的value值是列表或者元组，则调用set_value
                elif isinstance(value, (list, tuple)):
                    self.set_value(value, key, target_value)
            return json_data
        except BaseException as e:
            ERROR.logger.error('set_json_value function: {}'.format(e))

    # 子方法：递归遍历json所有的key对应的value,通过key值修改value
    def set_value(self, json_data, key, target_value):
        for val in json_data:
            # 传入数据的value值是字典，则调用get_json_value
            if isinstance(val, dict):
                self.set_json_value(val, key, target_value)
            # 传入数据的value值是列表或者元组，则调用自身
            elif isinstance(val, (list, tuple)):
                self.set_value(val, key, target_value)

    # 支持多个key，且会将所有相同key对应的value值进行修改
    def set_json_value_batch(self, json_data, *args):
        # noinspection PyBroadException
        try:
            if isinstance(args, tuple):
                if args == ():
                    return json_data
                else:
                    new_json_data = json_data
                    for arg in args:
                        for key in arg:
                            value = arg[key]
                            new_json_data = self.set_json_value(new_json_data, key, value)
                    return new_json_data
        except BaseException as e:
            ERROR.logger.error('set_json_value_batch function: {}'.format(e))

    @staticmethod
    def replace_str_value(input_data, *args):
        """
            # 批量替换包含${vars}的值,*args为字典格式数据，可以传多个参数，适用于任何格式的请求体（json、xml等)
            # 该函数没有使用self相关的变量，因此把此函数设为静态方法（暴力替换）
        """
        # noinspection PyBroadException
        try:
            # 将传入数据强转为字符串进行替换
            new_data = str(input_data)
            for arg in args:
                for i in arg:
                    target_value = arg[i]
                    replace_value = "${" + i + "}"
                    new_data = new_data.replace(replace_value, target_value)
            # 判断传进的数据如果为json格式,如果是就转换为json格式
            if isinstance(input_data, (list, dict)):
                return eval(new_data)
            return new_data
        except BaseException as e:
            ERROR.logger.error('replace_str_value function: {}'.format(e))


if __name__ == '__main__':
    r = DataFilePath()
    data = {
        "paymentType": "1",
        "id": "${order_id}",
        "tradeType": "${hahah}",
        "testPhone": "18071710220"
    }
    for k, y in data.items():
        if "${" in y:
            e = r.replace_str_value(123141, data)
            print(e)

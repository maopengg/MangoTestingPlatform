# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 随机数据封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏
import random
import string
import uuid

from faker import Faker

from src.exceptions.error_msg import ERROR_MSG_0006
from src.exceptions.tools_exception import ValueTypeError


class RandomStringData:
    """ 随机的字符类型测试数据 """
    faker = Faker(locale='zh_CN')
    goods = ["清洁霜", "洗面奶", "浴剂", "润发油", "洗发护发剂", "剃须膏", "面霜", "蜜", "化妆水", "面膜", "发乳",
             "发胶", "胭脂", "口红", "眼影", "清凉剂",
             "除臭剂", "育毛剂", "除毛剂", "染毛剂", "驱虫剂", "橄榄精华", "洗面乳", "浴液", "洗发液", "化妆水", "香水",
             "洁肤水", "卸妆液", "精华液", "原液",
             "蜜类", "护发乳", "精华乳", "润面霜", "粉底霜", "洗发膏", "遮瑕膏", "炯发膏", "精华霜", "妆前霜", "香粉",
             "爽身粉", "散粉", "洁肤粉",
             "蜜粉", "粉饼", "化妆盒", "发蜡", "卸妆油", "润肤油", "精华油", "香水", "古龙水", "面霜", "护手霜", "眼影",
             "防晒霜", "隔离霜", "腮红",
             "BB霜", "沐浴露", "洗发水", "洗面奶", "发胶", "剃须膏", "洁肤", "乳液", "面霜", "精华", "隔离", "防晒",
             "粉底", "遮瑕膏", "眉笔",
             "眉粉", "睫毛膏", "眼线笔", "眼影", "腮红", "眼霜", "隔离液", "遮瑕膏", "防晒液", "粉底液（自然）", "粉条",
             "散粉", "粉饼", "打高光的粉",
             "眼影", "眼部亮粉", "腮红", "润唇膏", "唇蜜", "唇膏", "唇笔", "唇彩", "眉笔", "眉粉", "眼线笔", "睫毛膏",
             "指甲油", "眼唇部卸妆油", "脸部卸妆油",
             "洗甲油"]

    @classmethod
    def goods_name(cls) -> str:
        """不带随机数的商品名称"""
        return cls.goods[random.randint(0, 104)]

    @classmethod
    def goods_name_int(cls):
        """带随机数的商品名称"""
        return cls.goods[random.randint(0, 104)] + str(random.randint(0, 1000))

    @classmethod
    def str_uuid(cls):
        """随机的UUID，长度36"""
        return str(uuid.uuid4())

    @classmethod
    def get_city(cls):
        """获取城市"""
        return cls.faker.city()

    @classmethod
    def get_country(cls):
        """获取国家"""
        return cls.faker.country()

    @classmethod
    def get_province(cls):
        """获取省份"""
        return cls.faker.province()

    @classmethod
    def get_pystr(cls):
        """生成英文的字符串"""
        return cls.faker.pystr()

    @classmethod
    def get_word(cls):
        """生成词语"""
        return cls.faker.word()

    @classmethod
    def get_text(cls):
        """生成一篇文章"""
        return cls.faker.text()

    @classmethod
    def get_random_string(cls, **kwargs):
        """随机字母数字,可传入数字获取指定位数字符串，默认为10"""
        try:
            data = kwargs.get('data')
            if data is None:
                data = 10
            length = int(data)
        except ValueError:
            raise ValueTypeError(*ERROR_MSG_0006)
        # 定义字符集合，包含大小写字母和数字
        characters = string.ascii_letters + string.digits
        # 使用random模块的choice函数从字符集合中随机选择字符，生成指定长度的随机字符串
        random_string = ''.join(random.choice(characters) for _ in range(length))
        return random_string


if __name__ == '__main__':
    print(RandomStringData.get_random_string(**{'data': '1g2'}))

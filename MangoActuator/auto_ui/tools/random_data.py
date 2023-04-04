# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 随机数据封装
# @Time   : 2022-11-04 22:05
# @Author : 毛鹏

import datetime
import random
import time
from datetime import date, timedelta, datetime

from faker import Faker

"""
当前类的注释必须是 “”“中间写值”“”
"""


class RandomData:

    def __init__(self):
        self.faker = Faker(locale='zh_CN')

    @staticmethod
    def time_random():
        """获取基于当前时间戳的随机五位数"""
        s = int(time.time())
        s = str(s)
        return s[5:len(s)]

    @staticmethod
    def random_0_9() -> int:
        """0-9的随机数"""
        _data = random.randint(0, 9)
        return _data

    @staticmethod
    def random_10_99() -> int:
        """10-99的随机数"""
        _data = random.randint(10, 99)
        return _data

    @staticmethod
    def random_100_999() -> int:
        """100-999的随机数"""
        _data = random.randint(100, 999)
        return _data

    @staticmethod
    def random_0_5000() -> int:
        """0-5000的随机数"""
        _data = random.randint(0, 5000)
        return _data

    @staticmethod
    def random_int():
        """小数"""
        return random.random()

    @staticmethod
    def goods_name() -> str:
        """不带随机数的商品名称"""
        goods = ["清洁霜", "洗面奶", "浴剂", "洗发护发剂", "剃须膏", "面霜", "蜜", "化妆水", "面膜", "发乳", "发胶", "胭脂", "口红", "眼影", "清凉剂", "除臭剂",
                 "育毛剂", "除毛剂", "染毛剂", "驱虫剂", "橄榄精华", "洗面乳", "浴液", "洗发液", "化妆水", "香水", "洁肤水", "卸妆液", "精华液", "原液", "蜜类",
                 "护发乳", "精华乳", "润面霜", "粉底霜", "洗发膏", "遮瑕膏", "炯发膏", "精华霜", "妆前霜", "香粉", "爽身粉", "散粉", "洁肤粉", "蜜粉", "粉饼",
                 "化妆盒", "发蜡", "卸妆油", "润肤油", "润发油", "精华油", "香水", "古龙水", "面霜", "护手霜", "眼影", "防晒霜", "隔离霜", "腮红", "BB霜",
                 "沐浴露",
                 "洗发水", "洗面奶", "发胶", "剃须膏", "洁肤", "乳液", "面霜", "精华", "隔离", "防晒", "粉底", "遮瑕膏", "眉笔", "眉粉", "睫毛膏",
                 "眼线笔", "眼影", "腮红", "眼霜", "隔离液", "遮瑕膏", "防晒液", "粉底液（自然）", "粉条", "散粉", "粉饼", "打高光的粉", "眼影", "眼部亮粉", "腮红",
                 "润唇膏", "唇蜜", "唇膏", "唇笔", "唇彩", "眉笔", "眉粉", "眼线笔", "睫毛膏", "指甲油", "眼唇部卸妆油", "脸部卸妆油", "洗甲油"]
        return goods[random.randint(0, 104)]

    @staticmethod
    def goods_name_int():
        """带随机数的商品名称"""
        goods = ["清洁霜", "洗面奶", "浴剂", "润发油", "洗发护发剂", "剃须膏", "面霜", "蜜", "化妆水", "面膜", "发乳", "发胶", "胭脂", "口红", "眼影", "清凉剂",
                 "除臭剂",
                 "育毛剂", "除毛剂", "染毛剂", "驱虫剂", "橄榄精华", "洗面乳", "浴液", "洗发液", "化妆水", "香水", "洁肤水", "卸妆液", "精华液", "原液", "蜜类",
                 "护发乳", "精华乳", "润面霜", "粉底霜", "洗发膏", "遮瑕膏", "炯发膏", "精华霜", "妆前霜", "香粉", "爽身粉", "散粉", "洁肤粉", "蜜粉", "粉饼",
                 "化妆盒", "发蜡", "卸妆油", "润肤油", "精华油", "香水", "古龙水", "面霜", "护手霜", "眼影", "防晒霜", "隔离霜", "腮红", "BB霜",
                 "沐浴露",
                 "洗发水", "洗面奶", "发胶", "剃须膏", "洁肤", "乳液", "面霜", "精华", "隔离", "防晒", "粉底", "遮瑕膏", "眉笔", "眉粉", "睫毛膏",
                 "眼线笔", "眼影", "腮红", "眼霜", "隔离液", "遮瑕膏", "防晒液", "粉底液（自然）", "粉条", "散粉", "粉饼", "打高光的粉", "眼影", "眼部亮粉", "腮红",
                 "润唇膏", "唇蜜", "唇膏", "唇笔", "唇彩", "眉笔", "眉粉", "眼线笔", "睫毛膏", "指甲油", "眼唇部卸妆油", "脸部卸妆油", "洗甲油"]
        return goods[random.randint(0, 104)] + str(random.randint(0, 1000))

    def get_phone(self) -> int:
        """随机生成手机号码"""
        phone = self.faker.phone_number()
        return phone

    def get_id_number(self) -> int:
        """随机生成身份证号码"""

        id_number = self.faker.ssn()
        return id_number

    def get_female_name(self) -> str:
        """女生姓名"""
        female_name = self.faker.name_female()
        return female_name

    def get_male_name(self) -> str:
        """男生姓名"""
        male_name = self.faker.name_male()
        return male_name

    def get_simple_profile(self):
        """获取简单的人物信息"""
        res = self.faker.simple_profile()
        return str(res)

    def get_profile(self):
        """获取带公司的人物信息"""
        res = self.faker.profile()
        return str(res)

    def get_email(self) -> str:
        """生成邮箱"""
        email = self.faker.email()
        return email

    def get_bank_card(self):
        """银行卡"""
        return self.faker.credit_card_number()

    def get_address(self):
        """带邮政编码的地址"""
        return self.faker.address()

    def get_job(self):
        """获取职称"""
        return self.faker.job()

    def get_company(self):
        """获取公司名称"""
        return self.faker.company()

    def get_city(self):
        """获取城市"""
        return self.faker.city()

    def get_country(self):
        """获取国家"""
        return self.faker.country()

    def get_province(self):
        """获取国家"""
        return self.faker.province()

    def get_pystr(self):
        """生成英文的字符串"""
        return self.faker.pystr()

    def get_word(self):
        """生成词语"""
        return self.faker.word()

    def get_text(self):
        """生成一篇文章"""
        return self.faker.text()

    def get_year(self):
        """获取年份"""
        return self.faker.year()

    def get_month(self):
        """获取月份"""
        return self.faker.month()

    def get_date(self):
        """获取日期"""
        return self.faker.date()

    def get_date_this_year(self):
        """获取当前年份:年月日"""
        return self.faker.date_this_year()

    def get_date_time(self):
        """获取：年月日时分秒"""
        return self.faker.date_time()

    def get_future_datetime(self):
        """获取未来时间，年月日 时分秒"""
        return self.faker.future_datetime()

    def get_future_date(self):
        """获取未来时间 年月日"""
        return self.faker.future_date()

    @classmethod
    def get_time(cls) -> str:
        """计算当前时间"""
        now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return now_time

    @classmethod
    def today_date(cls):
        """获取今日0点整时间"""

        _today = date.today().strftime("%Y-%m-%d") + " 00:00:00"
        return str(_today)

    @classmethod
    def time_after_week(cls):
        """获取一周后12点整的时间"""

        _time_after_week = (date.today() + timedelta(days=+6)).strftime("%Y-%m-%d") + " 00:00:00"
        return _time_after_week

    @classmethod
    def time_after_month(cls):
        """获取30天后的12点整时间"""

        _time_after_week = (date.today() + timedelta(days=+30)).strftime("%Y-%m-%d") + " 00:00:00"
        return _time_after_week


def regular(func):
    func = func.strip()
    func = func.replace("()", "")
    return getattr(RandomData(), func)()


def get_methods():
    func = []
    for k, y in RandomData.__dict__.items():
        if k not in "__module____init____dict____weakref____doc__":
            dic = {
                'label': k + '()',
                'value': y.__doc__
            }
            func.append(dic)
    return func


if __name__ == '__main__':
    # data = "get_female_name()"
    # b = regular(data)
    # print(b)
    print(get_methods())

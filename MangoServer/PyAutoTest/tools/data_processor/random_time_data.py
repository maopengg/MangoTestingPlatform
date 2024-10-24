# -*- coding: utf-8 -*-
# @Project: 芒果测试平台# @Description:
# @Time   : 2023-03-07 8:24
# @Author : 毛鹏

from datetime import date, timedelta, datetime

import time
from faker import Faker


class RandomTimeData:
    """ 随机时间类型测试数据 """
    faker = Faker(locale='zh_CN')

    @classmethod
    def now_time(cls) -> str:
        """获取当前年月日时分秒"""
        localtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        return localtime

    @classmethod
    def now_time_day(cls) -> str:
        """获取当前年月日"""
        localtime = time.strftime("%Y-%m-%d", time.localtime())
        return localtime

    @classmethod
    def get_time_for_min(cls, **kwargs) -> int:
        """获取几分钟后的时间戳 参数：minute"""
        minute = kwargs.get('data')
        if minute is None:
            minute = 1
        return int(time.time() + 60 * int(minute)) * 1000

    @classmethod
    def get_now_time(cls) -> int:
        """获取当前时间戳整形"""
        return int(time.time()) * 1000

    @classmethod
    def get_year(cls):
        """获取随机年份"""
        return cls.faker.year()

    @classmethod
    def get_month(cls):
        """获取随机月份"""
        return cls.faker.month()

    @classmethod
    def get_date(cls):
        """获取随机日期"""
        return cls.faker.date()

    @classmethod
    def get_date_this_year(cls):
        """获取随机年月日"""
        return cls.faker.date_this_year()

    @classmethod
    def get_date_time(cls):
        """获取随机年月日时分秒"""
        return cls.faker.date_time()

    @classmethod
    def get_before_time(cls, **kwargs):
        """获取当今日之前的日期 参数：days"""
        days = kwargs.get('data')
        if days is None:
            days = 1
        yesterday = datetime.now() - timedelta(days=int(days))
        yesterday_str = yesterday.strftime('%Y-%m-%d')
        return yesterday_str

    @classmethod
    def get_future_datetime(cls):
        """获取未来的随机年月日时分秒"""
        return cls.faker.future_datetime()

    @classmethod
    def get_future_date(cls):
        """获取未来的随机年月日"""
        return cls.faker.future_date()

    @classmethod
    def get_deta_hms(cls):
        """获取时分秒"""
        now_time = datetime.now().strftime("%H%M%S")
        return now_time

    @classmethod
    def get_time(cls) -> str:
        """获取当前年月日时分秒"""
        now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return now_time

    @classmethod
    def get_time_by_type(cls, **kwargs) -> str:
        """获取当前年月日时分秒并返回指定格式"""
        types = str(kwargs.get('data'))
        data_type = ''
        if types is None or types == '0':
            data_type = '%Y-%m-%d %H:%M:%S'
        elif types == '1':
            data_type = '%Y-%m-%d %H:%M'
        elif types == '2':
            data_type = '%Y-%m-%d %H'
        elif types == '3':
            data_type = '%Y-%m-%d'
        elif types == '4':
            data_type = '%Y-%m'
        elif types == '5':
            data_type = '%Y'
        now_time = datetime.now().strftime(data_type)
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

    @classmethod
    def time_day_reduce(cls, **kwargs) -> int:
        """获取今日日期的数字，传参可以减N"""
        types = kwargs.get('data')
        today = datetime.today()
        if types:
            return today.day - int(types)
        else:
            return today.day

    @classmethod
    def time_day_plus(cls, **kwargs) -> int:
        """获取今日日期的数字，传参可以加N"""
        types = kwargs.get('data')
        today = datetime.today()
        if types:
            return today.day + int(types)
        else:
            return today.day


if __name__ == '__main__':
    print(RandomTimeData.time_day(**{'data': 2}))

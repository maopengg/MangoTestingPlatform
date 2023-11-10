# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description:
# @Time   : 2023-03-07 8:24
# @Author : 毛鹏

from datetime import date, timedelta, datetime

import time
from faker import Faker


class RandomTimeData:
    """ 随机时间类型测试数据 """
    faker = Faker(locale='zh_CN')

    # @classmethod
    # def timestamp_conversion(cls, time_str: str) -> int:
    #     """将年月日时分秒转换成时间戳"""
    #
    #     try:
    #         datetime_format = datetime.strptime(str(time_str), "%Y-%m-%d %H:%M:%S")
    #         timestamp = int(
    #             time.mktime(datetime_format.timetuple()) * 1000.0
    #             + datetime_format.microsecond / 1000.0
    #         )
    #         return timestamp
    #     except ValueError as exc:
    #         raise ValueError('日期格式错误, 需要传入得格式为 "%Y-%m-%d %H:%M:%S" ') from exc
    #
    # @classmethod
    # def time_conversion(cls, time_num: int) -> str:
    #     """时间戳转换成年月日时分秒"""
    #     if isinstance(time_num, int):
    #         time_stamp = float(time_num / 1000)
    #         time_array = time.localtime(time_stamp)
    #         other_style_time = time.strftime("%Y-%m-%d %H:%M:%S", time_array)
    #         return other_style_time

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
    def get_time_for_min(cls, minute: int = 1) -> int:
        """获取几分钟后的时间戳 参数：分钟"""
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
    def get_before_time(cls, days: int = 1):
        """获取当今日之前的日期 参数：前几天"""
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


if __name__ == '__main__':
    print(RandomTimeData.get_time())

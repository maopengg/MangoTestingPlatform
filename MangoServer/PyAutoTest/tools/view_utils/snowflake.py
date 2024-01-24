# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-10-26 11:41
# @Author : 毛鹏
import uuid

import time


class Snowflake:
    worker_id = 0
    datacenter_id = 0
    sequence = 0
    last_timestamp = -1

    @classmethod
    def snowflake_id(cls):
        timestamp = int(time.time() * 1000)

        if timestamp < cls.last_timestamp:
            raise Exception("Clock moved backwards. Refusing to generate id")

        if timestamp == cls.last_timestamp:
            cls.sequence = (cls.sequence + 1) & 4095
            if cls.sequence == 0:
                timestamp = cls.wait_next_millis(cls.last_timestamp)
        else:
            cls.sequence = 0

        cls.last_timestamp = timestamp

        unique_id = ((timestamp - 1288834974657) << 22) | (cls.datacenter_id << 17) | (
                cls.worker_id << 12) | cls.sequence
        return unique_id

    @classmethod
    def wait_next_millis(cls, last_timestamp):
        timestamp = int(time.time() * 1000)
        while timestamp <= last_timestamp:
            timestamp = int(time.time() * 1000)
        return timestamp

    @classmethod
    def generate_id(cls):
        unique_id = uuid.uuid4()
        unique_number = str(unique_id.int)[-12:].zfill(12).replace('0', '1')
        return unique_number


if __name__ == '__main__':
    for i in range(10000000):
        print(Snowflake.snowflake_id())

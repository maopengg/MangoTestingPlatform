# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-10-26 11:41
# @Author : 毛鹏
import uuid

import time


class Snowflake:
    def __init__(self, datacenter_id=1, worker_id=1):
        self.datacenter_id = datacenter_id
        self.worker_id = worker_id
        self.sequence = 0
        self.last_timestamp = -1

    def generate_unique_number(self):
        timestamp = int(time.time() * 1000)
        if timestamp < self.last_timestamp:
            raise Exception("Clock moved backwards. Refusing to generate ID.")
        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & 4095
            if self.sequence == 0:
                timestamp = self.wait_next_millis(self.last_timestamp)
        else:
            self.sequence = 0
        self.last_timestamp = timestamp
        _int = ((timestamp - 1609430400000) << 22) | (self.datacenter_id << 17) | (self.worker_id << 12) | self.sequence
        return int(str(_int)[-12:])

    def wait_next_millis(self, last_timestamp):
        timestamp = int(time.time() * 1000)
        while timestamp <= last_timestamp:
            timestamp = int(time.time() * 1000)
        return timestamp

    @classmethod
    def generate_id(cls):
        unique_id = uuid.uuid4()
        unique_number = int(str(unique_id.int)[-12:])
        return unique_number


if __name__ == '__main__':
    for i in range(10000):
        print(Snowflake.generate_id())

# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-05 12:39
# @Author : 毛鹏
import os
import sys


class NewLog:
    def __init__(self):
        file = ['log', 'failure_screenshot', 'cache']
        current_dir1 = os.path.abspath(__file__)
        current_dir1 = os.path.dirname(os.path.dirname(current_dir1))
        current_dir2 = os.path.dirname(sys.executable)
        if 'python.exe' not in sys.executable:
            current_dir1 = current_dir2
        logs_dir = os.path.join(current_dir1, "logs")
        self.logs_dir = logs_dir
        test_dir = os.path.join(current_dir1, "tests")
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            for i in file:
                subdirectory = os.path.join(logs_dir, i)
                if not os.path.exists(subdirectory):
                    os.makedirs(subdirectory)
        self.log_file = os.path.join(logs_dir, "log")
        self.failure_screenshot_file = os.path.join(logs_dir, "failure_screenshot")
        self.cache_file = os.path.join(logs_dir, 'cache')
        self.test_file = os.path.join(logs_dir, 'tests')

    @classmethod
    def get_log(cls):
        return cls().log_file

    @classmethod
    def get_log_screenshot(cls):
        return cls().failure_screenshot_file

    @classmethod
    def get_cache(cls):
        return cls().cache_file

    @classmethod
    def get_tests(cls):
        return cls().test_file


if __name__ == '__main__':
    NewLog()

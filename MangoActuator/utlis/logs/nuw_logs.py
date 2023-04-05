# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-05 12:39
# @Author : 毛鹏
import os

file = ['log', 'failure_screenshot']
current_dir = os.path.dirname(os.path.abspath(__file__))
current_dir = os.path.dirname(os.path.dirname(current_dir))
logs_dir = os.path.join(current_dir, "logs")


def nuw_dir():
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    for i in file:
        subdirectory = os.path.join(logs_dir, i)
        if not os.path.exists(subdirectory):
            os.makedirs(subdirectory)


def get_log():
    return os.path.join(logs_dir, "log")


def get_log_screenshot():
    return os.path.join(logs_dir, "failure_screenshot")


if __name__ == '__main__':
    print(get_log())

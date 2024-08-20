# -*- coding: utf-8 -*-
# @Project: MangoActuator
# @Description: 
# @Time   : 2023-08-03 16:54
# @Author : 毛鹏
import multiprocessing

import psutil


class Perf:
    def __init__(self):
        cpu_count = psutil.cpu_count(logical=False)
        self.pool = multiprocessing.Pool(cpu_count - 1)

    def mian(self):
        pass

# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-03-03 22:03
# @Author : 毛鹏

from concurrent.futures import ThreadPoolExecutor
from queue import Queue


class FlowConsumer:
    queue = Queue()
    max_tasks = 2

    executor = ThreadPoolExecutor(max_workers=max_tasks)
    running = True

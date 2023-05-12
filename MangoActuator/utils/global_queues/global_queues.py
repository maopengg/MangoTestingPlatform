# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023/5/12 14:59
# @Author : 毛鹏
import multiprocessing


def process_queue(q):
    while True:
        data = q.get()
        if data is None:
            break
        print(data)


def create_queue_in_new_process():
    q = multiprocessing.Queue()
    p = multiprocessing.Process(target=process_queue, args=(q,))
    p.start()
    q.put("Hello, world!")
    q.put(None)
    p.join()


if __name__ == '__main__':
    create_queue_in_new_process()
    q = multiprocessing.Queue()
    q.put("Hello from main thread!")
    q.put(None)
    process_queue(q)

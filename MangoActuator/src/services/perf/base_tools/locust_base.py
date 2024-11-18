# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-05-08 10:55
# @Author : 毛鹏
from locust import FastHttpUser
from locust import task
from locust.env import Environment
from locust.log import setup_logging
from locust.runners import WorkerRunner

# 设置日志级别
setup_logging("INFO")


class MyUser(FastHttpUser):
    host = "http://localhost:8000"

    @task
    def login(self):
        self.client.post('/login', {
            'username': '17798339533',
            'password': '123456'
        })


# 创建 Environment 对象
env = Environment(user_classes=[MyUser])

# 创建 Worker 运行器
worker_runner: WorkerRunner = env.create_worker_runner("127.0.0.1", 5557)
worker_runner.shape_worker()
user_classes_count = {
    "MyUser": 10,
}

# 开始测试
worker_runner.start_worker(user_classes_count)

# 等待测试结束
worker_runner.greenlet.join()

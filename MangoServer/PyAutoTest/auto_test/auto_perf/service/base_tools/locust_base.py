# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-05-08 10:55
# @Author : 毛鹏
from locust import task
from locust.contrib.fasthttp import FastHttpUser
from locust.log import setup_logging

setup_logging("INFO")


class PerfScript(FastHttpUser):
    host = "http://localhost:8000"

    @task
    def login(self):
        self.client.post('/login', {
            'username': '17798339533',
            'password': '123456'
        })

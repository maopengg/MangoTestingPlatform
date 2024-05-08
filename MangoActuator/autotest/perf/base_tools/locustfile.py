# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description:
# @Time   : 2024-05-08 10:55
# @Author : 毛鹏

import gevent
from locust import HttpUser, events, task
from locust.env import Environment
from locust.log import setup_logging
from locust.stats import stats_history, stats_printer

setup_logging("INFO")


class MyUser(HttpUser):
    host = "http://127.0.0.1:8000"


    @task
    def t(self):
        self.client.post('/login', {
            'username': '17798339533',
            'password': '123456'
        })

# setup Environment and Runner
env = Environment(user_classes=[MyUser], events=events)
runner = env.create_local_runner()

# start a WebUI instance
web_ui = env.create_web_ui("127.0.0.1", 8089)

# execute init event handlers (only really needed if you have registered any)
env.events.init.fire(environment=env, runner=runner, web_ui=web_ui)

# start a greenlet that periodically outputs the current stats
gevent.spawn(stats_printer(env.stats))

# start a greenlet that save current stats to history
gevent.spawn(stats_history, env.runner)

# start the test
runner.start(1, spawn_rate=10)

# in 30 seconds stop the runner
gevent.spawn_later(30, runner.quit)

# wait for the greenlets
runner.greenlet.join()

# stop the web server for good measures
web_ui.stop()
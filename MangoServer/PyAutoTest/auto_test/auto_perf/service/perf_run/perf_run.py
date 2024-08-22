# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-05-08 17:12
# @Author : 毛鹏
#
#
# import gevent
# from locust import events
# from locust.env import Environment
# from locust.stats import stats_history, stats_printer
#
# from PyAutoTest.auto_test.auto_perf.service_conn.bases.locust_base import PerfScript
#
#
# def perf_run():
#     # setup Environment and Runner
#     env = Environment(user_classes=[PerfScript], events=events)
#     runner = env.create_master_runner()
#     # start a WebUI instance
#     web_ui = env.create_web_ui("0.0.0.0", 8089)
#     # execute init event handlers (only really needed if you have registered any)
#     env.events.init.fire(environment=env, runner=runner, web_ui=web_ui)
#     # start a greenlet that periodically outputs the current stats
#     gevent.spawn(stats_printer(env.stats))
#     # start a greenlet that save current stats to history
#     gevent.spawn(stats_history, env.runner)
#     # start the test
#     runner.start(1, spawn_rate=10)
#     # in 60 seconds stop the runner
#     gevent.spawn_later(60, runner.quit)
#     # wait for the greenlets
#     runner.greenlet.join()
#     # stop the web server for good measures
#     web_ui.stop()

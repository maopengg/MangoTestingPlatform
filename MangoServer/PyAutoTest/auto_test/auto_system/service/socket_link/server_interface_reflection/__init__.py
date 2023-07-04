# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-04-29 11:19
# @Author : 毛鹏
import logging

from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.api_consumer import APIConsumer
from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.perf_consumer import PerfConsumer
from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.system_consumer import \
    SystemConsumer
from PyAutoTest.auto_test.auto_system.service.socket_link.server_interface_reflection.ui_consumer import UIConsumer

log = logging.getLogger('system')


class ServerInterfaceReflection(APIConsumer, SystemConsumer, UIConsumer, PerfConsumer):

    def start_up(self, func, *args, **kwargs):
        getattr(self, func)(*args, **kwargs)

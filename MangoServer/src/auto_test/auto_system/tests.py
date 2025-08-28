# Create your tests here.
import json

from django.test import TestCase

from src.auto_test.auto_system.service.socket_link.server_interface_reflection.ui import UIConsumer


class YourTestClass(TestCase):

    def test_your_function(self):
        with open(r'D:\GitCode\uitest\MangoServer\test.json') as f:
            data = json.load(f)
            UIConsumer().u_case_batch_result(data)

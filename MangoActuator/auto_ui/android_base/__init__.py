# from typing import Optional
#
# from uiautomator2 import Device
# from wda import Client, AlertAction, BaseClient
from auto_ui.android_base.assertion import UiautomatorAssertion
from auto_ui.android_base.device import UiautomatorEquipmentDevice
from auto_ui.android_base.element import UiautomatorElementOperation
from auto_ui.android_base.page import UiautomatorPage


class DriverMerge(UiautomatorAssertion,
                  UiautomatorEquipmentDevice,
                  UiautomatorElementOperation,
                  UiautomatorPage):
    pass


# from utils.logs.log_control import ERROR
#
#
# class AndroidDriver(Device):
#     """安卓设备"""
#
#     def __call__(self, **kwargs):
#         if len(kwargs) == 1 and "xpath" in kwargs:
#             return self.xpath(kwargs["xpath"])
#         else:
#             return Device.__call__(self, **kwargs)
#
#     def find_element(self, **kwargs):
#         if len(kwargs) == 1 and "xpath" in kwargs:
#             return self.xpath(kwargs["xpath"])
#         else:
#             return Device.__call__(self, **kwargs)
#
#
# class AppleDevice(Client):
#     """苹果设备"""
#
#     def session(self,
#                 bundle_id=None,
#                 arguments: Optional[list] = None,
#                 environment: Optional[dict] = None,
#                 alert_action: Optional[AlertAction] = None):
#         setattr(Client, 'find_element', AppleDevice.find_element)
#         socket_client = BaseClient.session(self, bundle_id, arguments, environment, alert_action)
#         return socket_client
#
#     def find_element(self, **kwargs):
#         return BaseClient.__call__(self, **kwargs)
#
#
# def connect_device(system: str, url: str):
#     if system.lower() == "android":
#         return AndroidDriver(url)
#     else:
#         return AppleDevice(url)
#
#
# class Operation:
#     def __init__(self, device):
#         self.device = device
#         self.print = print
#
#     def find_element(self, ele):
#         """查找单个元素"""
#         try:
#             element = self.device.find_element(**ele)
#             ERROR.logger.error("定位元素: %s" % str(ele))
#             return element
#         except Exception as e:
#             ERROR.logger.error("定位元素出错: %s" % str(ele))
#             raise e
#

class ElementNotFoundError(Exception):
    """元素获取失败"""


class ElementNotDisappearError(Exception):
    """元素消失失败"""
#
#
# if __name__ == '__main__':
#     url = "http://localhost:4723/wd/hub"
#     system = "android"  # 设备系统类型
#     device = connect_device(system, url)  # 连接设备
#     op = Operation(device)  # 实例化操作类
#     op.find_element('111')

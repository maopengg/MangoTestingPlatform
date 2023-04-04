# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2023-03-11 17:25
# @Author : 毛鹏
import time

import uiautomator2

"""
python -m uiautomator2 init
python -m weditor

"""


class AndroidBase:
    """app基类"""

    def __init__(self, equipment, package):
        self.app = uiautomator2.connect(equipment)
        self.package = package
        self.app.implicitly_wait(10)

    def percentage_click(self, x: float or int, y: float or int):
        self.app.click(x=x, y=y)

    def find_element_by_text(self, text):
        """
        通过元素的text属性查找元素
        :param text: 元素的text属性
        :return: 元素对象
        """
        return self.app(text=text)

    def find_element_by_desc(self, desc):
        """
        通过元素的desc属性查找元素
        :param desc: 元素的desc属性
        :return: 元素对象
        """
        return self.app(description=desc)

    def find_element_by_id(self, res_id):
        """
        通过元素的resource-id属性查找元素
        :param res_id: 元素的resource-id属性
        :return: 元素对象
        """
        return self.app(resourceId=res_id)

    def find_element_by_class_name(self, class_name):
        """
        通过元素的class属性查找元素
        :param class_name: 元素的class属性
        :return: 元素对象
        """
        return self.app(className=class_name)

    def find_element_by_xpath(self, xpath):
        """
        通过元素的xpath查找元素
        :param xpath: 元素的xpath
        :return: 元素对象
        """
        return self.app.xpath(xpath)

    def find_element_by_selector(self, selector):
        """
        通过元素的selector查找元素
        :param selector: 元素的selector
        :return: 元素对象
        """
        return self.app(selector=selector)

    def launch_app(self):
        """
        启动应用程序
        """
        self.app.app_start(self.package)

    def coordinate_click(self, x: float or int, y: float or int):
        """
        点击
        :param x: x坐标
        :param y: y坐标
        """
        self.app.click(x=x, y=y)

    def double_click(self, x: float or int, y: float or int):
        """
        双击
        :param x: x坐标
        :param y: y坐标
        """
        self.app.double_click(x=x, y=y)

    def swipe(self, fx: float or int, fy: float or int, tx: float or int, ty: float or int):
        """
        滑动
        :param fx: 起始x坐标
        :param fy: 起始y坐标
        :param tx: 目标x坐标
        :param ty: 目标y坐标
        """
        self.app.swipe(fx=fx, fy=fy, tx=tx, ty=ty)

    def long_click(self, x: float or int, y: float or int, duration: float or int = 1.0):
        """
        长按
        :param x: x坐标
        :param y: y坐标
        :param duration: 长按时间，默认为1s
        """
        self.app.long_click(x=x, y=y, duration=duration)

    def press(self, key: str):
        """
        按键
        :param key: 键名，如"home","back","enter"等
        """
        self.app.press(key)

    def text(self, content: str):
        """
        输入文本
        :param content: 要输入的文本内容
        """
        self.app.send_keys(content)

    def screenshot(self, filename: str):
        """
        截图
        :param filename: 保存截图的文件名
        """
        self.app.screenshot(filename)

    def wait(self, timeout: float or int = 10):
        """
        显式等待
        :param timeout: 超时时间，默认为10s
        """
        self.app.wait_timeout = timeout

    def exists(self, target: str, timeout: float or int = 3):
        """
        判断元素是否存在
        :param target: 元素的text或description属性
        :param timeout: 超时时间，默认为3s
        :return: 如果元素存在，返回True；否则返回False
        """
        try:
            self.app(text=target).wait(timeout=timeout)
            return True
        except:
            return False

    def get_text(self, target: str):
        """
        获取元素的文本内容
        :param target: 元素的text或description属性
        :return: 元素的文本内容
        """
        return self.app(text=target).get_text()

    def __del__(self):
        """
        停止应用程序运行
        """
        self.app.app_stop(self.package)


if __name__ == '__main__':
    r = AndroidBase('8796a033', 'com.tencent.mm')
    r.launch_app()
    r.percentage_click(0.634, 0.963)
    time.sleep(1)
    r.percentage_click(0.192, 0.312)
    time.sleep(1)

    r.percentage_click(0.162, 0.251)
    time.sleep(1)

    r.percentage_click(0.903, 0.945)

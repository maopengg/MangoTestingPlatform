# -*- coding: utf-8 -*-
# @Project: auto_test
# @Description: 
# @Time   : 2024-08-21 10:28
# @Author : 毛鹏
import time
from PySide6.QtWidgets import QApplication, QPushButton, QWidget, QHBoxLayout
from playwright.sync_api import sync_playwright


class PushButton(QWidget):

    def __init__(self, ):
        super().__init__()
        self.setWindowTitle('Push Button')
        click = QPushButton()
        click.setText('点击事件')
        click.clicked.connect(self.click)
        layout = QHBoxLayout(self)
        layout.addWidget(click)
    def click(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=False
            )
            context = browser.new_context(record_video_dir=r'D:\GitCode\MangoTestingPlatform\MangoActuator\logs\videos')

            page = context.new_page()
            page.goto("https://www.yuque.com/login?register_with_scene=true&defaultType=org&register_from=official_website_top_button")
            element = page.locator('xpath=//span[@id="nc_1_n1z"]')
            # 获取元素的位置
            box = element.bounding_box()

            if box:  # 检查元素是否可见
                # 执行拖动操作
                page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)  # 移动到元素中心
                page.mouse.down()  # 按下鼠标
                page.mouse.move(box['x'] + box['width'] / 2 + 100, box['y'] + box['height'] / 2)  # 向右移动 100 像素
                page.mouse.up()  # 松开鼠标
            time.sleep(10)

            page.close()
            context.close()
            browser.close()

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    window = PushButton()
    window.show()
    app.exec()

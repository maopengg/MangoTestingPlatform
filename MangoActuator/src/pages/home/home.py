# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2024-08-27 14:45
# @Author : 毛鹏
import platform
from collections import deque

import psutil
from PySide6.QtCore import Signal, QTimer, QDateTime
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QSizePolicy
from mangoautomation.enums import BrowserTypeEnum
from mangoui.widgets.container import MangoCard
from mangoui.widgets.display import MangoLabel
from mangoui.widgets.input import MangoTextEdit
from mangoui.widgets.layout import MangoHBoxLayout, MangoVBoxLayout, MangoFormLayout
from mangoui.widgets.window import MangoWidget, MangoDialog

from src.settings.settings import IS_WINDOW
from src.tools import project_dir
from src.tools.set_config import SetConfig

fixed_list = deque(maxlen=100)


class HomePage(MangoWidget):
    real_time = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.page = 1
        self.page_size = 10
        self.parent = parent
        self.real_time.connect(self.update_message)
        self._layout = MangoHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addLayout(self._layout)
        self.left_layout = MangoVBoxLayout()
        self._layout.addLayout(self.left_layout, 6)
        self.right_layout = MangoVBoxLayout()
        self._layout.addLayout(self.right_layout, 4)

        # 左边
        self.run_status_layout = MangoFormLayout()
        self.run_status_card = MangoCard(self.run_status_layout, '执行状态')
        self.run_status = MangoLabel('🟢 接收中', self)
        self.run_status_layout.addRow('接收状态', self.run_status)
        self.run_status_case_name = MangoLabel('-', self)
        self.run_status_layout.addRow('当前用例', self.run_status_case_name)
        self.run_status_layout.addRow('今日执行', MangoLabel('x 次', self))
        self.left_layout.addWidget(self.run_status_card, 2)

        self.current_task_layout = MangoFormLayout()
        self.current_task_card = MangoCard(self.current_task_layout, '当前任务')
        self.current_task_layout.addRow('测试套ID', MangoLabel('1232312', self))
        self.current_task_layout.addRow('用例名称', MangoLabel('2025-01-01 00:00:00', self))
        self.current_task_layout.addRow('开始时间', MangoLabel('2025-01-01 00:00:00', self))

        self.historical_statistics_layout = MangoFormLayout()
        self.historical_statistics_card = MangoCard(self.historical_statistics_layout, '历史统计')
        self.historical_statistics_layout.addRow('成功率', MangoLabel('98.12%', self))
        self.historical_statistics_layout.addRow('平均用时', MangoLabel('45s', self))
        self.historical_statistics_layout.addRow('峰值用例', MangoLabel('32', self))

        # self.run_status_layout_h = MangoHBoxLayout()
        # self.run_status_layout_h.addWidget(self.current_task_card)
        # self.run_status_layout_h.addWidget(self.historical_statistics_card)
        # self.left_layout.addLayout(self.run_status_layout_h)

        self.log_layout = MangoHBoxLayout()
        self.log_card = MangoCard(self.log_layout, '实时日志')
        self.log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_text_edit = MangoTextEdit('')
        self.log_text_edit.setReadOnly(True)

        self.log_layout.addWidget(self.log_text_edit)
        self.left_layout.addWidget(self.log_card, 8)

        # 右边
        self.system_resource_layout = MangoFormLayout()
        self.system_resource_card = MangoCard(self.system_resource_layout, '系统资源')
        self.cpu = MangoLabel('-', self)
        self.memory = MangoLabel('-', self)
        self.system_resource_layout.addRow('已用CPU', self.cpu)
        self.system_resource_layout.addRow('已用内存', self.memory)
        self.system_resource_layout.addRow('网络链接', MangoLabel('🟢 正常', self))

        self.env_info_layout = MangoFormLayout()
        self.env_info_card = MangoCard(self.env_info_layout, '环境信息')
        self.python = MangoLabel(f'-', self)
        self.env_info_layout.addRow('python', self.python)
        self.env_info_layout.addRow('pytest', MangoLabel('8.3.3', self))
        self.env_info_layout.addRow('浏览器',
                                    MangoLabel(f'{BrowserTypeEnum.get_value(SetConfig.get_web_type())}', self))

        self.system_layout = MangoHBoxLayout()
        self.system_layout.addWidget(self.system_resource_card, 5)
        self.system_layout.addWidget(self.env_info_card, 5)
        self.right_layout.addLayout(self.system_layout, 2)

        self.server_config_layout = MangoFormLayout()
        self.server_config_card = MangoCard(self.server_config_layout, '环境信息')
        self.server_config_layout.addRow('服务地址', MangoLabel(f'{SetConfig.get_host()}', self))
        self.server_config_layout.addRow('WS链接', MangoLabel(f'{SetConfig.get_ws()}', self))
        self.link = MangoLabel('🟢 正常', self)
        self.server_config_layout.addRow('链接状态', self.link)
        self.right_layout.addWidget(self.server_config_card, 2)

        self.file_layout = MangoFormLayout()
        self.file_card = MangoCard(self.file_layout, '文件路径（右键路径可复制）')

        # 创建固定宽度的标签
        cache_label = MangoLabel(f'{project_dir.cache()}', self)
        log_label = MangoLabel(f'{project_dir.logs()}', self)
        screenshot_label = MangoLabel(f'{project_dir.screenshot()}', self)
        video_label = MangoLabel(f'{project_dir.videos()}', self)
        download_label = MangoLabel(f'{project_dir.download()}', self)
        upload_label = MangoLabel(f'{project_dir.upload()}', self)
        allure_label = MangoLabel(f'{project_dir.allure()}', self)
        self.file_layout.addRow('缓存目录', cache_label)
        self.file_layout.addRow('日志目录', log_label)
        self.file_layout.addRow('截图目录', screenshot_label)
        self.file_layout.addRow('视频目录', video_label)
        self.file_layout.addRow('下载目录', download_label)
        self.file_layout.addRow('上传目录', upload_label)
        self.file_layout.addRow('allure', allure_label)

        self.right_layout.addWidget(self.file_card, 6)

        if IS_WINDOW:
            self.mango_dialog = MangoDialog('添加作者微信进芒果测试平台交流群', (260, 340))
            label = MangoLabel()
            pixmap = QPixmap(":/picture/author.png")  # 替换为你的图片路径
            label.setPixmap(pixmap)
            label.setScaledContents(True)  # 允许缩放
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # type: ignore
            self.mango_dialog.layout.addWidget(label)

    def load_page_data(self, ):
        self.python.setText(platform.python_version())
        if fixed_list:
            for i in fixed_list:
                self.log_text_edit.append(i)

        cpu_percent = psutil.cpu_percent(interval=1)
        memory_info = psutil.virtual_memory()
        memory_percent = memory_info.percent
        self.cpu.setText(f'{cpu_percent}%')
        self.memory.setText(f'{memory_percent}%')
        if IS_WINDOW:
            QTimer.singleShot(500, self.open_dialog)

    def open_dialog(self):
        self.mango_dialog.exec()

    def update_message(self, text):
        if text:
            fixed_list.append(text)
            current_time = QDateTime.currentDateTime().toString("HH:mm:ss")
            self.log_text_edit.append(f'{current_time} - {text}')

    def set_link(self, value):
        if int(value):
            self.link.setText('🟢 正常')
            self.run_status.setText('🟢 接收中')
        else:
            self.link.setText('🔴 异常')
            self.run_status.setText('🔴 等待链接中')

    def set_case_name(self, value):
        self.run_status_case_name.setText(value)

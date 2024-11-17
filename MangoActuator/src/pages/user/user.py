import json
from typing import Optional

from mango_ui import *

from src.enums.system_enum import CacheDataKey2Enum, EnvironmentEnum
from src.enums.tools_enum import ClientTypeEnum
from src.models.user_model import UserModel
from src.network import HTTP
from src.network.web_socket.socket_api_enum import ToolsSocketEnum
from src.tools.assertion import Assertion
from src.tools.get_class_methods import GetClassMethod
from src.tools.methods import Methods


class UserPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = MangoVBoxLayout()

        self.user_info: Optional[UserModel | None] = None
        self.setLayout(self.layout)

    def show_data(self):
        self.user_info = HTTP.get_userinfo(UserModel().id)
        card_layout1 = MangoFormLayout()
        card_widget = MangoCard(card_layout1, '基本信息')
        card_layout1.addRow('头像', MangoLabel('-'))
        card_layout1.addRow('昵称', MangoLabel(self.user_info.nickname))

        card_layout2 = MangoFormLayout()
        card_widget2 = MangoCard(card_layout2, '账户信息')
        card_layout2.addRow('账号：', MangoLabel(self.user_info.username))
        card_layout2.addRow('角色：', MangoLabel(self.user_info.role.get('name') if self.user_info.role else None))
        card_layout2.addRow('邮箱：', MangoLabel(', '.join(self.user_info.mailbox) if self.user_info.mailbox else None))

        v_layout3 = MangoVBoxLayout()
        card_widget3 = MangoCard(v_layout3, '过滤条件')
        h_layout3_1 = MangoHBoxLayout()
        v_layout3.addLayout(h_layout3_1)
        h_layout3_1.addWidget(MangoLabel('选中的项目'))
        select_3_1_data = [ComboBoxDataModel(id=i.value, name=i.label) for i in Methods.base_dict.project]
        select_3_1_data.insert(0, ComboBoxDataModel(id=None, name='全部项目'))
        select_3_1 = MangoComboBox(
            '请选择项目进行过滤',
            data=select_3_1_data,
            value=self.user_info.selected_project,
            is_form=False
        )
        select_3_1.setMinimumWidth(300)
        select_3_1.click.connect(self.func_select_3_1)
        h_layout3_1.addWidget(select_3_1)
        h_layout3_1.addStretch()
        h_layout3_2 = MangoHBoxLayout()
        v_layout3.addLayout(h_layout3_2)
        h_layout3_2.addWidget(MangoLabel('选中的环境'))
        select_3_2_data = [ComboBoxDataModel(**i) for i in EnvironmentEnum.get_option('id', 'name')]
        select_3_2_data.insert(0, ComboBoxDataModel(id=None, name='必须选择一个环境哦！'))
        select_3_2 = MangoComboBox(
            '请选择用例执行环境',
            data=select_3_2_data,
            value=self.user_info.selected_environment,
            is_form=False
        )
        select_3_2.setMinimumWidth(300)
        select_3_2.click.connect(self.func_select_3_2)
        h_layout3_2.addWidget(select_3_2)
        h_layout3_2.addStretch()

        h_layout_4 = MangoHBoxLayout()
        card_layout4 = MangoFormLayout()
        h_layout_4.addLayout(card_layout4)

        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget2)
        self.layout.addWidget(card_widget3)
        self.layout.addStretch()

    def web_save(self):
        self.user_info.config.web_h5 = self.web_h5.get_value()
        self.user_info.config.web_recording = bool(self.web_recording.get_value())
        self.user_info.config.web_parallel = self.web_parallel.get_value()
        self.user_info.config.web_type = self.web_type.get_value()
        self.user_info.config.web_max = bool(self.web_max.get_value())
        self.user_info.config.web_headers = bool(self.web_headers.get_value())
        self.user_info.config.web_path = self.web_path.get_value() if self.web_path.get_value() else None
        self.user_info.config.and_equipment = self.and_equipment.get_value() if self.and_equipment.get_value() else None
        response_message(self, HTTP.put_user_info(json.loads(self.user_info.model_dump_json())))

    def func_select_3_2(self, value):
        self.user_info.selected_environment = value
        HTTP.put_environment(self.user_info.id, value)

    def func_select_3_1(self, value):
        self.user_info.selected_project = value
        HTTP.headers['Project'] = str(value) if value else value
        HTTP.put_user_project(self.user_info.id, value)

    def click_send_redis_data(self):
        r = GetClassMethod()
        send_list: list = r.main()
        send_list.append(
            {CacheDataKey2Enum.ASSERTION_METHOD.value: json.dumps(Assertion.get_methods(), ensure_ascii=False)})
        from src.network.web_socket.websocket_client import WebSocketClient
        WebSocketClient().sync_send(
            '设置缓存数据成功',
            func_name=ToolsSocketEnum.SET_OPERATION_OPTIONS.value,
            is_notice=ClientTypeEnum.WEB,
            func_args=send_list
        )

from mango_ui import *

from src import *
from src.enums.system_enum import CacheDataKey2Enum, EnvironmentEnum
from src.enums.tools_enum import ClientTypeEnum
from src.enums.ui_enum import BrowserTypeEnum, DeviceEnum
from src.models.user_model import UserModel
from src.network import Http
from src.network.web_socket.socket_api_enum import ToolsSocketEnum
from src.tools.assertion import Assertion
from src.tools.methods import Methods
from src.tools.get_class_methods import GetClassMethod


class UserPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = QVBoxLayout()

        self.user_info: Optional[UserModel | None] = None
        self.setLayout(self.layout)

    def show_data(self):
        self.user_info = Http.get_userinfo(UserModel().id)
        card_layout1 = QFormLayout()
        card_widget = MangoCard(card_layout1, '基本信息')
        card_layout1.addRow('头像', MangoLabel('-'))
        card_layout1.addRow('昵称', MangoLabel(self.user_info.nickname))

        card_layout2 = QFormLayout()
        card_widget2 = MangoCard(card_layout2, '账户信息')
        card_layout2.addRow('账号', MangoLabel(self.user_info.username))
        card_layout2.addRow('角色', MangoLabel(self.user_info.role.get('name') if self.user_info.role else None))
        card_layout2.addRow('邮箱', MangoLabel(', '.join(self.user_info.mailbox)))

        v_layout3 = QVBoxLayout()
        card_widget3 = MangoCard(v_layout3, '过滤条件')
        h_layout3_1 = QHBoxLayout()
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
        h_layout3_2 = QHBoxLayout()
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

        h_layout_4 = QHBoxLayout()
        card_layout4 = QFormLayout()
        h_layout_4.addLayout(card_layout4)

        card_widget4 = MangoCard(h_layout_4, '前端自动化设置')
        self.web_max = MangoToggle(self.user_info.config.web_max)
        card_layout4.addRow('浏览器最大化', self.web_max)
        self.web_recording = MangoToggle(self.user_info.config.web_recording)
        card_layout4.addRow('是否视频录制', self.web_recording)
        self.web_parallel = MangoComboBox(
            '请选择需要并发的数量',
            data=[ComboBoxDataModel(id=int(i), name=i) for i in ["1", "2", "3", "5", "10", "15", "20", "30"]],
            value=self.user_info.config.web_parallel
        )
        card_layout4.addRow('浏览器并行数量', self.web_parallel)

        card_layout5 = QFormLayout()
        h_layout_4.addLayout(card_layout5)
        self.web_type = MangoComboBox(
            '请选择浏览器类型',
            data=[ComboBoxDataModel(**i) for i in BrowserTypeEnum.get_option('id', 'name')],
            value=self.user_info.config.web_type,
            is_form=False
        )
        card_layout5.addRow('*浏览器类型：', self.web_type)
        web_h5_data = [ComboBoxDataModel(id=i, name=i) for i in DeviceEnum.get_obj()]
        web_h5_data.insert(0, ComboBoxDataModel(id=None, name='默认非H5'))
        self.web_h5 = MangoComboBox(
            '请选择设备模式',
            data=web_h5_data,
            value=self.user_info.config.web_h5,
            is_form=False
        )
        card_layout5.addRow('H5设备模式：', self.web_h5)
        self.web_path = MangoLineEdit(
            '请输入浏览器路径',
            value=self.user_info.config.web_path,
        )
        card_layout5.addRow('浏览器路径：', self.web_path)
        self.web_headers = MangoToggle(self.user_info.config.web_headers)
        card_layout5.addRow('无头模式：', self.web_headers)
        card_layout6 = QFormLayout()
        self.and_equipment = MangoLineEdit('请输入安卓设备号', value=self.user_info.config.and_equipment)
        self.and_equipment.setMaximumWidth(300)
        card_layout6.addRow('安卓设备号：', self.and_equipment)
        h_layout_4.addLayout(card_layout6)

        card_layout7 = QVBoxLayout()
        but_4 = MangoPushButton('保存')
        but_4.clicked.connect(self.web_save)
        card_layout7.addWidget(but_4)
        h_layout_4.addLayout(card_layout7)

        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget2)
        self.layout.addWidget(card_widget3)
        self.layout.addWidget(card_widget4)
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
        response_message(self, Http.put_user_info(json.loads(self.user_info.model_dump_json())))

    def func_select_3_2(self, value):
        self.user_info.selected_environment = value
        Http.put_environment(self.user_info.id, value)

    def func_select_3_1(self, value):
        self.user_info.selected_project = value
        Http.headers['Project'] = str(value) if value else value
        Http.put_user_project(self.user_info.id, value)

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

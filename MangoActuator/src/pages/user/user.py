from src import *
from src.enums.system_enum import CacheDataKey2Enum, EnvironmentEnum
from src.enums.tools_enum import CacheKeyEnum, CacheValueTypeEnum, ClientTypeEnum
from src.models.gui_model import ComboBoxDataModel
from src.models.user_model import UserModel
from src.network import Http
from src.network.web_socket.socket_api_enum import ToolsSocketEnum
from src.tools.assertion import Assertion
from src.tools.data_processor.sql_cache import SqlCache
from src.tools.other.get_class_methods import GetClassMethod
from src.widgets import *


class UserPage(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(5, 5, 5, 5)

        self.user_info = None
        self.setLayout(self.layout)

    def show_data(self):
        self.user_info = Http.get_userinfo(UserModel().id)
        card_layout1 = QFormLayout()
        card_widget = MangoCardWidget(card_layout1, '基本信息')
        card_layout1.addRow('头像', MangoLabel('-'))
        card_layout1.addRow('昵称', MangoLabel(self.user_info.nickname))

        card_layout2 = QFormLayout()
        card_widget2 = MangoCardWidget(card_layout2, '账户信息')
        card_layout2.addRow('账号', MangoLabel(self.user_info.username))
        card_layout2.addRow('角色', MangoLabel(self.user_info.role.get('name') if self.user_info.role else None))
        card_layout2.addRow('邮箱', MangoLabel(', '.join(self.user_info.mailbox)))

        v_layout3 = QVBoxLayout()
        card_widget3 = MangoCardWidget(v_layout3, '过滤条件')
        h_layout3_1 = QHBoxLayout()
        v_layout3.addLayout(h_layout3_1)
        h_layout3_1.addWidget(MangoLabel('选中的项目'))
        select_3_1_data = [ComboBoxDataModel(id=i.value, name=i.label) for i in settings.base_dict]
        select_3_1_data.insert(0, ComboBoxDataModel(id=None, name='全部项目'))
        select_3_1 = MangoComboBox(
            '请选择项目进行过滤',
            data=select_3_1_data,
            value=self.user_info.selected_project,
            is_form=False
        )
        select_3_1.setMinimumWidth(300)
        select_3_1.clicked.connect(self.func_select_3_1)
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
        select_3_2.clicked.connect(self.func_select_3_2)
        h_layout3_2.addWidget(select_3_2)
        h_layout3_2.addStretch()
        self.layout.addWidget(card_widget)
        self.layout.addWidget(card_widget2)
        self.layout.addWidget(card_widget3)
        self.layout.addStretch()

    def func_select_3_2(self, value):
        Http.put_environment(self.user_info.id, value)

    def func_select_3_1(self, value):
        Http.headers['Project'] = str(value)
        Http.put_user_project(self.user_info.id, value)

    def ui_browser_max(self, value):
        SqlCache.set_sql_cache(
            CacheKeyEnum.BROWSER_IS_MAXIMIZE.value,
            '1' if value.get('value') else '0',
            CacheValueTypeEnum.INT.value
        )

    def ui_recording(self, value):
        SqlCache.set_sql_cache(
            CacheKeyEnum.IS_RECORDING.value,
            '1' if value.get('value') else '0',
            CacheValueTypeEnum.INT.value
        )

    def on_combobox_changed(self, text):
        SqlCache.set_sql_cache(CacheKeyEnum.TEST_CASE_PARALLELISM.value, text)

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

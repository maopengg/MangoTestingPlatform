from mangokit.data_processor import EncryptionTool
from mangokit.database import SQLiteConnect
from mangokit.mangos import Mango
from mangoui import *
from requests.exceptions import JSONDecodeError, InvalidURL, ConnectionError

from src.network import HTTP
from src.pages.login.login import LoginWindow
from src.pages.window.mian_window import MainWindow
from src.settings import settings
from src.tools import project_dir
from src.tools.methods import Methods
from src.tools.sql_statement import sql_statement_1, sql_statement_2, sql_statement_3
from .login_dict import form_data
from ...tools.components.message import response_message


class LoginLogic(LoginWindow):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.form_data = [FormDataModel(**i) for i in form_data]

        self.register_but.clicked.connect(self.register)
        self.setWindowTitle('登录')
        self.setFixedSize(280, 350)
        self.setWindowIcon(QIcon(':/icons/app_icon.png'))
        self.main_window = None
        self.conn = SQLiteConnect(project_dir.cache_file())
        user_info = self.conn.execute(sql_statement_1)
        if user_info:
            self.ip_edit.setText(user_info[0].get("ip"))
            self.prot_edit.setText(user_info[0].get("port"))
            self.username_edit.setText(user_info[0].get('username'))
            self.password_edit.setText(user_info[0].get('password'))
        else:
            self.ip_edit.setText('121.37.174.56')
            self.prot_edit.setText('8000')

    @Slot()
    def on_pushButtonLogin_clicked(self):
        self.login_but.setEnabled(False)
        settings.IP = self.ip_edit.text()
        settings.PORT = self.prot_edit.text()
        settings.USERNAME = self.username_edit.text()
        settings.PASSWORD = self.password_edit.text()
        if not settings.IP or not settings.PORT:
            show_failed_message('请先输入IP或端口后再进行登录')
        if not settings.USERNAME or not settings.PASSWORD:
            show_failed_message('请先输入账号或密码后再进行登录')
        HTTP.api.info.set_host(settings.IP, settings.PORT)
        try:
            response = HTTP.not_auth.login(settings.USERNAME,
                                           EncryptionTool.md5_32_small(**{'data': settings.PASSWORD}))
            if response.code == 200:
                if not settings.IS_NEW:
                    Methods.set_project()
                self.main_window = MainWindow(self.loop)
                self.close()
                self.main_window.show()
                remember = self.remember_box.isChecked()
                if remember:
                    self.conn.execute(sql_statement_3)
                    self.conn.execute(sql_statement_2,
                                      (settings.USERNAME, settings.PASSWORD, settings.IP, settings.PORT))
                HTTP.user.info.get_userinfo(response.data.get('userId'))
            else:
                show_failed_message('账号或密码错误')

        except (JSONDecodeError, InvalidURL):
            show_failed_message('IP或端口不正确')
        except ConnectionError:
            show_failed_message('IP或端口不正确或服务未启动')
        self.login_but.setEnabled(True)

    def register(self, ):
        settings.IP = self.ip_edit.text()
        settings.PORT = self.prot_edit.text()
        if not settings.IP:
            show_failed_message('请先输入IP再使用注册功能！')
            return
        if not settings.PORT:
            show_failed_message('请先输入端口再使用注册功能！')
            return
        HTTP.api.info.set_host(settings.IP, settings.PORT)
        form_data = Mango.add_from_data(self)
        dialog = DialogWidget('新增用户', form_data)
        dialog.exec()
        if dialog.data:

            if dialog.data['password'] == dialog.data['confirm_password']:
                dialog.data['password'] = EncryptionTool.md5_32_small(**{'data': dialog.data['password']})
                try:
                    response_model = HTTP.not_auth.user_register(dialog.data)
                    if response_model:
                        response_message(self, response_model)
                except (JSONDecodeError, InvalidURL):
                    show_failed_message('IP或端口不正确')
                except ConnectionError:
                    show_failed_message('IP或端口不正确或服务未启动')
            else:
                show_failed_message('您输入的两次密码不一致！')

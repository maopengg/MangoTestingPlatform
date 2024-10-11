from mango_ui import show_failed_message
from mango_ui.init import *
from mangokit import SQLiteConnect
from requests.exceptions import JSONDecodeError, InvalidURL, ConnectionError
from src.tools import InitPath
from src.network.http import Http
from src.pages.login.login_ui import LoginWindow
from src.pages.window.mian_window import MainWindow
from src.tools.sql_statement import sql_statement_1, sql_statement_2, sql_statement_3

from src.settings import settings
from src.tools.methods import Methods


class LoginLogic(LoginWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('登录')
        self.setFixedSize(280, 350)
        self.setWindowIcon(QIcon(':/icons/app_icon.png'))
        self.main_window = None
        self.conn = SQLiteConnect(InitPath.cache_path())
        user_info = self.conn.execute(sql_statement_1)
        if user_info:
            self.ip_edit.setText(user_info[0].get("ip"))
            self.prot_edit.setText(user_info[0].get("port"))
            self.username_edit.setText(user_info[0].get('username'))
            self.password_edit.setText(user_info[0].get('password'))
        self.show()

    @Slot()
    def on_pushButtonLogin_clicked(self):
        settings.IP = self.ip_edit.text()
        settings.PORT = self.prot_edit.text()
        settings.USERNAME = self.username_edit.text()
        settings.PASSWORD = self.password_edit.text()
        if not settings.IP or not settings.PORT:
            show_failed_message('请先输入IP或端口后再进行登录')
        if not settings.USERNAME or not settings.PASSWORD:
            show_failed_message('请先输入账号或密码后再进行登录')
        try:
            res = Http.login(settings.USERNAME, settings.PASSWORD)
            if res.code == 200:
                Methods.set_project()
                self.main_window = MainWindow()
                self.close()
                self.main_window.show()
                remember = self.remember_box.isChecked()
                if remember:
                    self.conn.execute(sql_statement_3)
                    self.conn.execute(sql_statement_2,
                                                (settings.USERNAME, settings.PASSWORD, settings.IP, settings.PORT))
            else:
                show_failed_message('账号或密码错误')

        except (JSONDecodeError, InvalidURL):
            show_failed_message('IP或端口不正确')
        except ConnectionError:
            show_failed_message('IP或端口不正确或服务未启动')
        # except TypeError:
        #     show_failed_message('账号或密码错误!')

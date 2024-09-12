from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon
from requests.exceptions import JSONDecodeError, InvalidURL, ConnectionError

from src.models.gui_model import CascaderModel
from src.network.http.http_client import HttpClient
from src.pages.login.login_ui import LoginWindow
from src.pages.mian_window import MainWindow
from src.settings import settings
from src.tools.database.sql_statement import sql_statement_1, sql_statement_2, sql_statement_3
from src.tools.database.sqlite_connect import SQLiteConnect
from src.widgets.mango_tooltip_box import show_failed_message


class LoginLogic(LoginWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('登录')
        self.setFixedSize(280, 350)
        self.setWindowIcon(QIcon(':/icons/app_icon.png'))
        self.main_window = None
        self.db_handler = SQLiteConnect()
        user_info = self.db_handler.execute_sql(sql_statement_1)
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
        try:
            res = HttpClient.login(settings.USERNAME, settings.PASSWORD)
            if res.get('code') == 200:
                settings.base_dict = [CascaderModel(**i) for i in HttpClient.project_info()['data']]

                self.main_window = MainWindow()
                self.close()
                self.main_window.show()
                remember = self.remember_box.isChecked()
                if remember:
                    self.db_handler.execute_sql(sql_statement_3)
                    self.db_handler.execute_sql(sql_statement_2,
                                                (settings.USERNAME, settings.PASSWORD, settings.IP, settings.PORT))
            else:
                show_failed_message('账号或密码错误')

        except (JSONDecodeError, InvalidURL):
            show_failed_message('IP或端口不正确')
        except ConnectionError:
            show_failed_message('IP或端口不正确或服务未启动')
        # except TypeError:
        #     show_failed_message('账号或密码错误!')

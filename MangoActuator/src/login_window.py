from mango_ui import show_failed_message, CascaderModel
from mango_ui.init import *
from requests.exceptions import JSONDecodeError, InvalidURL, ConnectionError

from src.network.http import Http
from src.pages.login.login_ui import LoginWindow
from src.pages.window.mian_window import MainWindow
from src.tools.database.sql_statement import sql_statement_1, sql_statement_2, sql_statement_3
from src.tools.database.sqlite_connect import SQLiteConnect

from src.settings import settings

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
            res = Http.login(settings.USERNAME, settings.PASSWORD)
            if res.code == 200:
                settings.base_dict = [CascaderModel(**i) for i in Http.project_info()['data']]

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

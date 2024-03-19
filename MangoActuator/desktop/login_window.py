from PySide6.QtWidgets import QWidget, QMessageBox
from requests.exceptions import JSONDecodeError, InvalidURL, ConnectionError

import service
from desktop.login.ui_login import Ui_login
from desktop.mian_window import MainWindow
from service.http_client.http_api import HttpApi
from tools.database_tool.sql_statement import sql_statement_1, sql_statement_2, sql_statement_3
from tools.database_tool.sqlite_handler import SQLiteHandler


class LoginWindow(QWidget, Ui_login):
    def __init__(self):
        super().__init__()
        self.setFixedSize(280, 350)
        self.setupUi(self)
        self.login_but.clicked.connect(self.login)
        self.main_window = None
        self.db_handler = SQLiteHandler()
        user_info = self.db_handler.execute_sql(sql_statement_1)
        username = ''
        password = ''
        ip = '填写IP'
        port = '填写后端端口'
        if len(user_info) > 1:
            self.show_login_failed_message('请联系管理员检查该问题，点击取消弹窗后，请输入正确的账号密码即可使用')
        elif user_info:
            username = user_info[0].get('username')
            password = user_info[0].get('password')
            ip = user_info[0].get("ip")
            port = user_info[0].get("port")
            # if user_info[0].get('username'):
            #     username = user_info[0].get('username')
            # if user_info[0].get('password'):
            #     password = user_info[0].get('password')
            # if user_info[0].get("ip"):
            #     ip = user_info[0].get("ip")
            # if user_info[0].get("port"):
            #     port = user_info[0].get("port")
        self.ip_edit.setText(ip)
        self.prot_edit.setText(port)
        self.username_edit.setText(username)
        self.password_edit.setText(password)

    def login(self):
        service.IP = self.ip_edit.text()
        service.PORT = self.prot_edit.text()
        service.USERNAME = self.username_edit.text()
        service.PASSWORD = self.password_edit.text()
        remember = self.remember_box.isChecked()
        if remember:
            self.db_handler.execute_sql(sql_statement_3)
            self.db_handler.execute_sql(sql_statement_2,
                                        (service.USERNAME, service.PASSWORD, service.IP, service.PORT))
        try:
            res = HttpApi().login()
            if res.get('code') == 200:
                self.main_window = MainWindow()
                self.close()
                self.main_window.show()
            else:
                self.show_login_failed_message('账号或密码错误')

        except (JSONDecodeError, InvalidURL):
            self.show_login_failed_message('IP或端口不正确')
        except ConnectionError:
            self.show_login_failed_message('IP或端口不正确或服务未启动')
        except TypeError:
            self.show_login_failed_message('账号或密码错误')

    @classmethod
    def show_login_failed_message(cls, text):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(text)
        msg.setWindowTitle("登录失败")
        msg.exec()

from PySide6.QtWidgets import QWidget, QMessageBox
from requests.exceptions import JSONDecodeError, InvalidURL, ConnectionError

import service_conn
from src.gui.login.ui_login import Ui_login
from desktop import MainWindow
from service_conn import HttpApi
from src.tools.database.sql_statement import sql_statement_1, sql_statement_2, sql_statement_3
from src.tools.database.sqlite_connect import SQLiteConnect


class LoginWindow(QWidget, Ui_login):
    def __init__(self):
        super().__init__()
        self.setFixedSize(280, 350)
        self.setupUi(self)
        self.login_but.clicked.connect(self.login)
        self.main_window = None
        self.db_handler = SQLiteConnect()
        user_info = self.db_handler.execute_sql(sql_statement_1)
        username = ''
        password = ''
        ip = '填写IP'
        port = '8000'
        if len(user_info) > 1:
            self.show_login_failed_message('请联系管理员检查该问题，点击取消弹窗后，请输入正确的账号密码即可使用')
        elif user_info:
            username = user_info[0].get('username')
            password = user_info[0].get('password')
            ip = user_info[0].get("ip")
            port = user_info[0].get("port")
        self.ip_edit.setText(ip)
        self.prot_edit.setText(port)
        self.username_edit.setText(username)
        self.password_edit.setText(password)

    def login(self):
        service_conn.IP = self.ip_edit.text()
        service_conn.PORT = self.prot_edit.text()
        service_conn.USERNAME = self.username_edit.text()
        service_conn.PASSWORD = self.password_edit.text()
        remember = self.remember_box.isChecked()
        if remember:
            self.db_handler.execute_sql(sql_statement_3)
            self.db_handler.execute_sql(sql_statement_2,
                                        (service_conn.USERNAME, service_conn.PASSWORD, service_conn.IP, service_conn.PORT))
        try:
            res = HttpApi.login(service_conn.USERNAME, service_conn.PASSWORD)
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

from PySide6.QtCore import Slot
from PySide6.QtGui import QIcon
from httpx import HTTPStatusError, ConnectError
from mangotools.data_processor import EncryptionTool
from mangotools.mangos import Mango
from mangoui.components import DialogWidget
from mangoui.models import FormDataModel
from mangoui.widgets.network import asyncSlot
from mangoui.widgets.window import show_failed_message

from src.network import HTTP
from src.pages.login.login import LoginWindow
from src.pages.window.mian_window import MainWindow
from src.tools.set_config import SetConfig
from .login_dict import form_data
from ... import log
from ...exceptions import ToolsError
from ...tools.components.message import response_message
from ...tools.url import is_valid_url, http_to_ws_url


class LoginLogic(LoginWindow):

    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.form_data = [FormDataModel(**i) for i in form_data]

        self.setWindowTitle('登录')
        self.setFixedSize(280, 350)
        self.setWindowIcon(QIcon(':/icons/app_icon.png'))
        self.main_window = None

        host = SetConfig.get_host()  # type: ignore
        username = SetConfig.get_username()  # type: ignore
        password = SetConfig.get_password()  # type: ignore
        self.ip_edit.setText(host if host else '')
        self.username_edit.setText(username if username else '')
        self.password_edit.setText(password if password else '')

    @Slot()
    def on_pushButtonLogin_clicked(self):
        """点击登录按钮"""
        if not self.ip_edit.text():
            show_failed_message('请输入后端的服务地址，请确保是正确的')
            return

        http_url = is_valid_url(str(self.ip_edit.text()))
        ws_url = http_to_ws_url(http_url)
        if not http_url or not ws_url:
            show_failed_message('请输入合法的域名地址，如：http://127.0.0.1:8000/')
            return

        SetConfig.set_ws(ws_url)  # type: ignore
        SetConfig.set_host(http_url)  # type: ignore

        if not self.username_edit.text() or not self.password_edit.text():
            show_failed_message('请输入账号或密码后再进行登录')
            return

        remember = self.remember_box.isChecked()
        SetConfig.set_username(self.username_edit.text())  # type: ignore
        SetConfig.set_password(self.password_edit.text())  # type: ignore
        if remember:
            SetConfig.set_remember_username(self.username_edit.text())  # type: ignore
            SetConfig.set_remember_password(self.password_edit.text())  # type: ignore

        self.login_but.setEnabled(False)
        self._do_login()

    @asyncSlot()
    async def _do_login(self):
        """执行登录（运行在 QEventLoop 中）"""
        try:
            response = await HTTP.system.login(
                self.username_edit.text(),
                self.password_edit.text()
            )
            self.login_but.setEnabled(True)
            if response.code == 200:
                # 先刷新客户端（reinit_client 已在 login 中执行，这里重建 user API 引用）
                HTTP.refresh()
                self.main_window = MainWindow(self.loop)
                self.close()
                self.main_window.show()
                await HTTP.user.get_userinfo(response.data.get('userId'))
            elif response.code == -300:
                show_failed_message('IP或端口不正确或服务未启动')
            else:
                log.error(f'登录失败，失败信息：{response.model_dump_json()}')
                show_failed_message(response.msg)
        except HTTPStatusError:
            self.login_but.setEnabled(True)
            show_failed_message('IP或端口不正确')
        except ConnectError:
            self.login_but.setEnabled(True)
            show_failed_message('IP或端口不正确或服务未启动')
        except ToolsError as e:
            self.login_but.setEnabled(True)
            show_failed_message(e.msg)
        except Exception as e:
            self.login_but.setEnabled(True)
            show_failed_message('发生未知错误，请联系管理员！')
            import traceback
            log.error(f'登录未知错误：{type(e)}, {e}，{traceback.format_exc()}')

    def register(self):
        """注册"""
        if not self.ip_edit.text():
            show_failed_message('请输入域名后再进行注册')
            return
        if not is_valid_url(str(self.ip_edit.text())):
            show_failed_message('请输入合法的域名地址再进行注册，如：http://127.0.0.1:8000/')
            return

        form_data_obj = Mango.add_from_data(self)
        dialog = DialogWidget('新增用户', form_data_obj)
        dialog.exec()

        if dialog.data:
            if dialog.data['password'] == dialog.data['confirm_password']:
                dialog.data['password'] = EncryptionTool.md5_32_small(dialog.data['password'])
                self._do_register(dialog.data)
            else:
                show_failed_message('您输入的两次密码不一致！')

    @asyncSlot()
    async def _do_register(self, json_data: dict):
        """执行注册（运行在 QEventLoop 中）"""
        try:
            response = await HTTP.system.user_register(json_data)
            if response:
                response_message(self, response)
        except HTTPStatusError:
            show_failed_message('IP或端口不正确')
        except ConnectError:
            show_failed_message('IP或端口不正确或服务未启动')
        except Exception as e:
            show_failed_message(f'注册失败: {str(e)}')

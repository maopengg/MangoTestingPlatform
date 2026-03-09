from PySide6.QtCore import Slot, Signal
from PySide6.QtGui import QIcon
from httpx import HTTPStatusError, ConnectError
from mangotools.data_processor import EncryptionTool
from mangotools.mangos import Mango
from mangoui.components import DialogWidget
from mangoui.models import FormDataModel
from mangoui.widgets.window import show_failed_message

from src.network import HTTP
from src.pages.login.login import LoginWindow
from src.pages.window.mian_window import MainWindow
from src.tools.set_config import SetConfig
from src.tools.async_request import AsyncRequestMixin, AsyncResult
from .login_dict import form_data
from ... import log
from ...exceptions import ToolsError
from ...tools.components.message import response_message
from ...tools.url import is_valid_url, http_to_ws_url


class LoginLogic(LoginWindow, AsyncRequestMixin):
    login_success_signal = Signal(dict)
    
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
        
        # 初始化异步请求
        self._init_async_request()
        
        # 连接信号到槽
        self.login_success_signal.connect(self._on_login_success)

    @Slot()
    def on_pushButtonLogin_clicked(self):
        """点击登录按钮"""
        # 验证输入
        if not self.ip_edit.text() or self.ip_edit.text() == '':
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
        
        # 保存配置
        remember = self.remember_box.isChecked()
        SetConfig.set_username(self.username_edit.text())  # type: ignore
        SetConfig.set_password(self.password_edit.text())  # type: ignore
        if remember:
            SetConfig.set_remember_username(self.username_edit.text())  # type: ignore
            SetConfig.set_remember_password(self.password_edit.text())  # type: ignore
        
        # 禁用按钮
        self.login_but.setEnabled(False)
        
        # 发起异步登录请求
        self.async_request(
            self._do_login,
            callback=self._on_login_result
        )
    
    async def _do_login(self):
        """执行登录"""
        response = await HTTP.not_auth.login(
            self.username_edit.text(),
            self.password_edit.text()
        )
        return response
    
    def _on_login_result(self, result: AsyncResult):
        """处理登录结果"""
        self.login_but.setEnabled(True)
        
        if not result.success:
            error = result.error
            if isinstance(error, HTTPStatusError):
                show_failed_message('IP或端口不正确')
            elif isinstance(error, ConnectError):
                show_failed_message('IP或端口不正确或服务未启动')
            elif isinstance(error, ToolsError):
                show_failed_message(error.msg)
            else:
                show_failed_message('发生未知错误，请联系管理员！')
                import traceback
                log.error(f'发生未知错误，请联系管理员！错误类型：{type(error)}, 错误详情：{error}，错误明细：{traceback.format_exc()}')
            return
        
        response = result.data
        if response.code == 200:
            # 使用信号在主线程中处理UI操作
            self.login_success_signal.emit(response.data)
        elif response.code == -300:
            show_failed_message('IP或端口不正确或服务未启动')
        else:
            log.error(f'登录失败，失败信息：{response.model_dump_json()}')
            show_failed_message(response.msg)
    
    @Slot(dict)
    def _on_login_success(self, user_data):
        """在主线程中处理登录成功后的UI操作"""
        self.main_window = MainWindow(self.loop)
        self.close()
        self.main_window.show()
        # 异步获取用户信息
        self.async_request(
            lambda: HTTP.user.info.get_userinfo(user_data.get('userId'))
        )

    def register(self):
        """注册"""
        if not self.ip_edit.text() or self.ip_edit.text() == '':
            show_failed_message('请输入域名后再进行注册')
            return
        if not is_valid_url(str(self.ip_edit.text())):
            show_failed_message('请输入合法的域名地址再进行注册，如：http://127.0.0.1:8000/')
            return
        
        form_data = Mango.add_from_data(self)
        dialog = DialogWidget('新增用户', form_data)
        dialog.exec()
        
        if dialog.data:
            if dialog.data['password'] == dialog.data['confirm_password']:
                dialog.data['password'] = EncryptionTool.md5_32_small(dialog.data['password'])
                # 发起异步注册请求
                self.async_request(
                    self._do_register,
                    callback=self._on_register_result,
                    json_data=dialog.data
                )
            else:
                show_failed_message('您输入的两次密码不一致！')
    
    async def _do_register(self, json_data: dict):
        """执行注册"""
        return await HTTP.not_auth.user_register(json_data)
    
    def _on_register_result(self, result: AsyncResult):
        """处理注册结果"""
        if not result.success:
            error = result.error
            if isinstance(error, HTTPStatusError):
                show_failed_message('IP或端口不正确')
            elif isinstance(error, ConnectError):
                show_failed_message('IP或端口不正确或服务未启动')
            else:
                show_failed_message(f'注册失败: {str(error)}')
            return
        
        response_model = result.data
        if response_model:
            response_message(self, response_model)

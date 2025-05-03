from urllib.parse import urlparse, urlunparse

from mangokit.data_processor import EncryptionTool, SqlCache
from mangokit.mangos import Mango
from mangoui import *
from requests.exceptions import JSONDecodeError, InvalidURL, ConnectionError

from src.enums.tools_enum import CacheKeyEnum
from src.network import HTTP
from src.pages.login.login import LoginWindow
from src.pages.window.mian_window import MainWindow
from src.settings import settings
from src.tools import project_dir
from src.tools.methods import Methods
from .login_dict import form_data
from ... import log
from ...tools.components.message import response_message


def http_to_ws_url(http_url):
    """
    将HTTP/HTTPS URL转换为WebSocket URL
    :param http_url: 原始HTTP/HTTPS URL
    :return: 对应的WebSocket URL，如果输入不合法则返回None
    """
    try:
        parsed = urlparse(http_url)
        if parsed.scheme not in ('http', 'https'):
            return None
        new_scheme = 'wss' if parsed.scheme == 'https' else 'ws'
        path = parsed.path
        if not path.endswith('/'):
            path = path + '/'
        ws_url = urlunparse((
            new_scheme,
            parsed.netloc,
            path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

        return ws_url

    except Exception:
        return None


def is_valid_url(url):
    try:
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return None
        if parsed.scheme not in ('http', 'https', 'ftp'):
            return None
        return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
    except Exception:
        return None


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
        self.cache = SqlCache(project_dir.cache_file())
        host = self.cache.get_sql_cache(CacheKeyEnum.HOST.value)
        username = self.cache.get_sql_cache(CacheKeyEnum.REMEMBER_USERNAME.value)
        password = self.cache.get_sql_cache(CacheKeyEnum.REMEMBER_PASSWORD.value)
        self.ip_edit.setText(host if host else '')
        self.username_edit.setText(username if username else '')
        self.password_edit.setText(password if password else '')

    @Slot()
    def on_pushButtonLogin_clicked(self):
        self.login_but.setEnabled(True)
        if not self.ip_edit.text() or self.ip_edit.text() == '':
            show_failed_message('请输入域名后再进行登录')
            self.login_but.setEnabled(True)
            return
        http_url = is_valid_url(str(self.ip_edit.text()))
        ws_url = http_to_ws_url(http_url)
        if not http_url or not ws_url:
            show_failed_message('请输入合法的域名地址，如：http://127.0.0.1:8000/')
            self.login_but.setEnabled(True)
            return
        else:
            self.cache.set_sql_cache(CacheKeyEnum.WS.value, ws_url)
            self.cache.set_sql_cache(CacheKeyEnum.HOST.value, http_url)
        if not self.username_edit.text() or self.username_edit.text() == '' or not self.password_edit.text() or self.password_edit.text() == '':
            show_failed_message('请输入账号或密码后再进行登录')
            self.login_but.setEnabled(True)
            return
        remember = self.remember_box.isChecked()
        self.cache.set_sql_cache(CacheKeyEnum.USERNAME.value, self.username_edit.text())
        self.cache.set_sql_cache(CacheKeyEnum.PASSWORD.value, self.password_edit.text())
        if remember:
            self.cache.set_sql_cache(CacheKeyEnum.REMEMBER_USERNAME.value, self.username_edit.text())
            self.cache.set_sql_cache(CacheKeyEnum.REMEMBER_PASSWORD.value, self.password_edit.text())
        try:
            response = HTTP.not_auth.login(self.username_edit.text(), self.password_edit.text())
            if response.code == 200:
                if not settings.IS_NEW:
                    Methods.set_project()
                self.main_window = MainWindow(self.loop)
                self.close()
                self.main_window.show()
                HTTP.user.info.get_userinfo(response.data.get('userId'))
            else:
                show_failed_message('账号或密码错误')
        except (JSONDecodeError, InvalidURL):
            show_failed_message('IP或端口不正确')
        except ConnectionError:
            show_failed_message('IP或端口不正确或服务未启动')
        except Exception as e:
            show_failed_message('发生未知错误，请联系管理员！')
            import traceback
            log.error(f'发生未知错误，请联系管理员！错误类型：{type(e)}, 错误详情：{e}，错误明细：{traceback.format_exc()}')
        self.login_but.setEnabled(True)

    def register(self, ):
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

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from pathlib import Path
from queue import Empty
import os
import subprocess
import sys

import flet as ft

from src import process
from src.enums.tools_enum import MessageEnum
from src.network import HTTP
from src.services.runtime import RuntimeInstanceLock
from src.settings import settings
from src.tools import project_dir
from src.tools.execution_activity import ExecutionActivity
from src.tools.log_collector import log
from src.tools.send_global_msg import global_msg_queue
from src.tools.set_config import SetConfig
from src.tools.url import is_valid_url, platform_ws_url
from .config import config_view
from .runtime import AsyncRuntimeBridge
from .theme import (
    BACKGROUND, MUTED, PRIMARY, TEXT, LINE, NAV_TEXT, NAV_MUTED, NAV_ACTIVE,
    TINT, PAGE_GAP, BODY_SIZE, SUCCESS, WARNING, SURFACE, SOFT, DANGER,
    CODE_BG, CODE_TEXT, CODE_MUTED, LOG_COLORS, compact_input, action_button,
    detail_row, field_row, section, status_badge, toggle_control, checkbox_control, platform_logo,
)
from .tray import TrayController
from .select import CompactSelect


class FletActuatorApplication:
    TITLES = {"home": "运行概览", "logs": "实时日志", "web": "WEB 配置", "android": "Android 配置", "ios": "iOS 配置", "pc": "PC 配置", "pytest": "Pytest 配置", "settings": "系统设置", "user": "用户信息"}

    def __init__(self, page: ft.Page):
        self.page = page
        # 原生隐藏启动不一定同步到 Python 的属性，先显式隐藏才能可靠触发后续显示更新。
        page.window.visible = False
        self.bridge = AsyncRuntimeBridge()
        self.bridge.start()
        self.user_id = None
        self.closing = False
        self.ready = False
        self.connected = False
        self.logs = deque(maxlen=2000)
        self.status = ft.Text("就绪", color=MUTED, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
        self.content = ft.Container(expand=True, padding=PAGE_GAP)
        self.current = "home"
        self.tray = TrayController(project_dir.resource_path("assets/app_icon.ico"), lambda: self.bridge.callbacks.put((self.show_window, ())), lambda: self.bridge.callbacks.put((self.request_exit, ())))
        page.title = "芒果执行器"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.theme = ft.Theme(color_scheme_seed=PRIMARY, visual_density=ft.VisualDensity.COMPACT,
            canvas_color=SURFACE, focus_color=NAV_ACTIVE, hover_color=TINT,
            color_scheme=ft.ColorScheme(surface=SURFACE, surface_tint=SURFACE,
                primary=PRIMARY, on_primary=SURFACE, on_surface=TEXT,
                primary_container=NAV_ACTIVE, on_primary_container=PRIMARY,
                secondary=PRIMARY, on_secondary=SURFACE, secondary_container=TINT,
                on_secondary_container=TEXT, surface_variant=SOFT, on_surface_variant=MUTED,
                outline=LINE, outline_variant=LINE, error=DANGER),
            font_family="Microsoft YaHei" if sys.platform == "win32" else "PingFang SC" if sys.platform == "darwin" else None,
            text_theme=ft.TextTheme(body_medium=ft.TextStyle(color=TEXT, size=BODY_SIZE), body_large=ft.TextStyle(color=TEXT, size=BODY_SIZE), label_large=ft.TextStyle(size=BODY_SIZE)))
        page.bgcolor = SURFACE
        page.padding = 0
        page.window.prevent_close = True
        page.window.on_event = self.window_event
        self.show_login()
        self.pump_task = page.run_task(self.pump)

    def notify(self, text, *, popup=True):
        self.status.value = str(text)
        self.status.tooltip = str(text)
        if popup:
            self.page.open(ft.SnackBar(ft.Text(str(text))))
        else:
            self.page.update()

    def confirm(self, text, callback):
        dialog = ft.AlertDialog(title=ft.Text("请确认", size=16, weight=ft.FontWeight.W_600),
                                content=ft.Container(ft.Text(text, size=13, color=TEXT), width=360),
                                bgcolor=SURFACE, surface_tint_color=SURFACE, elevation=4,
                                content_padding=ft.padding.symmetric(horizontal=24, vertical=16),
                                actions_padding=ft.padding.only(left=16, right=16, bottom=16),
                                actions_alignment=ft.MainAxisAlignment.END,
                                shape=ft.RoundedRectangleBorder(radius=7))
        def accept(event):
            self.page.close(dialog)
            callback(event)
        dialog.actions = [action_button("取消", lambda _: self.page.close(dialog)),
                          action_button("确认", accept, primary=True)]
        self.page.open(dialog)

    def show_login(self):
        self.page.bgcolor = SURFACE
        self.page.window.min_width, self.page.window.min_height = 360, 440
        self.page.window.width, self.page.window.height = 360, 470
        self.page.window.resizable = True
        username, password, remember = SetConfig.get_remembered_login()
        self.host = ft.TextField(label="服务地址", value=str(SetConfig.get_host() or ""))
        proxy = self.normalize_proxy(SetConfig.get_proxy_url())
        self.proxy = ft.TextField(label="代理地址（可选）", value=proxy)
        self.username = ft.TextField(label="账号", value=username)
        self.password = ft.TextField(label="密码", value=password, password=True, can_reveal_password=True, on_submit=self.login)
        for control in (self.host, self.proxy, self.username, self.password):
            compact_input(control)
            control.height = 38
            control.content_padding = ft.padding.symmetric(horizontal=12, vertical=10)
        self.remember = checkbox_control(ft.Checkbox(label="记住密码", value=remember))
        self.login_status = ft.Text("使用测试平台账号登录", color=MUTED, size=12, text_align=ft.TextAlign.CENTER)
        self.login_button = action_button("登录并启动执行器", self.login, primary=True)
        self.proxy.visible = bool(self.proxy.value)
        self.page.window.height = 500 if self.proxy.visible else 470

        def toggle_proxy(_):
            self.proxy.visible = not self.proxy.visible
            self.login_card.height = 400 if self.proxy.visible else 360
            self.page.window.height = 500 if self.proxy.visible else 470
            self.page.update()
            self.page.window.center()

        form = ft.Column([
            ft.Row([
                platform_logo(36),
                ft.Column([ft.Text("芒果执行器", size=18, weight=ft.FontWeight.W_600, color=TEXT), ft.Text("自动化测试 · 本机执行服务", size=11, color=MUTED)], spacing=2),
            ], spacing=10),
            ft.Container(height=4),
            self.login_status,
            self.host, self.username, self.password, self.proxy,
            ft.Row([self.remember, action_button("代理设置", toggle_proxy)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row([self.login_button], alignment=ft.MainAxisAlignment.CENTER),
        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, scroll=ft.ScrollMode.AUTO)
        self.login_button.expand = True
        self.login_card = ft.Container(form, height=400 if self.proxy.visible else 360,
            padding=12)
        self.page.controls = [ft.Container(self.login_card, width=360, padding=20, expand=True,
                                           alignment=ft.alignment.center)]
        self.page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.page.update()
        self.page.window.center()
        self.page.window.visible = True
        self.page.update()
        self.page.window.to_front()

    def endpoint(self):
        host = is_valid_url((self.host.value or "").strip())
        ws = platform_ws_url(host) if host else None
        if not host or not ws:
            raise RuntimeError("请输入合法的平台服务地址")
        SetConfig.set_host(host)
        SetConfig.set_ws(ws)
        SetConfig.set_proxy_url(self.normalize_proxy(self.proxy.value) or None)
        HTTP.refresh()

    @staticmethod
    def normalize_proxy(value):
        text = str(value or "").strip()
        return "" if text.lower() in {"none", "null"} else text

    async def login(self, _):
        if self.login_button.disabled:
            return
        try:
            self.endpoint()
            username, password = (self.username.value or "").strip(), self.password.value or ""
            if not username or not password:
                raise RuntimeError("请输入账号和密码")
            self.login_button.disabled = True
            self.login_button.text = "登录中…"
            self.login_status.value = "正在连接测试平台…"
            self.login_status.color = MUTED
            self.page.update()
            async def request():
                response = await asyncio.wait_for(HTTP.system.login(username, password), 30)
                if response.code != 200:
                    raise RuntimeError(str(response.msg or "登录失败"))
                SetConfig.save_login_credentials(username, password, bool(self.remember.value))
                HTTP.refresh()
                await asyncio.wait_for(HTTP.system.refresh_runtime_config(), 30)
                return response.data.get("userId") if isinstance(response.data, dict) else None
            self.user_id = await asyncio.wrap_future(self.bridge.submit(request()))
            self.show_main()
        except Exception as error:
            self.login_button.disabled = False
            self.login_button.text = "登录并启动执行器"
            self.login_status.color = DANGER
            self.login_status.value = str(error) or "连接超时，请检查服务地址后重试"
            self.page.update()

    def show_main(self):
        self.page.bgcolor = BACKGROUND
        self.page.window.resizable = True
        self.page.window.width, self.page.window.height = 1120, 760
        self.page.window.min_width, self.page.window.min_height = 960, 640
        self.page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH
        self.nav_items = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)
        self.sidebar = ft.Container(width=188, bgcolor=SURFACE,
            border=ft.border.only(right=ft.BorderSide(1, LINE)), padding=ft.padding.symmetric(horizontal=10, vertical=14),
            content=ft.Column([
                ft.Container(ft.Row([
                    platform_logo(30),
                    ft.Column([ft.Text("芒果执行器", size=15, color=TEXT, weight=ft.FontWeight.W_600),
                               ft.Text("本机工作空间", size=11, color=MUTED)], spacing=2),
                ], spacing=8), padding=ft.padding.only(left=6, bottom=12)),
                self.nav_items,
                ft.Divider(color=LINE, height=1),
                ft.Container(ft.Row([
                    ft.CircleAvatar(content=ft.Icon(ft.Icons.PERSON_OUTLINE_ROUNDED, color=PRIMARY, size=18), bgcolor=TINT, radius=15),
                    ft.Column([ft.Text(str(SetConfig.get_username() or "执行器用户"), color=TEXT, size=12,
                                       max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                               ft.Text("用户信息", color=MUTED, size=11)], spacing=2, expand=True),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT_ROUNDED, size=16, color=MUTED),
                ], spacing=8), border_radius=5, padding=8, ink=True, on_click=lambda _: self.show_page("user")),
                action_button("退出执行器", lambda _: self.request_exit(), ft.Icons.LOGOUT_ROUNDED),
            ], spacing=8))
        self.compact_nav = CompactSelect(width=150, value="home", options=list(self.TITLES.items()), on_change=lambda e: self.show_page(e.control.value), visible=False)
        self.platform_badge = status_badge("等待连接", WARNING)
        footer = ft.Container(ft.Row([
            ft.Icon(ft.Icons.INFO_OUTLINE, size=12, color=MUTED),
            ft.Container(self.status, expand=True),
            self.platform_badge,
            ft.Text(f"v{settings.SETTINGS.get('version', '-')}", size=11, color=MUTED),
        ], spacing=6), padding=ft.padding.symmetric(horizontal=12, vertical=6),
            bgcolor=SURFACE, border=ft.border.only(top=ft.BorderSide(1, LINE)))
        self.page.controls = [ft.Row([self.sidebar, ft.Column([self.content, footer], expand=True, spacing=0)],
                                    expand=True, spacing=0, vertical_alignment=ft.CrossAxisAlignment.STRETCH)]
        self.page.on_resized = self.resize
        self.tray.start()
        self.bridge.submit(process(self.bridge), on_error=lambda error: self.notify(f"执行器服务异常：{error}"))
        self.show_page("home")
        self.ready = True
        self.page.window.center()

    def show_page(self, key):
        self.current = key
        if hasattr(self, "nav_items"):
            icons = (ft.Icons.GRID_VIEW_ROUNDED, ft.Icons.SUBJECT_ROUNDED, ft.Icons.LANGUAGE_ROUNDED, ft.Icons.ANDROID_ROUNDED, ft.Icons.PHONE_IPHONE_ROUNDED, ft.Icons.DESKTOP_WINDOWS_OUTLINED, ft.Icons.CODE_ROUNDED, ft.Icons.SETTINGS_OUTLINED)
            self.nav_items.controls = []
            for index, ((name, title), icon) in enumerate(zip(list(self.TITLES.items())[:8], icons)):
                if index in (0, 2, 7):
                    label = {0: "工作空间", 2: "执行配置", 7: "系统"}[index]
                    self.nav_items.controls.append(ft.Container(ft.Text(label, size=11, color=MUTED),
                        padding=ft.padding.only(left=10, top=12 if index else 2, bottom=5)))
                active = name == key
                self.nav_items.controls.append(ft.Container(ft.Row([
                    ft.Icon(icon, size=17, color=PRIMARY if active else NAV_MUTED),
                    ft.Text(title, size=13, color=PRIMARY if active else NAV_TEXT,
                            weight=ft.FontWeight.W_600 if active else ft.FontWeight.W_400),
                ], spacing=10), bgcolor=NAV_ACTIVE if active else None, border_radius=5,
                    padding=ft.padding.symmetric(horizontal=10, vertical=9), ink=True,
                    tooltip=title, on_click=lambda _, name=name: self.show_page(name)))
            self.compact_nav.value = key
        if key == "home":
            control = self.home()
        elif key == "logs":
            control = self.log_view()
        elif key == "user":
            self.user_details = ft.Column([ft.Text("正在加载…", size=13, color=MUTED)], spacing=0)
            control = section("用户信息", self.user_details)
            if self.user_id:
                self.bridge.submit(HTTP.user.get_userinfo(self.user_id), self.render_user, lambda error: self.notify(str(error)))
        else:
            control = config_view(self, key)
        descriptions = {"home": "查看平台连接、任务进度和本机运行目录。", "logs": "查看执行消息，按级别和关键词筛选。", "user": "查看当前登录账号与平台信息。"}
        heading = ft.Column([ft.Row([
            ft.Text(self.TITLES[key], size=18, color=TEXT, weight=ft.FontWeight.W_600, expand=True),
            *([status_badge("修改后自动保存", SUCCESS)] if key in {"web", "android", "ios", "pytest"} else []),
            self.compact_nav,
        ], spacing=8), ft.Text(descriptions.get(key, "管理本机执行环境，配置保存后用于后续任务。"), size=12, color=MUTED)], spacing=4)
        body = ft.Container(control, expand=True) if key == "logs" else ft.Column([control], scroll=ft.ScrollMode.AUTO,
            expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, spacing=0)
        self.content.content = ft.Column([heading, body], spacing=12, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.resize(None)
        self.page.update()

    def resize(self, _):
        small = (self.page.width or 1120) < 900
        self.sidebar.visible = not small
        self.compact_nav.visible = small
        self.content.padding = 10 if small else 14
        self.page.update()

    def render_user(self, response):
        if response.code != 200:
            self.user_details.controls = [ft.Text(str(response.msg), size=13, color=WARNING)]
            return
        data = response.data[0] if isinstance(response.data, list) else response.data
        self.user_details.controls = [detail_row(label, data.get(key) or "-") for label, key in
                                      (("昵称", "name"), ("账号", "username"), ("角色", "role"), ("邮箱", "mailbox"))]

    def home(self):
        self.connection = ft.Text("连接正常" if self.connected else "等待连接", size=12,
                                  color=SUCCESS if self.connected else WARNING)
        self.task_info = ft.Text(size=12, color=MUTED)
        self.task_fields = {
            key: detail_row(label, "-") for label, key in (
                ("任务名称", "task_name"), ("任务类型", "task_type"),
                ("执行标识", "task_id"), ("当前动作", "current_action"),
                ("开始时间", "started_at_text"), ("耗时（秒）", "elapsed_seconds"),
            )
        }
        self.recent_result = ft.Text(size=12, color=MUTED, max_lines=2,
                                     overflow=ft.TextOverflow.ELLIPSIS, visible=False)
        self.progress = ft.ProgressBar(value=0, visible=False, color=PRIMARY, bgcolor=LINE, bar_height=4, border_radius=3)
        self.refresh_activity()
        async def set_open(event):
            from mangotools.contracts import ActuatorPresenceUpdate
            from src.network import ActuatorToolsEventEnum, socket_conn
            value = SetConfig.set_open_status(event.control.value)
            socket_conn.sync_send("设置OPEN状态", func_name=ActuatorToolsEventEnum.SET_USERINFO.value, func_args=ActuatorPresenceUpdate(username=SetConfig.get_username(), is_open=value))
        directories = []
        for label, path in (("日志", project_dir.logs()), ("截图", project_dir.screenshot()), ("下载", project_dir.download()), ("视频", project_dir.videos()), ("缓存", project_dir.cache())):
            directories.append(ft.Container(ft.Row([
                ft.Text(label, size=13, width=44),
                ft.Text(str(path), size=12, color=MUTED, expand=True, max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS, tooltip=str(path)),
                action_button("打开", lambda _, path=path: self.open_directory(path)),
                action_button("复制路径", lambda _, path=path: self.page.set_clipboard(str(path))),
            ], spacing=8), padding=ft.padding.symmetric(horizontal=8, vertical=2),
                bgcolor=SOFT if len(directories) % 2 == 0 else None, border_radius=5))
        connection = section("平台连接", self.connection,
            detail_row("账号", SetConfig.get_username() or "-"),
            detail_row("平台地址", SetConfig.get_host() or "-"),
            detail_row("WS 地址", SetConfig.get_ws() or "-"),
            field_row("开放领取任务", ft.Switch(value=bool(settings.IS_OPEN), on_change=set_open)),
            icon=ft.Icons.CLOUD_OUTLINED)
        tasks = section("任务监控", self.task_info,
                        ft.Column(list(self.task_fields.values()), spacing=0),
                        self.progress, self.recent_result, icon=ft.Icons.PLAY_CIRCLE_OUTLINE)
        connection.col = tasks.col = {"xs": 12, "md": 6}
        return ft.Column([
            ft.ResponsiveRow([connection, tasks], spacing=PAGE_GAP, run_spacing=PAGE_GAP),
            section("本机目录", ft.Column(directories, spacing=2), icon=ft.Icons.FOLDER_OPEN_OUTLINED),
        ], spacing=PAGE_GAP, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def refresh_activity(self):
        snapshot = ExecutionActivity.snapshot()
        active, recent = snapshot.get("active") or [], snapshot.get("recent") or []
        task = (active or recent or [{}])[0]
        self.task_info.value = f"运行中 {len(active)} 个任务" if active else "当前空闲，等待任务" if not recent else "当前空闲，显示最近任务"
        for key, row in self.task_fields.items():
            value = task.get(key)
            text = "-" if value is None or value == "" else str(value)
            row.controls[1].value = text
            row.controls[1].tooltip = text
        self.recent_result.visible = bool(recent)
        if recent:
            labels = {"success": "成功", "failed": "失败", "running": "运行中"}
            result = recent[0]
            status = labels.get(result.get("status"), result.get("status") or "-")
            self.recent_result.value = f"最近结果：{status}" + (f" · {result['error_message']}" if result.get("error_message") else "")
            self.recent_result.tooltip = self.recent_result.value
        total = int(task.get("progress_total") or 0)
        self.progress.visible = total > 0
        self.progress.value = min(1, int(task.get("progress_current") or 0) / total) if total else 0

    def log_view(self):
        self.keyword = compact_input(ft.TextField(label="搜索日志", on_change=lambda _: self.render_logs(), col={"xs": 12, "sm": 6}))
        self.level = CompactSelect(label="级别", width=130, value="全部", options=[(v, v) for v in ("全部", "info", "success", "warning", "error")], on_change=lambda _: self.render_logs())
        self.limit = CompactSelect(label="显示条数", width=130, value="500", options=[(v, v) for v in ("200", "500", "1000")], on_change=lambda _: self.render_logs())
        self.level.col = self.limit.col = {"xs": 6, "sm": 3}
        self.level.width = self.limit.width = None
        self.auto_scroll = ft.Switch(label="自动滚动", value=True, adaptive=True)
        self.log_list = ft.ListView(expand=True, spacing=4, auto_scroll=True)
        self.log_empty = ft.Text("暂无实时日志，收到执行消息后会自动显示。", color=CODE_MUTED, size=12)
        self.log_count = ft.Text(color=MUTED, size=12)
        def debug(event):
            settings.IS_DEBUG = bool(event.control.value)
            log.set_debug(settings.IS_DEBUG)
            from mangotools.contracts import ActuatorPresenceUpdate
            from src.network import ActuatorToolsEventEnum, socket_conn
            socket_conn.sync_send("设置DEBUG状态", func_name=ActuatorToolsEventEnum.SET_USERINFO.value, func_args=ActuatorPresenceUpdate(username=SetConfig.get_username(), debug=settings.IS_DEBUG))
        def clear(_):
            self.logs.clear()
            self.render_logs()
        self.render_logs()
        self.debug_switch = ft.Switch(label="调试日志", value=bool(settings.IS_DEBUG), on_change=debug, adaptive=True)
        return ft.Container(
            ft.Column([
                ft.ResponsiveRow([self.keyword, self.level, self.limit], spacing=PAGE_GAP, run_spacing=PAGE_GAP),
                ft.ResponsiveRow([
                    ft.Container(toggle_control(self.debug_switch), col={"xs": 6, "sm": 3}),
                    ft.Container(toggle_control(self.auto_scroll), col={"xs": 6, "sm": 3}),
                    ft.Row([action_button("清空显示", clear), action_button("打开日志目录", lambda _: self.open_directory(project_dir.logs()))], col={"xs": 12, "sm": 6}, spacing=PAGE_GAP),
                ], spacing=PAGE_GAP, run_spacing=4),
                ft.Row([ft.Icon(ft.Icons.TERMINAL_ROUNDED, size=15, color=MUTED),
                        self.log_count], spacing=6),
                ft.Container(ft.Column([self.log_empty, self.log_list], expand=True, spacing=8,
                                      horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                             expand=True, bgcolor=CODE_BG, border_radius=5, padding=12),
            ], spacing=PAGE_GAP, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            bgcolor=SURFACE, border=ft.border.all(1, LINE), padding=12, border_radius=7, expand=True,
        )

    def render_logs(self):
        keyword = (self.keyword.value or "").lower()
        rows = [row for row in self.logs if (self.level.value == "全部" or row[1] == self.level.value) and keyword in row[2].lower()][-int(self.limit.value):]
        self.log_list.controls = [ft.Container(ft.Row([
            ft.Text(time, size=11, color=CODE_MUTED, width=58, selectable=True),
            ft.Text(level.upper(), size=10, color=LOG_COLORS.get(level, CODE_TEXT), width=58),
            ft.Text(text, color=LOG_COLORS.get(level, CODE_TEXT), selectable=True, size=12, expand=True),
        ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.START), padding=ft.padding.symmetric(vertical=3))
            for time, level, text in rows]
        self.log_list.auto_scroll = self.auto_scroll.value
        self.log_empty.visible = not rows
        self.log_empty.value = "没有符合筛选条件的日志。" if self.logs else "暂无实时日志，收到执行消息后会自动显示。"
        self.log_count.value = f"显示 {len(rows)} / 共 {len(self.logs)}"
        if self.ready:
            self.page.update()

    async def pump(self):
        ticks = 0
        while not self.closing:
            for callback, args in self.bridge.drain_callbacks():
                try:
                    callback(*args)
                except Exception:
                    log.error("桌面事件处理失败", exc_info=True)
            dirty_logs = False
            for _ in range(200):
                try:
                    message = global_msg_queue.get_nowait()
                except Empty:
                    break
                if message.type == MessageEnum.REAL_TIME:
                    level = str(getattr(message.level, "name", message.level) or "info").lower()
                    self.logs.append((datetime.now().strftime("%H:%M:%S"), level, str(message.msg)))
                    dirty_logs = True
                elif message.type == MessageEnum.WS_LINK:
                    self.connected = bool(int(message.msg))
                elif message.type in (MessageEnum.BOTTOM, MessageEnum.NOTIFICATION):
                    self.status.value = str(message.msg)
                    self.status.tooltip = str(message.msg)
            if self.ready:
                if ticks % 10 == 0:
                    color = SUCCESS if self.connected else WARNING
                    self.platform_badge.content.controls[0].color = color
                    self.platform_badge.content.controls[1].color = color
                    self.platform_badge.content.controls[1].value = "平台已连接" if self.connected else "等待重连"
                if self.current == "home" and ticks % 10 == 0:
                    self.connection.value = "连接正常" if self.connected else "等待重连"
                    self.connection.color = SUCCESS if self.connected else WARNING
                    self.refresh_activity()
                if self.current == "logs" and dirty_logs:
                    self.render_logs()
                self.page.update()
            ticks += 1
            await asyncio.sleep(0.1)

    @staticmethod
    def open_directory(path):
        Path(path).mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(path))
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])

    def show_window(self):
        self.page.window.visible = True
        self.page.window.minimized = False
        self.page.window.center()
        self.page.window.to_front()

    def window_event(self, event):
        if event.data == "close":
            if self.tray.available:
                self.page.window.visible = False
                self.page.update()
            else:
                self.request_exit()

    def request_exit(self):
        self.confirm("确认停止本机执行服务并退出？", lambda _: self.page.run_task(self.exit))

    async def exit(self):
        if self.closing:
            return
        self.closing = True
        self.tray.stop()
        await asyncio.to_thread(self.bridge.stop)
        self.page.window.destroy()


def run_flet_application():
    RuntimeInstanceLock.acquire_process_lock(f"{project_dir.cache()}/actuator.lock")
    project_dir.cache_file()
    SetConfig.restore_runtime_settings()
    SetConfig.ensure_web_headers_default(False)
    SetConfig.set_web_default(False)
    from src.services.capabilities import CapabilityRegistry
    if "perf" in CapabilityRegistry.enabled_codes():
        from src.services.perf.k6_runtime import ensure_k6_available
        try:
            ensure_k6_available()
        except Exception as error:
            log.warning(f"k6 初始化失败：{error}")
    def start_page(page):
        try:
            FletActuatorApplication(page)
        except Exception:
            log.exception("执行器桌面页面初始化失败")
            page.window.visible = True
            page.update()
            raise

    async def run():
        def report_loop_error(loop, context):
            error = context.get("exception")
            log.error("桌面运行时异步任务失败", exc_info=(type(error), error, error.__traceback__) if error else None)
            loop.default_exception_handler(context)

        asyncio.get_running_loop().set_exception_handler(report_loop_error)
        await ft.app_async(target=start_page, view=ft.AppView.FLET_APP_HIDDEN)

    asyncio.run(run())

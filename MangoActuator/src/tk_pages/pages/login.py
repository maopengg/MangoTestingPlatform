from __future__ import annotations

import asyncio
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox

from src.network import HTTP
from src.tools.set_config import SetConfig
from src.tools.url import is_valid_url, platform_ws_url

from ..components import Button, Checkbutton, ColorFrame, ColorLabel, Entry, Frame, Label, Page


class LoginPage(Page):
    title = "登录"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.configure(padding=0)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        shell = Frame(self, variant="surface")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)
        font_family = tkfont.nametofont("TkDefaultFont").actual("family")

        intro = ColorFrame(shell, tone="nav", width=300, padx=34, pady=36)
        intro.grid(row=0, column=0, sticky="ns")
        intro.grid_propagate(False)
        ColorLabel(
            intro, text="M", width=2, background_tone="primary", foreground_tone="#FFFFFF",
            font=("Arial", 17, "bold"), padx=6, pady=8,
        ).pack(anchor="w")
        ColorLabel(
            intro, text="芒果执行器", background_tone="nav", foreground_tone="#FFFFFF",
            font=(font_family, 20, "bold"),
        ).pack(anchor="w", pady=(22, 6))
        ColorLabel(
            intro, text="为自动化测试提供稳定、可观察的本地执行环境。", background_tone="nav",
            foreground_tone="nav_text", justify="left",
            wraplength=220, font=(font_family, 10),
        ).pack(anchor="w")
        for index, text in enumerate(("连接测试平台", "接收并执行任务", "实时查看运行状态"), start=1):
            row = ColorFrame(intro, tone="nav")
            row.pack(fill="x", pady=(26 if index == 1 else 14, 0))
            ColorLabel(
                row, text=str(index), width=2, background_tone="nav_active", foreground_tone="#FFFFFF",
                font=("Arial", 9, "bold"), padx=2, pady=3,
            ).pack(side="left", padx=(0, 10))
            ColorLabel(
                row, text=text, background_tone="nav", foreground_tone="nav_text",
                font=(font_family, 10),
            ).pack(side="left")
        ColorLabel(
            intro, text="执行器会在系统托盘持续运行", background_tone="nav",
            foreground_tone="nav_muted", font=(font_family, 9),
        ).pack(side="bottom", anchor="w")

        host = SetConfig.get_host() or ""  # type: ignore
        proxy = SetConfig.get_proxy_url() or ""  # type: ignore
        username, password, remember = SetConfig.get_remembered_login()
        self.host_var = tk.StringVar(value=str(host))
        self.proxy_var = tk.StringVar(value=str(proxy if proxy != "None" else ""))
        self.username_var = tk.StringVar(value=username)
        self.password_var = tk.StringVar(value=password)
        self.remember_var = tk.BooleanVar(value=remember)
        self.status_var = tk.StringVar(value="请输入执行器登录信息")
        self._login_in_progress = False

        panel = Frame(shell, variant="surface", padding=(46, 34))
        panel.grid(row=0, column=1, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        Label(panel, text="登录执行器", variant="login_title").grid(row=0, column=0, sticky="w")
        Label(
            panel, text="使用测试平台账号登录，启动本机执行服务。", variant="surface_muted",
        ).grid(row=1, column=0, sticky="w", pady=(6, 20))

        fields = [
            ("服务地址 *", self.host_var, False),
            ("代理地址", self.proxy_var, False),
            ("账号 *", self.username_var, False),
            ("密码 *", self.password_var, True),
        ]
        row = 2
        for label, variable, password_field in fields:
            Label(panel, text=label, variant="form").grid(row=row, column=0, sticky="w")
            row += 1
            entry = Entry(panel, textvariable=variable, show="*" if password_field else "")
            entry.grid(row=row, column=0, sticky="ew", pady=(5, 10))
            row += 1

        Checkbutton(panel, text="记住密码", variable=self.remember_var).grid(row=row, column=0, sticky="w", pady=(0, 10))
        row += 1
        status = ColorLabel(
            panel, textvariable=self.status_var, anchor="w", background_tone="surface_alt",
            foreground_tone="text_secondary", padx=10, pady=7, wraplength=360,
        )
        status.grid(row=row, column=0, sticky="ew", pady=(0, 14))
        row += 1
        buttons = Frame(panel, variant="surface")
        buttons.grid(row=row, column=0, sticky="ew")
        Button(buttons, text="注册账号", variant="link", command=self._open_register).pack(side="left")
        self.login_button = Button(buttons, text="登录", variant="primary", command=self._login)
        self.login_button.pack(side="right", ipadx=12)
        self.bind_all("<Return>", lambda _event: self._login())

    def _validate_endpoint(self) -> tuple[str, str] | None:
        host = is_valid_url(self.host_var.get().strip())
        ws_url = platform_ws_url(host) if host else None
        if not host or not ws_url:
            messagebox.showerror("登录失败", "请输入合法的服务地址，如：http://127.0.0.1:8000/")
            return None
        return host, ws_url

    def _login(self) -> None:
        if self._login_in_progress:
            return
        endpoint = self._validate_endpoint()
        if not endpoint:
            return
        username = self.username_var.get().strip()
        password = self.password_var.get()
        if not username or not password:
            messagebox.showerror("登录失败", "请输入账号和密码")
            return
        host, ws_url = endpoint
        SetConfig.set_host(host)  # type: ignore
        SetConfig.set_ws(ws_url)  # type: ignore
        SetConfig.set_proxy_url(self.proxy_var.get().strip() or None)  # type: ignore
        HTTP.refresh()
        self._set_login_in_progress(True)
        self.status_var.set("正在连接测试平台...")

        async def login_request():
            response = await asyncio.wait_for(HTTP.system.login(username, password), timeout=30)
            if response.code != 200:
                return response, None
            SetConfig.save_login_credentials(username, password, self.remember_var.get())
            HTTP.refresh()
            await HTTP.system.refresh_runtime_config()
            user_id = response.data.get("userId") if isinstance(response.data, dict) else None
            user_response = await HTTP.user.get_userinfo(user_id) if user_id else None
            return response, user_response

        self.app.bridge.submit(login_request(), self._login_finished, self._login_failed)

    def _login_finished(self, result) -> None:
        response, _user_response = result
        self._set_login_in_progress(False)
        if response.code != 200:
            self.status_var.set(str(response.msg or "登录失败"))
            messagebox.showerror("登录失败", str(response.msg or "请检查服务地址和账号密码"))
            return
        user_id = response.data.get("userId") if isinstance(response.data, dict) else None
        self.app.show_main(user_id)

    def _login_failed(self, error: BaseException) -> None:
        self._set_login_in_progress(False)
        self.status_var.set("连接失败")
        messagebox.showerror("登录失败", str(error) or type(error).__name__)

    def _set_login_in_progress(self, active: bool) -> None:
        self._login_in_progress = bool(active)
        self.login_button.configure(state="disabled" if active else "normal", text="登录中..." if active else "登录")

    def _open_register(self) -> None:
        endpoint = self._validate_endpoint()
        if not endpoint:
            return
        host, ws_url = endpoint
        SetConfig.set_host(host)  # type: ignore
        SetConfig.set_ws(ws_url)  # type: ignore
        SetConfig.set_proxy_url(self.proxy_var.get().strip() or None)  # type: ignore
        HTTP.refresh()
        dialog = tk.Toplevel(self)
        dialog.title("注册用户")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        values = {key: tk.StringVar() for key in ("name", "username", "password", "confirm_password")}
        labels = (("用户昵称", "name"), ("用户账号", "username"), ("用户密码", "password"), ("确认密码", "confirm_password"))
        body = Frame(dialog, variant="surface", padding=18)
        body.pack(fill="both", expand=True)
        for row, (label, key) in enumerate(labels):
            Label(body, text=label, variant="surface").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=6)
            Entry(body, textvariable=values[key], show="*" if "password" in key else "", width=30).grid(row=row, column=1, pady=6)

        def submit():
            data = {key: value.get().strip() for key, value in values.items()}
            if not all(data.values()):
                messagebox.showwarning("注册", "请填写全部字段", parent=dialog)
                return
            if data["password"] != data["confirm_password"]:
                messagebox.showwarning("注册", "两次输入的密码不一致", parent=dialog)
                return
            self.app.bridge.submit(
                HTTP.system.user_register(data),
                lambda response: self._register_finished(dialog, response),
                lambda error: messagebox.showerror("注册失败", str(error), parent=dialog),
            )

        Button(body, text="取消", command=dialog.destroy).grid(row=4, column=0, pady=(12, 0))
        Button(body, text="提交", variant="primary", command=submit).grid(row=4, column=1, sticky="e", pady=(12, 0))

    @staticmethod
    def _register_finished(dialog: tk.Toplevel, response) -> None:
        if response.code == 200:
            messagebox.showinfo("注册", str(response.msg or "注册成功"), parent=dialog)
            dialog.destroy()
        else:
            messagebox.showerror("注册失败", str(response.msg or "注册失败"), parent=dialog)

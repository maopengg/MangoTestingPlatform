from __future__ import annotations

from queue import Empty
import tkinter as tk
import traceback
from tkinter import messagebox

from src import process
from src.enums.tools_enum import MessageEnum
from src.services.capabilities import CapabilityRegistry
from src.services.perf.k6_runtime import ensure_k6_available
from src.services.runtime import RuntimeInstanceLock
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.send_global_msg import global_msg_queue
from src.tools.set_config import SetConfig

from .components import Button, ColorLabel, Frame, Label
from .pages import AndroidPage, HomePage, IOSPage, LoginPage, LogsPage, PcPage, PytestPage, SettingsPage, UserPage, WebPage
from .runtime import AsyncRuntimeBridge
from .theme import COLORS, setup_theme
from .tray import TrayController


class TkActuatorApplication:
    POLL_INTERVAL_MS = 100

    def __init__(self, root: tk.Tk | None = None):
        self.root = root or tk.Tk()
        setup_theme(self.root)
        self.root.title("芒果执行器")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = min(1120, max(980, int(screen_width * 0.64)))
        height = min(720, max(620, int(screen_height * 0.68)))
        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)
        self._main_geometry = f"{width}x{height}+{x}+{y}"
        self.root.geometry(self._main_geometry)
        self.root.protocol("WM_DELETE_WINDOW", self.on_window_close)
        try:
            self.root.iconbitmap(project_dir.resource_path("assets/app_icon.ico"))
        except tk.TclError:
            pass
        self.bridge = AsyncRuntimeBridge()
        self.bridge.start()
        self.user_id: int | None = None
        self.pages: dict[str, Frame] = {}
        self.page_container: Frame | None = None
        self.status_var = tk.StringVar(value="就绪")
        self.page_title_var = tk.StringVar(value="")
        self.nav_buttons: dict[str, Button] = {}
        self.account_button: Button | None = None
        self._brand_logo_image = None
        self.tray: TrayController | None = None
        self._main_ready = False
        self._closing = False
        self._hidden_tip_shown = False
        self.show_login()
        self.root.after(self.POLL_INTERVAL_MS, self._poll_events)

    @property
    def loop(self):
        return self.bridge.loop

    def run(self) -> None:
        self.root.mainloop()

    def show_login(self) -> None:
        self._clear_root()
        self.root.minsize(760, 540)
        width, height = 860, 580
        x = max(0, (self.root.winfo_screenwidth() - width) // 2)
        y = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        page = LoginPage(self.root, self)
        page.pack(fill="both", expand=True)

    def show_main(self, user_id: int | None) -> None:
        self.user_id = user_id
        self.root.unbind("<Return>")
        self._clear_root()
        self.root.minsize(980, 640)
        self.root.geometry(self._main_geometry)
        shell = Frame(self.root)
        shell.pack(fill="both", expand=True)
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(1, weight=1)
        navigation = Frame(shell, variant="navigation", padding=(12, 18), width=188)
        navigation.grid(row=0, column=0, sticky="ns", rowspan=2)
        navigation.grid_propagate(False)
        brand = Frame(navigation, variant="navigation")
        brand.pack(fill="x", padx=6, pady=(0, 22))
        self._create_brand_logo(brand).pack(side="left", padx=(0, 10))
        brand_text = Frame(brand, variant="navigation")
        brand_text.pack(side="left")
        Label(brand_text, text="MANGO", variant="brand").pack(anchor="w")
        Label(brand_text, text="自动化执行器", variant="nav_meta").pack(anchor="w")

        workspace = Frame(shell)
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.rowconfigure(0, weight=1)
        workspace.columnconfigure(0, weight=1)
        self.page_container = Frame(workspace)
        self.page_container.grid(row=0, column=0, sticky="nsew")
        self.page_container.rowconfigure(0, weight=1)
        self.page_container.columnconfigure(0, weight=1)
        statusbar = Frame(shell, variant="statusbar", padding=(14, 6))
        statusbar.grid(row=1, column=1, sticky="ew")
        ColorLabel(statusbar, text="●", background_tone="surface", foreground_tone="success", font=("Arial", 8)).pack(side="left", padx=(0, 7))
        Label(statusbar, textvariable=self.status_var, variant="statusbar").pack(side="left")
        Label(statusbar, text="后台任务持续运行", variant="statusbar").pack(side="right")

        definitions = [
            ("home", "运行概览", HomePage),
            ("logs", "实时日志", LogsPage),
        ]
        configuration_pages = [
            ("web", "WEB 配置", WebPage),
            ("android", "Android 配置", AndroidPage), ("ios", "iOS 配置", IOSPage),
            ("pc", "PC 配置", PcPage), ("pytest", "Pytest 配置", PytestPage),
            ("settings", "系统设置", SettingsPage),
        ]
        self.pages = {}
        self.nav_buttons = {}
        Label(navigation, text="监控", variant="nav_meta").pack(anchor="w", padx=8, pady=(0, 5))
        for key, label, page_class in definitions:
            page = page_class(self.page_container, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[key] = page
            button = Button(navigation, text=label, variant="navigation", command=lambda value=key: self.show_page(value))
            button.pack(fill="x", pady=2)
            self.nav_buttons[key] = button
        Label(navigation, text="执行配置", variant="nav_meta").pack(anchor="w", padx=8, pady=(18, 5))
        for key, label, page_class in configuration_pages:
            page = page_class(self.page_container, self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[key] = page
            button = Button(navigation, text=label, variant="navigation", command=lambda value=key: self.show_page(value))
            button.pack(fill="x", pady=2)
            self.nav_buttons[key] = button
        user_page = UserPage(self.page_container, self)
        user_page.grid(row=0, column=0, sticky="nsew")
        self.pages["user"] = user_page
        Button(navigation, text="退出执行器", variant="navigation", command=self.exit).pack(side="bottom", fill="x", pady=2)
        Button(navigation, text="帮助文档", variant="navigation", command=self._open_help).pack(side="bottom", fill="x", pady=2)
        account = Frame(navigation, variant="navigation")
        account.pack(side="bottom", fill="x", padx=10, pady=(8, 12))
        Label(account, text="当前账号", variant="nav_meta").pack(anchor="w")
        self.account_button = Button(
            account,
            text=str(SetConfig.get_username() or "执行器用户"),  # type: ignore
            variant="account",
            command=lambda: self.show_page("user"),
        )
        self.account_button.pack(fill="x", pady=(3, 0))
        self._main_ready = True
        self.show_page("home")
        self._start_tray()
        self.bridge.submit(process(self.bridge), lambda _result: self.set_status("执行器服务已启动"), self._runtime_failed)

    def show_page(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        for name, button in self.nav_buttons.items():
            button.set_variant("navigation_selected" if name == key else "navigation")
        if self.account_button is not None:
            self.account_button.set_variant("account_selected" if key == "user" else "account")
        self.page_title_var.set(getattr(page, "title", ""))
        page.tkraise()
        on_show = getattr(page, "on_show", None)
        if callable(on_show):
            on_show()

    def enqueue_ui(self, callback, *args) -> None:
        self.bridge.callbacks.put((callback, args))

    def set_status(self, text: str) -> None:
        self.status_var.set(str(text))

    def _poll_events(self) -> None:
        if self._closing:
            return
        for callback, args in self.bridge.drain_callbacks():
            try:
                callback(*args)
            except Exception as error:
                from src.services.system_error_reporter import ActuatorSystemErrorReporter

                self.bridge.submit(ActuatorSystemErrorReporter.report(
                    error,
                    f'tk-callback:{getattr(callback, "__name__", type(callback).__name__)}',
                    traceback_text=traceback.format_exc(),
                ))
                log.error(f"执行 tkinter UI 回调失败：{error}")
        while True:
            try:
                message = global_msg_queue.get_nowait()
            except Empty:
                break
            self._handle_message(message)
        self.root.after(self.POLL_INTERVAL_MS, self._poll_events)

    def _handle_message(self, message) -> None:
        if not self._main_ready:
            return
        home: HomePage = self.pages["home"]  # type: ignore[assignment]
        if message.type == MessageEnum.BOTTOM:
            self.set_status(str(message.msg))
        elif message.type == MessageEnum.REAL_TIME:
            logs: LogsPage = self.pages["logs"]  # type: ignore[assignment]
            logs.append_log(str(message.msg), message.level)
        elif message.type == MessageEnum.WS_LINK:
            home.set_link(message.msg)
        elif message.type == MessageEnum.CASE_NAME:
            home.set_case_name(message.msg)
        elif message.type == MessageEnum.EXECUTION_STATE and isinstance(message.msg, dict):
            home.set_execution_state(message.msg)
        elif message.type == MessageEnum.NOTIFICATION:
            self.set_status(str(message.msg))

    def on_window_close(self) -> None:
        if self.tray and self.tray.available:
            self.root.withdraw()
            if not self._hidden_tip_shown:
                self._hidden_tip_shown = True
                messagebox.showinfo("芒果执行器", "执行器仍在后台运行，可从系统托盘重新打开。")
            return
        if messagebox.askyesno("退出", "系统托盘不可用，确认退出执行器？"):
            self.exit()

    def show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def exit(self) -> None:
        if self._closing:
            return
        self._closing = True
        if self.tray:
            self.tray.stop()
        self.bridge.stop()
        self.root.destroy()

    def _start_tray(self) -> None:
        self.tray = TrayController(
            project_dir.resource_path("assets/app_icon.ico"),
            lambda: self.enqueue_ui(self.show_window),
            lambda: self.enqueue_ui(self.exit),
        )
        if not self.tray.start():
            self.set_status("系统托盘不可用，关闭窗口时将提示退出")

    def _create_brand_logo(self, parent):
        try:
            from PIL import Image, ImageTk

            image = Image.open(project_dir.resource_path("assets/app_icon.ico")).convert("RGBA")
            image.thumbnail((34, 34), Image.Resampling.LANCZOS)
            self._brand_logo_image = ImageTk.PhotoImage(image)
            return tk.Label(
                parent,
                image=self._brand_logo_image,
                background=COLORS["nav"],
                borderwidth=0,
                highlightthickness=0,
            )
        except Exception:
            return ColorLabel(
                parent,
                text="M",
                background_tone="primary",
                foreground_tone="#FFFFFF",
                font=("Arial", 12, "bold"),
                width=2,
                padx=3,
                pady=5,
            )

    def _runtime_failed(self, error: BaseException) -> None:
        self.set_status(f"执行器服务启动失败：{error}")
        messagebox.showerror("执行器服务", str(error) or type(error).__name__)

    @staticmethod
    def _open_help() -> None:
        import webbrowser
        webbrowser.open("http://43.142.161.61:8002/")

    def _clear_root(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()


def run_tk_application() -> None:
    RuntimeInstanceLock.acquire_process_lock(f"{project_dir.cache()}/actuator.lock")
    project_dir.cache_file()
    SetConfig.restore_runtime_settings()
    SetConfig.ensure_web_headers_default(False)
    SetConfig.set_web_default(False)  # type: ignore
    if "perf" in CapabilityRegistry.enabled_codes():
        try:
            k6_binary = ensure_k6_available()
            if k6_binary:
                log.info(f"k6 性能引擎已就绪：{k6_binary}")
            else:
                log.warning("k6 性能引擎不可用，本执行器不会承接性能测试")
        except Exception as error:
            log.error(f"k6 性能引擎自动安装失败，本执行器将继续启动但不会承接性能测试：{error}")
    TkActuatorApplication().run()

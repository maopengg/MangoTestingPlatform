from __future__ import annotations

import subprocess
import tkinter as tk
from tkinter import messagebox
from typing import Any

from mangotools.enums import BrowserTypeEnum
from src.enums.ui_enum import DeviceEnum
from src.network import HTTP
from src.tools.set_config import SetConfig

from ..components import (
    Button, Card, ConstrainedFrame, Entry, FormGrid, Frame, Label, LabelFrame,
    Page, ScrollableFrame, Separator, Switch, Text, combo_value, readonly_combo,
    set_combo_by_value,
)


class ConfigPage(Page):
    def save_success(self) -> None:
        self.app.set_status("配置已保存")
        messagebox.showinfo("保存配置", "配置已保存")


class WebPage(ConfigPage):
    title = "WEB 配置"
    browser_options = list(BrowserTypeEnum.obj().items())
    parallel_options = [(value, str(value)) for value in range(1, 21)]
    queue_options = [(value, str(value)) for value in (5, 10, 20, 50, 100, 200)]
    device_options = [(None, "不开启")] + [(name, name) for name in DeviceEnum.obj()]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.rowconfigure(1, weight=1)
        self.header(self.title, "配置浏览器运行方式、并发容量和执行产物策略")
        scroll = ScrollableFrame(self)
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.body.columnconfigure(0, weight=1)
        content = ConstrainedFrame(scroll.body, max_width=1120)
        content.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        card = Card(content.body, "浏览器运行参数", "基础环境、并发容量与执行产物策略")
        card.grid(row=0, column=0, sticky="ew")
        card.body.columnconfigure(0, weight=1)
        form = FormGrid(card.body, bordered=False)
        form.grid(row=0, column=0, sticky="ew")
        self.browser = readonly_combo(form, [label for _, label in self.browser_options])
        self.path = Entry(form)
        self.parallel = readonly_combo(form, [label for _, label in self.parallel_options])
        self.queue_size = readonly_combo(form, [label for _, label in self.queue_options])
        self.h5 = readonly_combo(form, [label for _, label in self.device_options], 34)
        self.web_max = tk.BooleanVar()
        self.recording = tk.BooleanVar()
        self.headless = tk.BooleanVar()
        self.screenshot = tk.BooleanVar()
        self.static_cache = tk.BooleanVar()
        self.auto_save_var = tk.StringVar(value="修改后自动保存")
        form.add("*选择浏览器", self.browser)
        form.add("浏览器路径", self.path, "非必填；留空时自动查找浏览器")
        form.add("*浏览器并行数", self.parallel)
        form.add("*UI 队列容量", self.queue_size, "最多提前缓存的 UI 用例数量")
        form.add("浏览器 H5 模式", self.h5, "测试移动端网页时选择设备")
        form.add("最大化", Switch(
            form, self.web_max, "启动后最大化",
            lambda: self._persist_setting(SetConfig.set_web_max, self.web_max.get(), "最大化"),  # type: ignore
        ))
        form.add("视频录制", Switch(
            form, self.recording, "录制执行视频",
            lambda: self._persist_setting(SetConfig.set_web_recording, self.recording.get(), "视频录制"),  # type: ignore
        ))
        form.add("无头模式", Switch(
            form, self.headless, "后台运行浏览器",
            lambda: self._persist_setting(SetConfig.set_web_headers, self.headless.get(), "无头模式"),  # type: ignore
        ))
        form.add("操作截图上传", Switch(
            form, self.screenshot, "每步操作和断言截图",
            lambda: self._persist_setting(SetConfig.set_web_step_screenshot, self.screenshot.get(), "操作截图上传"),  # type: ignore
        ))
        form.add("静态资源缓存", Switch(
            form, self.static_cache, "缓存脚本、样式、字体和媒体",
            lambda: self._persist_setting(SetConfig.set_web_static_cache_enabled, self.static_cache.get(), "静态资源缓存"),  # type: ignore
        ))
        self.browser.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._persist_combo(self.browser, self.browser_options, SetConfig.set_web_type, "浏览器"),  # type: ignore
        )
        self.parallel.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._persist_combo(self.parallel, self.parallel_options, SetConfig.set_web_parallel, "浏览器并行数"),  # type: ignore
        )
        self.queue_size.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._persist_combo(self.queue_size, self.queue_options, SetConfig.set_ui_queue_size, "UI 队列容量"),  # type: ignore
        )
        self.h5.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._persist_combo(self.h5, self.device_options, SetConfig.set_web_h5, "浏览器 H5 模式"),  # type: ignore
        )
        self.path.bind(
            "<FocusOut>",
            lambda _event: self._persist_setting(SetConfig.set_web_path, self.path.get().strip(), "浏览器路径"),  # type: ignore
        )
        Separator(card.body).grid(row=1, column=0, sticky="ew", pady=(14, 14))
        actions = Frame(card.body, variant="surface")
        actions.grid(row=2, column=0, sticky="ew")
        Label(actions, textvariable=self.auto_save_var, variant="surface_muted").pack(side="left")
        Button(actions, text="重置缓存对象", command=self.reset_runtime).pack(side="right")

    def on_show(self):
        set_combo_by_value(self.browser, self.browser_options, SetConfig.get_web_type())  # type: ignore
        self.path.delete(0, "end")
        self.path.insert(0, str(SetConfig.get_web_path() or ""))  # type: ignore
        set_combo_by_value(self.parallel, self.parallel_options, SetConfig.get_web_parallel())  # type: ignore
        set_combo_by_value(self.queue_size, self.queue_options, SetConfig.get_ui_queue_size())  # type: ignore
        set_combo_by_value(self.h5, self.device_options, SetConfig.get_web_h5())  # type: ignore
        self.web_max.set(bool(SetConfig.get_web_max()))  # type: ignore
        self.recording.set(bool(SetConfig.get_web_recording()))  # type: ignore
        self.headless.set(bool(SetConfig.get_web_headers()))  # type: ignore
        self.screenshot.set(bool(SetConfig.get_web_step_screenshot()))  # type: ignore
        self.static_cache.set(bool(SetConfig.get_web_static_cache_enabled()))  # type: ignore

    def _persist_combo(self, combo, options, setter, label: str):
        selected = combo.current()
        if selected < 0:
            return
        self._persist_setting(setter, options[selected][0], label)

    def _persist_setting(self, setter, value, label: str):
        setter(value)
        message = f"已自动保存：{label}"
        self.auto_save_var.set(message)
        self.app.set_status(message)

    def reset_runtime(self):
        if not messagebox.askyesno("重置缓存对象", "确认重置浏览器运行时缓存对象？"):
            return
        from src.services.ui.case_flow import CaseFlow
        CaseFlow.reset_web_runtime()
        self.app.set_status("浏览器缓存对象已重置")


class AndroidPage(ConfigPage):
    title = "Android 配置"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.header(self.title, "选择本机 Android 设备并检查 ADB 在线状态")
        form = FormGrid(self)
        form.grid(row=1, column=0, sticky="ew")
        self.device_id = Entry(form)
        self.devices = tk.StringVar(value="尚未刷新")
        form.add("设备 ID", self.device_id)
        form.add("刷新设备", Button(form, text="刷新", command=self.refresh_devices))
        form.add("在线设备", Label(form, textvariable=self.devices, variant="surface"))
        Button(self, text="保存配置", variant="primary", command=self.save).grid(row=2, column=0, sticky="e", pady=12)

    def on_show(self):
        self.device_id.delete(0, "end")
        self.device_id.insert(0, str(SetConfig.get_and_equipment() or ""))  # type: ignore

    def save(self):
        SetConfig.set_and_equipment(self.device_id.get().strip())  # type: ignore
        self.save_success()

    @staticmethod
    def _read_devices() -> list[str]:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
        devices = []
        states = {"device": "已连接", "unauthorized": "未授权", "offline": "离线", "no permissions": "无权限"}
        for line in result.stdout.splitlines()[1:]:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                devices.append(f"{parts[0]}({states.get(parts[1], parts[1])})")
        return devices

    def refresh_devices(self):
        self.devices.set("正在刷新...")

        def worker():
            try:
                devices: Any = self._read_devices()
            except Exception as error:
                devices = error
            self.app.enqueue_ui(self._show_devices, devices)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _show_devices(self, result):
        if isinstance(result, Exception):
            self.devices.set("刷新失败")
            messagebox.showerror("ADB 设备", str(result))
        else:
            self.devices.set("、".join(result) if result else "未发现在线设备")


class IOSPage(ConfigPage):
    title = "iOS 配置"
    fields = (
        ("Appium 地址", "ios_appium_url"), ("设备名称", "ios_device_name"),
        ("UDID", "ios_udid"), ("系统版本", "ios_platform_version"),
        ("开发团队 ID", "ios_xcode_org_id"), ("WDA Bundle ID", "ios_wda_bundle_id"),
    )

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.header(self.title, "配置 Appium、XCUITest 设备和真机签名信息")
        form = FormGrid(self)
        form.grid(row=1, column=0, sticky="ew")
        self.entries = {}
        for label, key in self.fields:
            entry = Entry(form)
            self.entries[key] = entry
            form.add(label, entry)
        Button(self, text="保存配置", variant="primary", command=self.save).grid(row=2, column=0, sticky="e", pady=12)

    def on_show(self):
        for _label, key in self.fields:
            entry = self.entries[key]
            entry.delete(0, "end")
            entry.insert(0, str(getattr(SetConfig, f"get_{key}")() or ""))

    def save(self):
        for _label, key in self.fields:
            getattr(SetConfig, f"set_{key}")(self.entries[key].get().strip())
        self.save_success()


class PcPage(ConfigPage):
    title = "PC 配置"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.header(self.title, "管理 Windows 桌面自动化运行参数")
        empty = Frame(self, variant="card", padding=(20, 24))
        empty.grid(row=1, column=0, sticky="ew")
        Label(empty, text="暂未开放 PC 执行配置", variant="section").pack(anchor="w")
        Label(empty, text="后续配置项将在此处展示。", variant="surface_muted").pack(anchor="w", pady=(6, 0))


class PytestPage(ConfigPage):
    title = "Pytest 配置"
    parallel_options = [(value, str(value)) for value in (1, 2, 3, 5, 10, 20)]
    queue_options = [(value, str(value)) for value in (5, 10, 20, 50, 100, 200)]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.header(self.title, "控制脚本用例并行执行数量和本地预取容量")
        form = FormGrid(self)
        form.grid(row=1, column=0, sticky="ew")
        self.parallel = readonly_combo(form, [label for _, label in self.parallel_options])
        self.queue_size = readonly_combo(form, [label for _, label in self.queue_options])
        form.add("*Pytest 并行数", self.parallel, "同时执行的 Pytest 用例数量")
        form.add("*Pytest 队列容量", self.queue_size, "最多提前缓存的 Pytest 用例数量")
        Button(self, text="保存配置", variant="primary", command=self.save).grid(row=2, column=0, sticky="e", pady=12)

    def on_show(self):
        set_combo_by_value(self.parallel, self.parallel_options, SetConfig.get_pytest_parallel())  # type: ignore
        set_combo_by_value(self.queue_size, self.queue_options, SetConfig.get_pytest_queue_size())  # type: ignore

    def save(self):
        parallel = combo_value(self.parallel, self.parallel_options)
        queue_size = combo_value(self.queue_size, self.queue_options)
        if parallel is None or queue_size is None:
            messagebox.showwarning("保存配置", "请选择并行数和队列容量")
            return
        SetConfig.set_pytest_parallel(parallel)  # type: ignore
        SetConfig.set_pytest_queue_size(queue_size)  # type: ignore
        self.save_success()


class SettingsPage(ConfigPage):
    title = "系统设置"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.header(self.title, "查看执行器桌面环境和基础运行设置")
        box = LabelFrame(self, text="UI自动化配置")
        box.grid(row=1, column=0, sticky="ew")
        Label(box, text="当前没有额外的系统配置项。", variant="surface").pack(anchor="w")
        Button(box, text="测试界面输出", command=self._test_output).pack(anchor="w", pady=(10, 6))
        self.output = Text(
            box, height=8, state="disabled", wrap="word", padx=10, pady=8,
        )
        self.output.pack(fill="x")

    def _test_output(self):
        self.output.configure(state="normal")
        self.output.insert("end", "tkinter 界面输出正常。\n")
        self.output.see("end")
        self.output.configure(state="disabled")


class UserPage(Page):
    title = "用户信息"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.header(self.title, "查看当前登录账号和平台角色信息")
        self.form = FormGrid(self)
        self.form.grid(row=1, column=0, sticky="ew")
        self.values = {key: tk.StringVar(value="-") for key in ("avatar", "name", "username", "role", "mailbox")}
        for label, key in (("头像", "avatar"), ("昵称", "name"), ("账号", "username"), ("角色", "role"), ("邮箱", "mailbox")):
            self.form.add(label, Label(self.form, textvariable=self.values[key], variant="surface"))

    def on_show(self):
        user_id = self.app.user_id
        if user_id:
            self.app.bridge.submit(HTTP.user.get_userinfo(user_id), self._render, self._failed)

    def _render(self, response):
        if response.code != 200 or not response.data:
            self._failed(RuntimeError(str(response.msg or "获取用户信息失败")))
            return
        data = response.data[0] if isinstance(response.data, list) else response.data
        role = data.get("role") or {}
        mailbox = data.get("mailbox") or []
        self.values["avatar"].set("-")
        self.values["name"].set(str(data.get("name") or "-"))
        self.values["username"].set(str(data.get("username") or "-"))
        self.values["role"].set(str(role.get("name") if isinstance(role, dict) else role or "-"))
        self.values["mailbox"].set("、".join(mailbox) if isinstance(mailbox, list) else str(mailbox or "-"))

    def _failed(self, error):
        messagebox.showerror("用户信息", str(error))

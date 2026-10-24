from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
import tkinter as tk

from mangotools.contracts import ActuatorPresenceUpdate
from src.network import ActuatorToolsEventEnum, socket_conn
from src.settings import settings
from src.tools import project_dir
from src.tools.execution_activity import ExecutionActivity
from src.tools.set_config import SetConfig

from ..components import Button, Card, Frame, Label, Page, Progressbar, StatusBadge, Switch


class HomePage(Page):
    title = "运行概览"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.rowconfigure(1, weight=1)
        self.current_task: dict | None = None
        self.header(self.title, "查看平台连接、任务进度和本机运行目录")

        content = Frame(self)
        content.grid(row=1, column=0, sticky="nsew")
        content.rowconfigure(0, weight=1)
        content.columnconfigure(0, weight=1, uniform="overview")
        content.columnconfigure(1, weight=1, uniform="overview")
        self._build_connection(content)
        self._build_execution(content)
        self._build_directories(content)
        self.after(1000, self._tick_elapsed)

    def _build_connection(self, parent):
        card = Card(parent, "连接状态", "平台通信与任务接收策略")
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 12))
        frame = card.body
        frame.columnconfigure(1, weight=1)
        self.connection_vars = {
            "status": tk.StringVar(value="等待连接"),
            "username": tk.StringVar(value=str(SetConfig.get_username() or "-")),  # type: ignore
            "host": tk.StringVar(value=str(SetConfig.get_host() or "-")),  # type: ignore
            "ws": tk.StringVar(value=str(SetConfig.get_ws() or "-")),  # type: ignore
            "mode": tk.StringVar(value="开放领取" if settings.IS_OPEN else "仅定向任务"),
        }
        Label(frame, text="连接状态", variant="surface_muted").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=3
        )
        self.connection_status = StatusBadge(
            frame, textvariable=self.connection_vars["status"], tone="warning",
        )
        self.connection_status.grid(row=0, column=1, sticky="w", pady=3)
        rows = (("登录账号", "username"), ("平台地址", "host"), ("WS 地址", "ws"), ("接收模式", "mode"))
        for row, (label, key) in enumerate(rows, start=1):
            Label(frame, text=label, variant="surface_muted").grid(row=row, column=0, sticky="nw", padx=(0, 12), pady=3)
            Label(frame, textvariable=self.connection_vars[key], variant="surface", wraplength=380).grid(row=row, column=1, sticky="w", pady=3)
        controls = Frame(frame, variant="surface")
        controls.grid(row=len(rows) + 1, column=0, columnspan=2, sticky="w", pady=(10, 0))
        self.open_var = tk.BooleanVar(value=bool(settings.IS_OPEN))
        Switch(controls, self.open_var, "开放领取", self._set_open).pack(side="left")

    def _build_execution(self, parent):
        card = Card(parent, "任务监控", "当前执行进度与最近一次结果")
        card.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=(0, 12))
        frame = card.body
        frame.columnconfigure(1, weight=1)
        self.task_vars = {key: tk.StringVar(value="-") for key in ("status", "count", "name", "type", "id", "action", "started", "elapsed", "recent")}
        self.task_vars["status"].set("空闲")
        self.task_vars["count"].set("当前没有运行中的任务")
        self.task_status = StatusBadge(frame, textvariable=self.task_vars["status"], tone="success")
        self.task_status.grid(row=0, column=0, sticky="w")
        Label(frame, textvariable=self.task_vars["count"], variant="surface").grid(row=0, column=1, sticky="w")
        rows = (("任务名称", "name"), ("任务类型", "type"), ("执行标识", "id"), ("当前动作", "action"), ("开始时间", "started"), ("已用时间", "elapsed"))
        for row, (label, key) in enumerate(rows, start=1):
            Label(frame, text=label, variant="surface_muted").grid(row=row, column=0, sticky="nw", padx=(0, 10), pady=3)
            Label(frame, textvariable=self.task_vars[key], variant="surface", wraplength=350).grid(row=row, column=1, sticky="w", pady=3)
        self.progress_frame = Frame(frame, variant="surface")
        self.progress_frame.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        self.progress = Progressbar(self.progress_frame, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)
        self.progress_text = tk.StringVar(value="")
        self.progress_label = Label(self.progress_frame, textvariable=self.progress_text, variant="surface")
        self.progress_label.pack(side="left", padx=(8, 0))
        self.progress_frame.grid_remove()
        Label(frame, textvariable=self.task_vars["recent"], variant="surface", wraplength=430).grid(row=8, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.task_vars["recent"].set("最近结果：暂无执行记录")

    def _build_directories(self, parent):
        card = Card(parent, "本机目录", "快速访问执行器产生的本地文件")
        card.grid(row=1, column=0, columnspan=2, sticky="ew")
        frame = card.body
        paths = (("日志", project_dir.logs()), ("截图", project_dir.screenshot()), ("下载", project_dir.download()), ("视频", project_dir.videos()), ("缓存", project_dir.cache()))
        for column in range(3):
            frame.columnconfigure(column, weight=1, uniform="directory")
        for index, (title, path) in enumerate(paths):
            row, column = divmod(index, 3)
            item = Frame(frame, variant="directory", padding=(12, 9))
            item.grid(
                row=row,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 5, 0 if column == 2 else 5),
                pady=(0 if row == 0 else 5, 0 if row == 1 else 5),
            )
            item.columnconfigure(0, weight=1, minsize=56)
            Label(item, text=title, variant="directory").grid(row=0, column=0, sticky="w")
            Button(
                item, text="打开", width=4, variant="directory_link",
                command=lambda value=path: self.open_directory(value),
            ).grid(row=0, column=1, padx=(8, 0))
            Button(
                item, text="复制", width=4, variant="directory_link",
                command=lambda value=path: self.copy_path(value),
            ).grid(row=0, column=2, padx=(2, 0))

    def on_show(self):
        self.connection_vars["username"].set(str(SetConfig.get_username() or "-"))  # type: ignore
        self.connection_vars["host"].set(str(SetConfig.get_host() or "-"))  # type: ignore
        self.connection_vars["ws"].set(str(SetConfig.get_ws() or "-"))  # type: ignore
        self.set_execution_state(ExecutionActivity.snapshot())

    def set_link(self, value):
        connected = bool(int(value))
        self.connection_vars["status"].set("连接正常" if connected else "等待重连")
        self.connection_status.set_tone("success" if connected else "warning")

    def set_case_name(self, value):
        if value and not self.current_task:
            self.task_vars["name"].set(str(value))

    def set_execution_state(self, snapshot: dict):
        active = snapshot.get("active") or []
        recent = snapshot.get("recent") or []
        task = active[0] if active else None
        self.current_task = task
        if task:
            self.task_vars["status"].set("执行中")
            self.task_status.set_tone("info")
            self.task_vars["count"].set(f"运行中 {len(active)} 个任务")
            self._render_task(task)
        else:
            self.task_vars["status"].set("空闲")
            self.task_status.set_tone("success")
            self.task_vars["count"].set("当前没有运行中的任务")
            self.progress_frame.grid_remove()
            if recent:
                self._render_task(recent[0])
            else:
                self.task_vars["name"].set("等待平台下发任务")
                for key in ("type", "id", "action", "started", "elapsed"):
                    self.task_vars[key].set("-")
        if recent:
            latest = recent[0]
            result = "成功" if latest.get("status") == "success" else "失败"
            error = f" · {latest.get('error_message')}" if latest.get("error_message") else ""
            self.task_vars["recent"].set(
                f"最近结果：{result} · {latest.get('task_name', '-')} · {latest.get('elapsed_seconds', 0)} 秒{error}"
            )
        else:
            self.task_vars["recent"].set("最近结果：暂无执行记录")

    def _render_task(self, task: dict):
        values = {
            "name": task.get("task_name") or "未命名任务", "type": task.get("task_type") or "-",
            "id": task.get("task_id") or "-", "action": task.get("current_action") or "-",
            "started": task.get("started_at_text") or "-", "elapsed": self._format_elapsed(int(task.get("elapsed_seconds") or 0)),
        }
        for key, value in values.items():
            self.task_vars[key].set(str(value))
        total = int(task.get("progress_total") or 0)
        current = int(task.get("progress_current") or 0)
        if total > 0:
            self.progress.configure(maximum=total, value=min(current, total))
            self.progress_text.set(f"{current} / {total}")
            self.progress_frame.grid()
        else:
            self.progress_frame.grid_remove()

    def _tick_elapsed(self):
        if self.current_task and self.current_task.get("started_at"):
            elapsed = max(0, int(time.time() - float(self.current_task["started_at"])))
            self.task_vars["elapsed"].set(self._format_elapsed(elapsed))
        self.after(1000, self._tick_elapsed)

    def _set_open(self):
        is_open = SetConfig.set_open_status(self.open_var.get())
        self.connection_vars["mode"].set("开放领取" if is_open else "仅定向任务")
        socket_conn.sync_send(
            "设置OPEN状态", func_name=ActuatorToolsEventEnum.SET_USERINFO.value,
            func_args=ActuatorPresenceUpdate(username=SetConfig.get_username(), is_open=is_open),  # type: ignore
        )

    def copy_path(self, path: str):
        self.clipboard_clear()
        self.clipboard_append(str(path))
        self.app.set_status("路径已复制")

    @staticmethod
    def open_directory(path: str):
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(directory))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(directory)])
        else:
            subprocess.Popen(["xdg-open", str(directory)])

    @staticmethod
    def _format_elapsed(seconds: int) -> str:
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

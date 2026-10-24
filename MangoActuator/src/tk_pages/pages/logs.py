from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import tkinter as tk

from src.enums.gui_enum import TipsTypeEnum
from mangotools.contracts import ActuatorPresenceUpdate
from src.network import ActuatorToolsEventEnum, socket_conn
from src.settings import settings
from src.tools import project_dir
from src.tools.log_collector import log
from src.tools.set_config import SetConfig

from ..components import (
    AutoHideScrollbar, Button, Card, ColorLabel, Combobox, Entry, Frame, Label,
    Page, Switch, Text,
)


LOG_LIMIT = 2000
HISTORY_LOAD_LIMIT = 300
DEFAULT_DISPLAY_LIMIT = 500
DISPLAY_LIMITS = (200, 500, 1000)

LEVEL_LABELS = {
    "info": "INFO ",
    "success": "PASS ",
    "warning": "WARN ",
    "error": "ERROR",
}
LEVEL_FILTERS = {
    "全部级别": None,
    "信息": "info",
    "成功": "success",
    "警告": "warning",
    "错误": "error",
}
LOCAL_LOG_PATTERN = re.compile(
    r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+"
    r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d+)?)\]"
    r"\[[^\]]*\]\s*(.*)$"
)
SOURCE_PATTERN = re.compile(r"^\[([^\]]{1,24})\]\s*(.*)$")


@dataclass(frozen=True)
class LogEntry:
    timestamp: str
    level: str
    source: str
    message: str
    sort_key: str = ""


def _tail_lines(path: Path, limit: int) -> list[str]:
    """Read a bounded number of lines without loading a potentially huge log file."""
    if limit <= 0 or not path.is_file():
        return []
    with path.open("rb") as file:
        file.seek(0, os.SEEK_END)
        position = file.tell()
        chunks: list[bytes] = []
        line_count = 0
        while position > 0 and line_count <= limit:
            size = min(8192, position)
            position -= size
            file.seek(position)
            chunk = file.read(size)
            chunks.append(chunk)
            line_count += chunk.count(b"\n")
    return b"".join(reversed(chunks)).decode("utf-8", errors="replace").splitlines()[-limit:]


def _level_name(level, message: str) -> str:
    if isinstance(level, TipsTypeEnum):
        level = level.name
    elif isinstance(level, int):
        try:
            level = TipsTypeEnum(level).name
        except ValueError:
            level = None
    if level:
        normalized = str(level).lower()
        if normalized in {"error", "critical", "fail"}:
            return "error"
        if normalized in {"warning", "warn"}:
            return "warning"
        if normalized in {"success", "response"}:
            return "success"
        if normalized in {"info", "debug"}:
            return "info"
    if any(word in message for word in ("失败", "异常", "错误", "未找到", "已断开")):
        return "error"
    if any(word in message for word in ("警告", "超时", "队列已满", "自动关闭")):
        return "warning"
    if any(word in message for word in ("成功", "完成", "通过", "已打开", "已连接")):
        return "success"
    return "info"


def _content_parts(message: str) -> tuple[str, str]:
    text = " ".join(str(message).strip().split())
    if text.startswith("UI-"):
        return "UI", text[3:].strip()
    if text.lower().startswith("pytest") or "Pytest" in text[:16]:
        return "Pytest", text
    source_match = SOURCE_PATTERN.match(text)
    if source_match:
        return source_match.group(1), source_match.group(2)
    if any(word in text[:24] for word in ("UI", "浏览器", "页面", "元素")):
        return "UI", text
    return "系统", text


def parse_local_log(line: str) -> LogEntry | None:
    match = LOCAL_LOG_PATTERN.match(line.strip())
    if not match:
        return None
    raw_level, raw_time, content = match.groups()
    source, message = _content_parts(content)
    level = {
        "WARNING": "warning",
        "ERROR": "error",
        "CRITICAL": "error",
    }.get(raw_level, "info")
    return LogEntry(
        timestamp=raw_time[5:19],
        level=level,
        source=source,
        message=message,
        sort_key=raw_time,
    )


class LogsPage(Page):
    title = "实时日志"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.rowconfigure(1, weight=1)
        self.logs: deque[LogEntry] = deque(maxlen=LOG_LIMIT)
        self.header(self.title, "聚合执行步骤、运行状态、警告与错误，支持筛选和检索")

        card = Card(self, "执行日志", f"保留最近 {LOG_LIMIT:,} 条；启动时载入最近 {HISTORY_LOAD_LIMIT} 条本地记录")
        card.grid(row=1, column=0, sticky="nsew")
        card.body.rowconfigure(1, weight=1)
        card.body.columnconfigure(0, weight=1)
        Button(card.actions, text="清空", variant="link", command=self.clear_logs).pack(side="right")
        Button(
            card.actions,
            text="打开目录",
            variant="link",
            command=lambda: self.open_directory(project_dir.logs()),
        ).pack(side="right", padx=(0, 8))
        self.log_count_var = tk.StringVar(value="显示 0 / 共 0")
        Label(card.actions, textvariable=self.log_count_var, variant="log_meta").pack(
            side="right", padx=(0, 12)
        )

        filters = Frame(card.body, variant="log_toolbar", padding=(12, 8))
        filters.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        filters.columnconfigure(5, weight=1)
        Label(filters, text="级别", variant="log_toolbar_muted").grid(row=0, column=0, sticky="w")
        self.level_var = tk.StringVar(value="全部级别")
        level_filter = Combobox(
            filters, textvariable=self.level_var, values=tuple(LEVEL_FILTERS), state="readonly",
            width=9, variant="log_toolbar",
        )
        level_filter.grid(row=0, column=1, padx=(7, 14))
        Label(filters, text="范围", variant="log_toolbar_muted").grid(row=0, column=2, sticky="w")
        self.limit_var = tk.StringVar(value=f"最近 {DEFAULT_DISPLAY_LIMIT} 条")
        limit_filter = Combobox(
            filters,
            textvariable=self.limit_var,
            values=tuple(f"最近 {value} 条" for value in DISPLAY_LIMITS),
            state="readonly",
            width=12,
            variant="log_toolbar",
        )
        limit_filter.grid(row=0, column=3, padx=(7, 14))
        Label(filters, text="搜索", variant="log_toolbar_muted").grid(row=0, column=4, sticky="w")
        self.search_var = tk.StringVar(value="")
        search_entry = Entry(filters, textvariable=self.search_var, width=18, variant="log_toolbar")
        search_entry.grid(row=0, column=5, sticky="ew", padx=(7, 0))

        behavior = Frame(filters, variant="surface")
        behavior.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        self.debug_var = tk.BooleanVar(value=bool(settings.IS_DEBUG))
        Switch(behavior, self.debug_var, "调试日志", self._set_debug).pack(side="left")
        self.auto_scroll_var = tk.BooleanVar(value=True)
        Switch(behavior, self.auto_scroll_var, "跟随最新").pack(side="left", padx=(18, 0))
        Label(
            behavior, text="调试日志会记录更多运行细节，仅建议排障时开启",
            variant="log_toolbar_muted",
        ).pack(side="right")

        self.log_text = Text(
            card.body,
            variant="log",
            wrap="none",
            state="disabled",
            insertbackground="#FFFFFF",
            font="TkFixedFont",
            padx=14,
            pady=12,
            spacing1=2,
            spacing3=3,
        )
        self.log_text.tag_configure("timestamp", foreground="#7F8A9C")
        self.log_text.tag_configure("source", foreground="#9FB2CC")
        self.log_text.tag_configure("info", foreground="#83B4FF")
        self.log_text.tag_configure("success", foreground="#64D9A7")
        self.log_text.tag_configure("warning", foreground="#F4BD69")
        self.log_text.tag_configure("error", foreground="#FF8585")
        yscroll = AutoHideScrollbar(
            card.body,
            orient="vertical",
            command=self.log_text.yview,
        )
        xscroll = AutoHideScrollbar(
            card.body,
            orient="horizontal",
            command=self.log_text.xview,
        )
        self.log_text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.log_text.grid(row=1, column=0, sticky="nsew")
        self.log_placeholder = ColorLabel(
            card.body,
            background_tone="log",
            foreground_tone="#7F8A9C",
            text="等待任务下发\n执行日志将在这里实时显示",
            justify="center",
            padx=18,
            pady=12,
        )
        yscroll.grid(row=1, column=1, sticky="ns")
        xscroll.grid(row=2, column=0, sticky="ew")
        level_filter.bind("<<ComboboxSelected>>", lambda _event: self._render_logs())
        limit_filter.bind("<<ComboboxSelected>>", lambda _event: self._render_logs())
        self.search_var.trace_add("write", lambda *_args: self._schedule_render())
        self._render_after_id = None
        self._load_recent_logs()

    def on_show(self) -> None:
        self.debug_var.set(bool(settings.IS_DEBUG))

    def _set_debug(self) -> None:
        settings.IS_DEBUG = bool(self.debug_var.get())
        log.set_debug(settings.IS_DEBUG)
        socket_conn.sync_send(
            "设置DEBUG状态",
            func_name=ActuatorToolsEventEnum.SET_USERINFO.value,
            func_args=ActuatorPresenceUpdate(
                username=SetConfig.get_username(), debug=settings.IS_DEBUG,  # type: ignore
            ),
        )
        status = "已开启" if settings.IS_DEBUG else "已关闭"
        self.app.set_status(f"调试日志{status}")

    def _load_recent_logs(self) -> None:
        directory = Path(project_dir.logs())
        entries: list[LogEntry] = []
        filenames = ["info-log.log", "warning-log.log", "error-log.log", "critical-log.log"]
        if settings.IS_DEBUG:
            filenames.insert(0, "debug-log.log")
        for filename in filenames:
            for line in _tail_lines(directory / filename, HISTORY_LOAD_LIMIT):
                entry = parse_local_log(line)
                if entry:
                    entries.append(entry)
        entries.sort(key=lambda entry: entry.sort_key)
        self.logs.extend(entries[-HISTORY_LOAD_LIMIT:])
        self._schedule_render()

    def append_log(self, text: str, level=None) -> None:
        if not text:
            return
        for raw_line in str(text).splitlines() or [str(text)]:
            source, message = _content_parts(raw_line)
            if not message:
                continue
            self.logs.append(LogEntry(
                timestamp=time.strftime("%m-%d %H:%M:%S"),
                level=_level_name(level, message),
                source=source,
                message=message,
                sort_key=datetime.now().isoformat(timespec="milliseconds"),
            ))
        self._schedule_render()

    def _schedule_render(self) -> None:
        if self._render_after_id:
            self.after_cancel(self._render_after_id)
        self._render_after_id = self.after(120, self._render_logs)

    def _filtered_logs(self) -> list[LogEntry]:
        selected_level = LEVEL_FILTERS.get(self.level_var.get())
        keyword = self.search_var.get().strip().casefold()
        entries = [
            entry for entry in self.logs
            if (selected_level is None or entry.level == selected_level)
            and (not keyword or keyword in f"{entry.source} {entry.message}".casefold())
        ]
        match = re.search(r"(\d+)", self.limit_var.get())
        display_limit = int(match.group(1)) if match else DEFAULT_DISPLAY_LIMIT
        return entries[-display_limit:]

    def _render_logs(self) -> None:
        self._render_after_id = None
        visible = self._filtered_logs()
        errors = sum(entry.level == "error" for entry in self.logs)
        warnings = sum(entry.level == "warning" for entry in self.logs)
        self.log_count_var.set(
            f"显示 {len(visible):,} / 共 {len(self.logs):,} · 错误 {errors:,} · 警告 {warnings:,}"
        )
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for entry in visible:
            self.log_text.insert("end", entry.timestamp, "timestamp")
            self.log_text.insert("end", "  ")
            self.log_text.insert("end", LEVEL_LABELS[entry.level], entry.level)
            self.log_text.insert("end", f"  [{entry.source}]", "source")
            self.log_text.insert("end", f"  {entry.message}\n")
        self.log_text.configure(state="disabled")
        if visible:
            self.log_placeholder.place_forget()
            if self.auto_scroll_var.get():
                self.log_text.see("end")
        else:
            placeholder = "等待任务下发\n执行日志将在这里实时显示" if not self.logs else "没有符合当前筛选条件的日志"
            self._show_placeholder(placeholder)

    def clear_logs(self) -> None:
        self.logs.clear()
        self._render_logs()

    def _show_placeholder(self, text: str) -> None:
        self.log_placeholder.configure(text=text)
        self.log_placeholder.place(relx=0.5, rely=0.5, anchor="center")

    @staticmethod
    def open_directory(path: str) -> None:
        directory = Path(path)
        directory.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(directory))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(directory)])
        else:
            subprocess.Popen(["xdg-open", str(directory)])

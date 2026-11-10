import asyncio
import platform
import subprocess
import sys

import flet as ft
from mangotools.enums import BrowserTypeEnum

from src.enums.ui_enum import DeviceEnum
from src.tools.set_config import SetConfig
from src.tools import project_dir
from src.settings import settings
from .theme import (
    PAGE_GAP, MUTED, SELECT_WIDTH_SHORT, SELECT_WIDTH_MEDIUM, SELECT_WIDTH_LONG,
    action_button, detail_row, empty_panel, field_row, section,
)
from .select import CompactSelect


def config_view(app, name):
    controls = []

    def setting(label, key, options=None, boolean=False):
        value = getattr(SetConfig, f"get_{key}")()

        def save(event):
            try:
                selected = event.control.value
                if options is not None:
                    selected = next(v for v, _ in options if str(v) == selected)
                getattr(SetConfig, f"set_{key}")(selected)
                app.notify(f"已保存：{label}", popup=False)
            except Exception as error:
                app.notify(f"保存失败：{error}")

        if boolean:
            control = ft.Switch(value=bool(value), on_change=save)
        elif options is not None:
            width = SELECT_WIDTH_LONG if key == "web_h5" else SELECT_WIDTH_MEDIUM if key == "web_type" else SELECT_WIDTH_SHORT
            control = CompactSelect(value=str(value), options=[(str(v), text) for v, text in options], on_change=save, width=width)
        else:
            control = ft.TextField(value=str(value or ""), on_blur=save, on_submit=save)
        controls.append(field_row(label, control))

    groups = []

    def group(title, description, icon):
        groups.append(section(title, *controls, description=description, icon=icon))
        controls.clear()

    if name == "web":
        setting("浏览器", "web_type", list(BrowserTypeEnum.obj().items()))
        setting("浏览器路径", "web_path")
        setting("浏览器并行数", "web_parallel", [(i, str(i)) for i in range(1, 21)])
        setting("UI 队列容量", "ui_queue_size", [(i, str(i)) for i in (5, 10, 20, 50, 100, 200)])
        setting("H5 设备", "web_h5", [(None, "不开启")] + [(i, i) for i in DeviceEnum.obj()])
        group("浏览器与调度", "选择浏览器、移动端模拟设备及用例调度容量。", ft.Icons.LANGUAGE_ROUNDED)
        for label, key in (("最大化", "web_max"), ("视频录制", "web_recording"), ("无头模式", "web_headers"), ("操作截图上传", "web_step_screenshot"), ("静态资源缓存", "web_static_cache_enabled")):
            setting(label, key, boolean=True)
        group("执行与证据", "控制浏览器显示、录制、截图上传及资源缓存。", ft.Icons.TUNE_ROUNDED)

        def reset(_):
            from src.services.ui.case_flow import CaseFlow
            CaseFlow.reset_web_runtime()
            app.notify("浏览器缓存对象已重置")
        groups.append(ft.Row([
            ft.Text("运行配置修改后用于后续新建的浏览器会话。", size=12, color=MUTED, expand=True),
            action_button("重置缓存对象", lambda _: app.confirm("确认重置浏览器运行时缓存对象？", reset), ft.Icons.REFRESH_ROUNDED),
        ], spacing=8))
    elif name == "android":
        setting("设备 ID", "and_equipment")
        output = ft.Text("尚未刷新")
        async def refresh(event):
            event.control.disabled = True
            output.value = "正在刷新设备…"
            app.page.update()
            try:
                result = await asyncio.to_thread(subprocess.run, ["adb", "devices"], capture_output=True, text=True, timeout=10, check=True)
                output.value = result.stdout.strip() or "未发现设备"
            except Exception as error:
                output.value = f"刷新失败：{error}"
            finally:
                event.control.disabled = False
                app.page.update()
        controls.extend([ft.Row([action_button("刷新设备", refresh)]), output])
        group("设备连接", "填写 ADB 设备标识；刷新设备可检查本机连接。", ft.Icons.ANDROID_ROUNDED)
    elif name == "ios":
        for label, key in (("Appium 地址", "ios_appium_url"), ("设备名称", "ios_device_name"), ("UDID", "ios_udid"), ("系统版本", "ios_platform_version"), ("开发团队 ID", "ios_xcode_org_id"), ("WDA Bundle ID", "ios_wda_bundle_id")):
            setting(label, key)
        group("设备与 Appium", "配置已授权设备与本机 Appium / WebDriverAgent 环境。", ft.Icons.PHONE_IPHONE_ROUNDED)
    elif name == "pytest":
        setting("Pytest 并行数", "pytest_parallel", [(i, str(i)) for i in (1, 2, 3, 5, 10, 20)])
        setting("Pytest 队列容量", "pytest_queue_size", [(i, str(i)) for i in (5, 10, 20, 50, 100, 200)])
        group("任务调度", "并行数控制同时运行数量，队列容量控制提前缓存数量。", ft.Icons.CODE_ROUNDED)
    elif name == "pc":
        return empty_panel("PC 执行配置暂未开放", "当前版本尚未提供 PC 专用配置项，可继续使用其他已安装的执行能力。", ft.Icons.DESKTOP_WINDOWS_OUTLINED)
    else:
        groups.append(section("运行环境",
            detail_row("执行器版本", settings.SETTINGS.get("version", "-")),
            detail_row("Python 版本", sys.version.split()[0]),
            detail_row("操作系统", platform.system()),
            detail_row("配置数据库", project_dir.cache_file()),
            ft.Row([action_button("打开运行目录", lambda _: app.open_directory(project_dir.runtime_path()), ft.Icons.FOLDER_OPEN_OUTLINED)]),
            icon=ft.Icons.DESKTOP_WINDOWS_OUTLINED))
        groups.append(section("本机运行说明",
            ft.Text("配置修改后自动保存到本机；关闭窗口后，执行服务继续在托盘运行。", size=13),
            ft.Text("调试日志可在“实时日志”页面开启，运行目录可在“运行概览”中打开。", size=12, color=MUTED),
            icon=ft.Icons.SETTINGS_OUTLINED))
    if name == "web":
        for item in groups[:2]:
            item.col = {"xs": 12, "md": 6}
        groups = [ft.ResponsiveRow(groups[:2], spacing=PAGE_GAP, run_spacing=PAGE_GAP), *groups[2:]]
    return ft.Column(groups, spacing=PAGE_GAP, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

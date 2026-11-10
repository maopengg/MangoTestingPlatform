import flet as ft
import base64
from functools import lru_cache
from pathlib import Path

from src.tools import project_dir

BACKGROUND = "#F8FAFC"
SURFACE = "#FFFFFF"
TEXT = "#0F172A"
MUTED = "#64748B"
PRIMARY = "#1E40AF"
LINE = "#DBE3EF"
NAV_TEXT = "#334155"
NAV_MUTED = MUTED
NAV_ACTIVE = "#DBEAFE"
TINT = "#EFF6FF"
SUCCESS = "#047857"
WARNING = "#92400E"
DANGER = "#DC2626"
SOFT = "#F1F5F9"
CODE_BG = "#172033"
CODE_TEXT = "#E2E8F0"
CODE_MUTED = "#A5B4C8"
LOG_COLORS = {"info": CODE_TEXT, "debug": CODE_MUTED, "success": "#6EE7B7",
              "warning": "#FDE68A", "error": "#FCA5A5"}

# 对齐控制台的紧凑间距、卡片和表单尺寸，使用 Flet 逻辑像素。
PAGE_GAP = 8
CARD_PADDING = 12
CONTROL_HEIGHT = 36
BODY_SIZE = 13
LABEL_WIDTH = 128
SELECT_WIDTH_SHORT = 120
SELECT_WIDTH_MEDIUM = 180
SELECT_WIDTH_LONG = 280


@lru_cache(maxsize=1)
def _platform_logo_data():
    return base64.b64encode(Path(project_dir.resource_path("assets/platform_logo.png")).read_bytes()).decode("ascii")


def platform_logo(size):
    return ft.Image(src_base64=_platform_logo_data(), width=size, height=size,
                    fit=ft.ImageFit.CONTAIN, semantics_label="芒果测试平台 Logo")


def compact_input(control):
    control.dense = True
    control.height = CONTROL_HEIGHT
    control.text_size = BODY_SIZE
    control.label_style = ft.TextStyle(size=12, color=MUTED)
    control.hint_style = ft.TextStyle(size=BODY_SIZE, color=MUTED)
    control.content_padding = ft.padding.symmetric(horizontal=10, vertical=6)
    control.border_radius = 5
    control.color = TEXT
    control.border_color = LINE
    control.focused_border_color = PRIMARY
    control.focused_border_width = 1.5
    control.filled = True
    control.fill_color = SURFACE
    if isinstance(control, ft.TextField):
        control.cursor_color = PRIMARY
        control.selection_color = NAV_ACTIVE
        control.text_vertical_align = ft.VerticalAlignment.CENTER
    return control


def button_style(*, primary=False):
    return ft.ButtonStyle(
        color={ft.ControlState.DISABLED: MUTED, ft.ControlState.DEFAULT: SURFACE if primary else PRIMARY},
        bgcolor={ft.ControlState.DISABLED: SOFT, ft.ControlState.DEFAULT: PRIMARY if primary else ft.Colors.TRANSPARENT},
        overlay_color={ft.ControlState.HOVERED: ft.Colors.with_opacity(0.08, SURFACE if primary else PRIMARY),
                       ft.ControlState.FOCUSED: ft.Colors.with_opacity(0.16, SURFACE if primary else PRIMARY)},
        padding=ft.padding.symmetric(horizontal=12 if primary else 8),
        text_style=ft.TextStyle(size=BODY_SIZE if primary else 12), icon_size=16,
        shape=ft.RoundedRectangleBorder(radius=5), elevation=0,
        animation_duration=150,
    )


def action_button(label, on_click, icon=None, *, primary=False):
    button = ft.FilledButton if primary else ft.TextButton
    return button(label, icon=icon, on_click=on_click, height=CONTROL_HEIGHT if primary else 30,
                  style=button_style(primary=primary))


def toggle_control(control):
    label = control.label
    control.label = None
    control.adaptive = True
    control.active_color = PRIMARY
    control.focus_color = NAV_ACTIVE
    control.hover_color = TINT
    control.scale = ft.Scale(scale=0.78, alignment=ft.alignment.center_left)
    control.height = CONTROL_HEIGHT
    control.width = 52
    if label:
        control.tooltip = label
    return ft.Row([
        ft.Container(control, width=44, height=CONTROL_HEIGHT, alignment=ft.alignment.center_left),
        *([ft.Text(label, size=BODY_SIZE, color=TEXT)] if label else []),
    ], spacing=6, tight=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def checkbox_control(control):
    control.label_style = ft.TextStyle(size=BODY_SIZE, color=TEXT)
    control.active_color = PRIMARY
    control.check_color = SURFACE
    control.focus_color = NAV_ACTIVE
    control.hover_color = TINT
    control.visual_density = ft.VisualDensity.COMPACT
    control.shape = ft.RoundedRectangleBorder(radius=3)
    return control


def detail_row(label, value):
    return ft.Row([
        ft.Text(label, size=12, color=MUTED, width=76),
        ft.Text(str(value), size=BODY_SIZE, color=TEXT, expand=True, selectable=True,
                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, tooltip=str(value)),
    ], spacing=8, height=26, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def section(title, *controls, description=None, icon=None):
    heading = ft.Row([
        *([ft.Icon(icon, size=16, color=PRIMARY)] if icon else []),
        ft.Text(title, size=14, color=TEXT, weight=ft.FontWeight.W_600),
    ], spacing=8)
    header = [heading]
    if description:
        header.append(ft.Text(description, size=12, color=MUTED))
    return ft.Container(
        content=ft.Column([
            ft.Column(header, spacing=4),
            ft.Divider(height=1, thickness=1, color=LINE),
            *controls,
        ], spacing=PAGE_GAP, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
        bgcolor=SURFACE, padding=CARD_PADDING, border_radius=7, border=ft.border.all(1, LINE),
    )


def status_badge(text, color=PRIMARY):
    return ft.Container(ft.Row([
        ft.Icon(ft.Icons.CIRCLE, size=6, color=color),
        ft.Text(text, size=11, color=color),
    ], spacing=5, tight=True), bgcolor=BACKGROUND, border_radius=4,
        padding=ft.padding.symmetric(horizontal=8, vertical=5), border=ft.border.all(1, LINE))


def empty_panel(title, description, icon=ft.Icons.INFO_OUTLINE):
    return ft.Container(ft.Column([
        ft.Icon(icon, size=28, color=MUTED),
        ft.Text(title, size=14, color=TEXT, weight=ft.FontWeight.W_600),
        ft.Text(description, size=12, color=MUTED, text_align=ft.TextAlign.CENTER),
    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=32, bgcolor=SURFACE, border=ft.border.all(1, LINE), border_radius=7)


def field_row(label, control):
    if isinstance(control, ft.TextField):
        compact_input(control)
    if isinstance(control, ft.Switch):
        control.tooltip = label
        value = toggle_control(control)
    elif isinstance(control, ft.Text):
        control.size = BODY_SIZE
        value = control
    else:
        value = control
    return ft.Row([
        ft.Text(label, color=MUTED, size=BODY_SIZE, width=LABEL_WIDTH),
        ft.Container(value, expand=True, alignment=ft.alignment.center_left),
    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)

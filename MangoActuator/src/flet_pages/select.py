"""桌面紧凑选择框，复用原生菜单的焦点、键盘和滚动行为。"""

import flet as ft

from .theme import BODY_SIZE, CONTROL_HEIGHT, LINE, MUTED, PRIMARY, SURFACE, TINT, TEXT


class CompactSelect(ft.Container):
    ITEM_HEIGHT = 32

    def __init__(self, *, options, value=None, on_change=None, width=180, label=None, visible=True):
        super().__init__(width=width, height=CONTROL_HEIGHT, visible=visible,
                         bgcolor=SURFACE, border=ft.border.all(1, LINE), border_radius=5)
        self.options = list(options)
        self.on_change = on_change
        self.label = label
        self.selected_text = ft.Text(size=BODY_SIZE, color=TEXT, max_lines=1,
                                     overflow=ft.TextOverflow.ELLIPSIS, expand=True)
        self.menu = ft.PopupMenuButton(
            content=ft.Container(ft.Row([
                self.selected_text,
                ft.Icon(ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED, size=18, color=MUTED),
            ], spacing=6), padding=ft.padding.symmetric(horizontal=10),
                height=CONTROL_HEIGHT - 2, alignment=ft.alignment.center_left),
            padding=0, menu_padding=ft.padding.symmetric(vertical=4),
            menu_position=ft.PopupMenuPosition.UNDER, bgcolor=SURFACE,
            surface_tint_color=SURFACE, elevation=2,
            shape=ft.RoundedRectangleBorder(radius=5),
            style=ft.ButtonStyle(overlay_color=TINT, shape=ft.RoundedRectangleBorder(radius=5)),
            size_constraints=ft.BoxConstraints(min_width=width, max_width=max(width, 180), max_height=264),
        )
        self.content = self.menu
        self.value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value
        text = next((text for key, text in self.options if key == value), "请选择")
        self.selected_text.value = f"{self.label}：{text}" if self.label else text
        self.tooltip = self.selected_text.value
        self.menu.items = [ft.PopupMenuItem(
            height=self.ITEM_HEIGHT, padding=0,
            content=ft.Container(ft.Row([
                ft.Text(text, size=BODY_SIZE, color=PRIMARY if key == value else TEXT,
                        max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                ft.Icon(ft.Icons.CHECK_ROUNDED, size=14, color=PRIMARY, opacity=1 if key == value else 0),
            ], spacing=8), height=self.ITEM_HEIGHT, padding=ft.padding.symmetric(horizontal=10),
                bgcolor=TINT if key == value else None, alignment=ft.alignment.center_left),
            tooltip=text, on_click=lambda event, key=key: self._select(event, key),
        ) for key, text in self.options]

    def _select(self, event, value):
        if self.value == value:
            return
        self.value = value
        self.update()
        if self.on_change:
            self.on_change(ft.ControlEvent(event.target, "change", str(value), self, event.page))

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from ..theme import COLORS


FRAME_STYLES = {
    "page": "TFrame",
    "surface": "Surface.TFrame",
    "card": "Card.TFrame",
    "navigation": "Navigation.TFrame",
    "topbar": "Topbar.TFrame",
    "statusbar": "Statusbar.TFrame",
    "directory": "Directory.TFrame",
    "log_toolbar": "LogToolbar.TFrame",
}
LABEL_STYLES = {
    "default": "TLabel",
    "surface": "Surface.TLabel",
    "muted": "Muted.TLabel",
    "surface_muted": "SurfaceMuted.TLabel",
    "form": "FormLabel.TLabel",
    "directory": "Directory.TLabel",
    "title": "Title.TLabel",
    "subtitle": "Subtitle.TLabel",
    "section": "Section.TLabel",
    "card_title": "CardTitle.TLabel",
    "card_meta": "CardMeta.TLabel",
    "login_title": "LoginTitle.TLabel",
    "brand": "Brand.TLabel",
    "nav_meta": "NavMeta.TLabel",
    "topbar_title": "TopbarTitle.TLabel",
    "statusbar": "Statusbar.TLabel",
    "log_meta": "LogMeta.TLabel",
    "log_toolbar_muted": "LogToolbarMuted.TLabel",
}
BUTTON_STYLES = {
    "default": "TButton",
    "primary": "Primary.TButton",
    "link": "Link.TButton",
    "directory_link": "DirectoryLink.TButton",
    "navigation": "Nav.TButton",
    "navigation_selected": "Selected.Nav.TButton",
}

BUTTON_VARIANTS = {
    "default": {
        "background": "surface", "hover": "interactive_hover", "pressed": "border",
        "foreground": "text", "border": "border_strong", "height": 36,
        "padding": 14, "radius": 9, "weight": "normal", "anchor": "center",
    },
    "primary": {
        "background": "primary", "hover": "primary_hover", "pressed": "primary_pressed",
        "foreground": "white", "border": "primary", "height": 38,
        "padding": 17, "radius": 10, "weight": "bold", "anchor": "center",
    },
    "link": {
        "background": None, "hover": "primary_subtle", "pressed": "primary_subtle",
        "foreground": "primary", "border": None, "height": 30,
        "padding": 9, "radius": 8, "weight": "normal", "anchor": "center",
    },
    "directory_link": {
        "background": None, "hover": "primary_subtle", "pressed": "primary_subtle",
        "foreground": "primary", "border": None, "height": 30,
        "padding": 8, "radius": 8, "weight": "normal", "anchor": "center",
    },
    "navigation": {
        "background": "nav", "hover": "nav_hover", "pressed": "nav_active",
        "foreground": "nav_text", "border": None, "height": 42,
        "padding": 14, "radius": 9, "weight": "normal", "anchor": "w",
    },
    "navigation_selected": {
        "background": "nav_active", "hover": "nav_active", "pressed": "nav_active",
        "foreground": "white", "border": None, "height": 42,
        "padding": 14, "radius": 9, "weight": "bold", "anchor": "w",
    },
    "account": {
        "background": "nav", "hover": "nav_hover", "pressed": "nav_active",
        "foreground": "white", "border": None, "height": 34,
        "padding": 8, "radius": 8, "weight": "bold", "anchor": "w",
    },
    "account_selected": {
        "background": "nav_active", "hover": "nav_active", "pressed": "nav_active",
        "foreground": "white", "border": None, "height": 34,
        "padding": 8, "radius": 8, "weight": "bold", "anchor": "w",
    },
}


def _color(name: str | None, fallback: str) -> str:
    if name is None:
        return fallback
    if name == "white":
        return "#FFFFFF"
    return COLORS.get(name, name)


def _parent_background(parent: tk.Misc) -> str:
    try:
        return str(parent.cget("background"))
    except tk.TclError:
        pass
    try:
        style_name = str(parent.cget("style")) or parent.winfo_class()
        background = ttk.Style(parent).lookup(style_name, "background")
        if background:
            return str(background)
    except tk.TclError:
        pass
    return COLORS["surface"]


def _rounded_rectangle(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs) -> int:
    radius = max(0, min(radius, (x2 - x1) // 2, (y2 - y1) // 2))
    points = (
        x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
        x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
        x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
    )
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


class Frame(ttk.Frame):
    def __init__(self, parent, variant: str = "page", **kwargs):
        kwargs.setdefault("style", FRAME_STYLES[variant])
        super().__init__(parent, **kwargs)


class Label(ttk.Label):
    def __init__(self, parent, variant: str = "default", **kwargs):
        kwargs.setdefault("style", LABEL_STYLES[variant])
        super().__init__(parent, **kwargs)


class Button(tk.Canvas):
    """Cross-platform rounded button with native Tk focus and keyboard behavior."""

    def __init__(self, parent, variant: str = "default", **kwargs):
        self._text = str(kwargs.pop("text", ""))
        self._command = kwargs.pop("command", None)
        self._state = str(kwargs.pop("state", "normal"))
        self._width_chars = int(kwargs.pop("width", 0) or 0)
        kwargs.pop("style", None)
        self._variant = variant
        self._hovered = False
        self._pressed = False
        self._focused = False
        self._corner_background = _parent_background(parent)
        self._font = tkfont.nametofont("TkDefaultFont").copy()
        super().__init__(
            parent,
            height=BUTTON_VARIANTS[variant]["height"],
            background=self._corner_background,
            borderwidth=0,
            highlightthickness=0,
            takefocus=True,
            cursor="arrow",
            **kwargs,
        )
        self.bind("<Configure>", self._redraw, add="+")
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.bind("<FocusIn>", self._on_focus_in, add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")
        self.bind("<space>", self._on_key, add="+")
        self.bind("<Return>", self._on_key, add="+")
        self._sync_metrics()
        self.after_idle(self._redraw)

    def _spec(self) -> dict:
        return BUTTON_VARIANTS[self._variant]

    def _sync_metrics(self) -> None:
        spec = self._spec()
        self._font.configure(weight=spec["weight"])
        measured = self._font.measure(self._text)
        if self._width_chars:
            measured = max(measured, self._font.measure("0" * self._width_chars))
        width = max(34, measured + spec["padding"] * 2)
        super().configure(width=width, height=spec["height"])

    def _redraw(self, _event=None) -> None:
        if not self.winfo_exists():
            return
        self.delete("all")
        spec = self._spec()
        width = max(2, self.winfo_width())
        height = max(2, self.winfo_height())
        disabled = self._state == "disabled"
        base = _color(spec["background"], self._corner_background)
        if disabled:
            fill = COLORS["subtle"] if self._variant != "navigation" else COLORS["nav"]
        elif self._pressed:
            fill = _color(spec["pressed"], base)
        elif self._hovered:
            fill = _color(spec["hover"], base)
        else:
            fill = base
        border = _color(spec["border"], fill)
        if self._focused and not disabled:
            border = COLORS["primary"] if not self._variant.startswith("navigation") else "#8FB0F2"
        inset = 2 if self._focused else 1
        _rounded_rectangle(
            self, inset, inset, width - inset, height - inset, spec["radius"],
            fill=fill, outline=border, width=2 if self._focused else 1,
        )
        foreground = "#94A3B8" if disabled else _color(spec["foreground"], COLORS["text"])
        if spec["anchor"] == "w":
            self.create_text(spec["padding"], height // 2, text=self._text, anchor="w", fill=foreground, font=self._font)
        else:
            self.create_text(width // 2, height // 2, text=self._text, anchor="center", fill=foreground, font=self._font)

    def _on_enter(self, _event=None) -> None:
        if self._state != "disabled":
            self._hovered = True
            self._redraw()

    def _on_leave(self, _event=None) -> None:
        self._hovered = False
        self._pressed = False
        self._redraw()

    def _on_press(self, _event=None) -> None:
        if self._state != "disabled":
            self.focus_set()
            self._pressed = True
            self._redraw()

    def _on_release(self, event=None) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self._redraw()
        if was_pressed and event is not None and 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height():
            self.invoke()

    def _on_focus_in(self, _event=None) -> None:
        self._focused = True
        self._redraw()

    def _on_focus_out(self, _event=None) -> None:
        self._focused = False
        self._pressed = False
        self._redraw()

    def _on_key(self, _event=None) -> str:
        self.invoke()
        return "break"

    def invoke(self):
        if self._state != "disabled" and callable(self._command):
            return self._command()
        return None

    def configure(self, cnf=None, **kwargs):
        options = dict(cnf or {})
        options.update(kwargs)
        changed = False
        if "text" in options:
            self._text = str(options.pop("text"))
            changed = True
        if "command" in options:
            self._command = options.pop("command")
        if "state" in options:
            self._state = str(options.pop("state"))
            super().configure(cursor="arrow")
            changed = True
        options.pop("style", None)
        result = super().configure(**options) if options else None
        if changed:
            self._sync_metrics()
        self._redraw()
        return result

    config = configure

    def cget(self, key):
        if key == "text":
            return self._text
        if key == "state":
            return self._state
        return super().cget(key)

    def set_variant(self, variant: str) -> None:
        if variant not in BUTTON_VARIANTS:
            raise ValueError(f"未知按钮样式：{variant}")
        self._variant = variant
        self._sync_metrics()
        self._redraw()


class _RoundedField(tk.Frame):
    """Rounded shell that preserves a native ttk input as the actual editor."""

    input_class = ttk.Entry
    default_width = 28

    def __init__(self, parent, variant: str = "default", **kwargs):
        self._variant = variant
        self._focused = False
        self._hovered = False
        self._width_chars = int(kwargs.pop("width", self.default_width) or self.default_width)
        self._height = 34 if variant == "log_toolbar" else 38
        self._corner_background = _parent_background(parent)
        input_style = self._input_style(variant)
        kwargs.pop("style", None)
        super().__init__(
            parent, background=self._corner_background, borderwidth=0,
            highlightthickness=0, takefocus=False,
        )
        self._canvas = tk.Canvas(
            self, background=self._corner_background, borderwidth=0,
            highlightthickness=0, takefocus=False,
        )
        self._canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._input = self.input_class(self, style=input_style, **kwargs)
        self._is_combobox = isinstance(self._input, ttk.Combobox)
        right_inset = 36 if self._is_combobox else 4
        self._input.place(
            x=4, y=3, relwidth=1, relheight=1,
            width=-(4 + right_inset), height=-6,
        )
        super().bind("<Configure>", self._draw, add="+")
        self._input.bind("<FocusIn>", self._on_focus_in, add="+")
        self._input.bind("<FocusOut>", self._on_focus_out, add="+")
        for widget in (self, self._canvas, self._input):
            widget.bind("<Enter>", self._on_enter, add="+")
            widget.bind("<Leave>", self._on_leave, add="+")
        self._canvas.bind("<Button-1>", self._on_canvas_click, add="+")
        if self._is_combobox:
            self._canvas.configure(cursor="arrow")
        self._sync_size()
        self.after_idle(self._draw)

    def _input_style(self, variant: str) -> str:
        raise NotImplementedError

    def _sync_size(self) -> None:
        font = tkfont.nametofont("TkDefaultFont")
        extra = 34 if self.input_class is ttk.Combobox else 24
        pixel_width = max(100, font.measure("0" * self._width_chars) + extra)
        super().configure(width=pixel_width, height=self._height)
        self.pack_propagate(False)
        self.grid_propagate(False)

    def _draw(self, _event=None) -> None:
        if not self.winfo_exists():
            return
        self._canvas.delete("all")
        width, height = max(2, self.winfo_width()), max(2, self.winfo_height())
        state = str(self._input.cget("state"))
        fill = COLORS["surface_alt"] if state == "disabled" else COLORS["surface"]
        border = COLORS["primary"] if self._focused else (
            COLORS["hover_border"] if self._hovered else COLORS["border"]
        )
        _rounded_rectangle(
            self._canvas, 1, 1, width - 1, height - 1, 10,
            fill=fill, outline=border, width=2 if self._focused else 1,
        )
        if self._is_combobox:
            arrow_color = COLORS["primary"] if self._focused or self._hovered else COLORS["muted"]
            center_x, center_y = width - 18, height // 2
            self._canvas.create_line(
                center_x - 5, center_y - 2,
                center_x, center_y + 3,
                center_x + 5, center_y - 2,
                fill=arrow_color, width=2, capstyle="round", joinstyle="round",
            )

    def _on_canvas_click(self, event=None):
        self._input.focus_set()
        if self._is_combobox and event is not None and event.x >= self.winfo_width() - 36:
            return self._post_dropdown()
        return None

    def _post_dropdown(self):
        if not self._is_combobox or str(self._input.cget("state")) == "disabled":
            return "break"
        try:
            self._input.tk.call("ttk::combobox::Post", self._input._w)
        except tk.TclError:
            self._input.event_generate(
                "<Alt-Down>",
                when="tail",
            )
        return "break"

    def _on_focus_in(self, _event=None) -> None:
        self._focused = True
        self._draw()

    def _on_focus_out(self, _event=None) -> None:
        self._focused = False
        self._draw()

    def _on_enter(self, _event=None) -> None:
        self._hovered = True
        self._draw()

    def _on_leave(self, event=None) -> None:
        if event is not None:
            target = self.winfo_containing(event.x_root, event.y_root)
            if target in (self, self._canvas, self._input):
                return
        self._hovered = False
        self._draw()

    def configure(self, cnf=None, **kwargs):
        options = dict(cnf or {})
        options.update(kwargs)
        if not hasattr(self, "_input"):
            return super().configure(**options)
        if "width" in options:
            self._width_chars = int(options.pop("width") or self.default_width)
            self._sync_size()
        options.pop("style", None)
        result = self._input.configure(**options) if options else None
        self._draw()
        return result

    config = configure

    def cget(self, key):
        if key == "width":
            return self._width_chars
        if hasattr(self, "_input"):
            try:
                return self._input.cget(key)
            except tk.TclError:
                pass
        return super().cget(key)

    def bind(self, sequence=None, func=None, add=None):
        if hasattr(self, "_input") and sequence != "<Configure>":
            return self._input.bind(sequence, func, add)
        return super().bind(sequence, func, add)

    def event_generate(self, sequence, **kwargs):
        if hasattr(self, "_input"):
            return self._input.event_generate(sequence, **kwargs)
        return super().event_generate(sequence, **kwargs)

    def focus_set(self) -> None:
        self._input.focus_set()

    focus = focus_set

    def get(self):
        return self._input.get()

    def delete(self, first, last=None):
        return self._input.delete(first, last)

    def insert(self, index, string):
        return self._input.insert(index, string)

    def xview(self, *args):
        return self._input.xview(*args)

    def icursor(self, index):
        return self._input.icursor(index)

    def selection_range(self, start, end):
        return self._input.selection_range(start, end)


class Entry(_RoundedField):
    input_class = ttk.Entry

    def _input_style(self, variant: str) -> str:
        return "RoundedLogToolbar.TEntry" if variant == "log_toolbar" else "Rounded.TEntry"


class Combobox(_RoundedField):
    input_class = ttk.Combobox

    def __init__(self, parent, variant: str = "default", **kwargs):
        super().__init__(parent, variant=variant, **kwargs)
        self._input.configure(cursor="arrow")
        self._input.bind("<Button-1>", self._on_input_click, add="+")

    def _on_input_click(self, _event=None):
        if str(self._input.cget("state")) == "readonly":
            self._input.focus_set()
            return self._post_dropdown()
        return None

    def _input_style(self, variant: str) -> str:
        return "RoundedLogToolbar.TCombobox" if variant == "log_toolbar" else "Rounded.TCombobox"

    def current(self, newindex=None):
        if newindex is None:
            return self._input.current()
        return self._input.current(newindex)

    def set(self, value):
        return self._input.set(value)


class Checkbutton(ttk.Checkbutton):
    pass


class Separator(ttk.Separator):
    pass


class Progressbar(ttk.Progressbar):
    pass


class LabelFrame(ttk.LabelFrame):
    pass


class ColorFrame(tk.Frame):
    """Native frame for solid-color branded surfaces unsupported by ttk."""

    def __init__(self, parent, tone: str = "surface", **kwargs):
        kwargs.setdefault("background", COLORS[tone])
        super().__init__(parent, **kwargs)


class ColorLabel(tk.Label):
    """Native label for badges and branded areas that need explicit colors."""

    def __init__(
        self,
        parent,
        background_tone: str = "surface",
        foreground_tone: str = "text",
        **kwargs,
    ):
        kwargs.setdefault("background", COLORS.get(background_tone, background_tone))
        kwargs.setdefault("foreground", COLORS.get(foreground_tone, foreground_tone))
        super().__init__(parent, **kwargs)


class StatusBadge(tk.Canvas):
    TONES = {
        "success": ("success_bg", "success"),
        "warning": ("warning_bg", "warning"),
        "danger": ("danger_bg", "danger"),
        "info": ("info_bg", "primary"),
    }

    def __init__(self, parent, tone: str = "info", **kwargs):
        self._tone = tone
        self._text = str(kwargs.pop("text", ""))
        self._textvariable = kwargs.pop("textvariable", None)
        self._font = tkfont.nametofont("TkDefaultFont").copy()
        self._font.configure(weight="bold")
        super().__init__(
            parent, height=28, background=_parent_background(parent), borderwidth=0,
            highlightthickness=0, takefocus=False, **kwargs,
        )
        if self._textvariable is not None:
            self._textvariable.trace_add("write", self._on_text_change)
        self.bind("<Configure>", self._draw, add="+")
        self._sync_size()
        self.after_idle(self._draw)

    def _value(self) -> str:
        return str(self._textvariable.get()) if self._textvariable is not None else self._text

    def _sync_size(self) -> None:
        super().configure(width=max(48, self._font.measure(self._value()) + 22), height=28)

    def _draw(self, _event=None) -> None:
        self.delete("all")
        background, foreground = self.TONES[self._tone]
        width, height = max(2, self.winfo_width()), max(2, self.winfo_height())
        _rounded_rectangle(self, 1, 1, width - 1, height - 1, 13, fill=COLORS[background], outline=COLORS[background])
        self.create_text(width // 2, height // 2, text=self._value(), fill=COLORS[foreground], font=self._font)

    def _on_text_change(self, *_args) -> None:
        self._sync_size()
        self._draw()

    def set_tone(self, tone: str) -> None:
        if tone not in self.TONES:
            raise ValueError(f"未知状态标签样式：{tone}")
        self._tone = tone
        self._draw()


class Text(tk.Text):
    def __init__(self, parent, variant: str = "editor", **kwargs):
        defaults = {
            "background": COLORS["log"] if variant == "log" else COLORS["surface_alt"],
            "foreground": COLORS["log_text"] if variant == "log" else COLORS["text"],
            "selectbackground": COLORS["primary"],
            "relief": "flat",
            "highlightthickness": 1,
            "highlightbackground": "#263249" if variant == "log" else COLORS["border"],
            "highlightcolor": COLORS["primary"],
        }
        for key, value in defaults.items():
            kwargs.setdefault(key, value)
        super().__init__(parent, **kwargs)


def readonly_combo(parent, values: list[str], width: int = 28, **kwargs) -> Combobox:
    return Combobox(parent, values=values, state="readonly", width=width, **kwargs)

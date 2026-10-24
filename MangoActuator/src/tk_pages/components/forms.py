from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..theme import COLORS
from .widgets import Combobox, Entry, Frame, Label


class Switch(Frame):
    """Frontend-style animated toggle backed by a Tk BooleanVar."""

    CANVAS_WIDTH = 48
    CANVAS_HEIGHT = 28
    TRACK = (3, 3, 45, 25)
    KNOB_SIZE = 18
    KNOB_OFF_X = 5
    KNOB_ON_X = 25

    def __init__(self, parent, variable: tk.BooleanVar, text: str, command=None):
        super().__init__(parent, variant="surface")
        self.variable = variable
        self.command = command
        self._hovered = False
        self._focused = False
        self._position = 1.0 if variable.get() else 0.0
        self._animation_id = None
        self.canvas = tk.Canvas(
            self, width=self.CANVAS_WIDTH, height=self.CANVAS_HEIGHT,
            background=COLORS["surface"], highlightthickness=0,
            bd=0, cursor="arrow", takefocus=True,
        )
        self.canvas.pack(side="left")
        self.label = Label(self, text=text, variant="surface", cursor="arrow")
        self.label.pack(side="left", padx=(7, 0))
        for widget in (self.canvas, self.label):
            widget.bind("<Button-1>", self._toggle)
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)
        self.canvas.bind("<space>", self._toggle)
        self.canvas.bind("<Return>", self._toggle)
        self.canvas.bind("<FocusIn>", self._focus_in)
        self.canvas.bind("<FocusOut>", self._focus_out)
        self.variable.trace_add("write", self._value_changed)
        self._draw()

    def _toggle(self, _event=None):
        self.variable.set(not self.variable.get())
        if self.command:
            self.command()
        return "break"

    def _enter(self, _event=None):
        self._hovered = True
        self._draw()

    def _leave(self, event=None):
        if event is not None:
            target = self.winfo_containing(event.x_root, event.y_root)
            if target in (self, self.canvas, self.label):
                return
        self._hovered = False
        self._draw()

    def _focus_in(self, _event=None):
        self._focused = True
        self._draw()

    def _focus_out(self, _event=None):
        self._focused = False
        self._draw()

    def _value_changed(self, *_args):
        target = 1.0 if self.variable.get() else 0.0
        if self._animation_id is not None:
            self.after_cancel(self._animation_id)
            self._animation_id = None
        if not self.winfo_ismapped():
            self._position = target
            self._draw()
            return
        start = self._position
        steps = 7

        def animate(step: int = 1):
            if not self.winfo_exists():
                return
            progress = min(1.0, step / steps)
            eased = 1.0 - ((1.0 - progress) ** 3)
            self._position = start + ((target - start) * eased)
            self._draw()
            if step < steps:
                self._animation_id = self.after(15, animate, step + 1)
            else:
                self._animation_id = None

        animate()

    @staticmethod
    def _pill(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, color: str):
        diameter = y2 - y1
        radius = diameter // 2
        canvas.create_oval(x1, y1, x1 + diameter, y2, fill=color, outline=color)
        canvas.create_rectangle(x1 + radius, y1, x2 - radius, y2, fill=color, outline=color)
        canvas.create_oval(x2 - diameter, y1, x2, y2, fill=color, outline=color)

    def _draw(self):
        self.canvas.delete("all")
        enabled = bool(self.variable.get())
        track = (
            COLORS["primary_hover"] if self._hovered else COLORS["primary"]
        ) if enabled else (
            COLORS["hover_border"] if self._hovered else COLORS["border_strong"]
        )
        if self._focused:
            self._pill(
                self.canvas, 0, 0, self.CANVAS_WIDTH, self.CANVAS_HEIGHT,
                COLORS["primary_subtle"],
            )
        self._pill(self.canvas, *self.TRACK, track)
        knob_left = self.KNOB_OFF_X + ((self.KNOB_ON_X - self.KNOB_OFF_X) * self._position)
        self.canvas.create_oval(
            knob_left + 1, 6, knob_left + self.KNOB_SIZE + 1, 24,
            fill="#AAB6C5", outline="#AAB6C5",
        )
        self.canvas.create_oval(
            knob_left, 5, knob_left + self.KNOB_SIZE, 23,
            fill="#FFFFFF", outline="#FFFFFF",
        )


class FormGrid(Frame):
    """Compact label/control/help grid used by configuration pages."""

    def __init__(self, parent, bordered: bool = True):
        super().__init__(
            parent,
            variant="card" if bordered else "surface",
            padding=(18, 12) if bordered else 0,
        )
        self._items: list[tuple[Label, tk.Widget, Label | None]] = []
        self._wide_layout: bool | None = None
        self.bind("<Configure>", self._on_resize)

    def add(self, label: str, control: tk.Widget, help_text: str = "") -> tk.Widget:
        label_widget = Label(self, text=label, variant="form")
        if isinstance(control, (Entry, Combobox, ttk.Entry, ttk.Combobox)):
            control.configure(width=40)
        help_widget = Label(self, text=help_text, variant="surface_muted", wraplength=320) if help_text else None
        self._items.append((label_widget, control, help_widget))
        self._apply_layout(self.winfo_width() >= 860)
        return control

    def _on_resize(self, event):
        self._apply_layout(event.width >= 860)

    def _apply_layout(self, wide: bool):
        if wide == self._wide_layout and all(widget.winfo_manager() for item in self._items for widget in item if widget):
            return
        self._wide_layout = wide
        for item in self._items:
            for widget in item:
                if widget:
                    widget.grid_forget()
        if wide:
            self.columnconfigure(0, minsize=155, weight=0)
            self.columnconfigure(1, minsize=380, weight=1)
            self.columnconfigure(2, minsize=300, weight=0)
            for row, (label, control, help_widget) in enumerate(self._items):
                label.grid(row=row, column=0, sticky="w", padx=(0, 18), pady=7)
                control.grid(row=row, column=1, sticky="ew", pady=7)
                if help_widget:
                    help_widget.grid(row=row, column=2, sticky="w", padx=(22, 0), pady=7)
        else:
            self.columnconfigure(0, minsize=130, weight=0)
            self.columnconfigure(1, minsize=0, weight=1)
            self.columnconfigure(2, minsize=0, weight=0)
            for index, (label, control, help_widget) in enumerate(self._items):
                row = index * 2
                label.grid(row=row, column=0, sticky="w", padx=(0, 14), pady=(6, 4))
                control.grid(row=row, column=1, sticky="ew", pady=(6, 4))
                if help_widget:
                    help_widget.grid(row=row + 1, column=1, sticky="w", pady=(0, 5))

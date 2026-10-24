from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..theme import COLORS
from .widgets import Frame


class ScrollableFrame(Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, background=COLORS["background"], bd=0)
        self.scrollbar = ttk.Scrollbar(
            self, orient="vertical", style="Modern.Vertical.TScrollbar", command=self.canvas.yview,
        )
        self.body = Frame(self.canvas)
        self._window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.body.bind("<Configure>", self._sync_region)
        self.canvas.bind("<Configure>", self._sync_width)
        self.canvas.bind_all("<MouseWheel>", self._mousewheel, add="+")
        self.canvas.bind_all("<Button-4>", self._mousewheel, add="+")
        self.canvas.bind_all("<Button-5>", self._mousewheel, add="+")

    def _sync_region(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _sync_width(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)

    def _mousewheel(self, event):
        widget = event.widget
        while widget is not None and widget is not self:
            widget = getattr(widget, "master", None)
        if widget is not self:
            return
        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        else:
            delta = int(getattr(event, "delta", 0))
            step = -1 if delta > 0 else 1
            if abs(delta) >= 120:
                step = int(-delta / 120)
        self.canvas.yview_scroll(step, "units")
        return "break"


class AutoHideScrollbar(ttk.Scrollbar):
    """Grid-managed scrollbar that disappears while the full content is visible."""

    def __init__(self, parent, **kwargs):
        orientation = str(kwargs.get("orient", "vertical"))
        kwargs.setdefault(
            "style",
            "Modern.Horizontal.TScrollbar" if orientation == "horizontal" else "Modern.Vertical.TScrollbar",
        )
        super().__init__(parent, **kwargs)
        self._visible = True

    def set(self, first, last):
        visible = float(first) > 0.0 or float(last) < 1.0
        if visible and not self._visible:
            self.grid()
            self._visible = True
        elif not visible and self._visible:
            self.grid_remove()
            self._visible = False
        super().set(first, last)

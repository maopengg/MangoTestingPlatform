from __future__ import annotations

import tkinter as tk

from ..theme import COLORS
from .widgets import Frame, Label, LabelFrame, _parent_background, _rounded_rectangle


class ConstrainedFrame(Frame):
    """Center page content and cap its width without breaking narrow-window resizing."""

    def __init__(self, parent, max_width: int = 1120, **kwargs):
        super().__init__(parent, **kwargs)
        self.max_width = max_width
        self.columnconfigure(0, weight=1)
        self.body = Frame(self)
        self.body.grid(row=0, column=0, sticky="ew")
        self.body.columnconfigure(0, weight=1)
        self.bind("<Configure>", self._constrain_width)

    def _constrain_width(self, event):
        inset = max(0, (event.width - self.max_width) // 2)
        self.body.grid_configure(padx=(inset, inset))


class Card(tk.Canvas):
    """Rounded elevated surface with a consistent header and padded content area."""

    def __init__(self, parent, title: str, description: str = "", **kwargs):
        width = kwargs.pop("width", 320)
        height = kwargs.pop("height", 160)
        corner_background = _parent_background(parent)
        super().__init__(
            parent, width=width, height=height, background=corner_background,
            borderwidth=0, highlightthickness=0, takefocus=False, **kwargs,
        )
        self._surface = Frame(self, variant="surface")
        self._surface.columnconfigure(0, weight=1)
        self._surface.rowconfigure(1, weight=1)
        self._surface_window = self.create_window(6, 5, anchor="nw", window=self._surface)
        header = Frame(self._surface, variant="surface", padding=(18, 15, 18, 11))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        Label(header, text=title, variant="card_title").grid(row=0, column=0, sticky="w")
        if description:
            Label(header, text=description, variant="card_meta").grid(row=1, column=0, sticky="w", pady=(3, 0))
        self.actions = Frame(header, variant="surface")
        self.actions.grid(row=0, column=1, rowspan=2, sticky="e")
        self.body = Frame(self._surface, variant="surface", padding=(18, 8, 18, 18))
        self.body.grid(row=1, column=0, sticky="nsew")
        self.bind("<Configure>", self._layout_surface, add="+")
        self._surface.bind("<Configure>", self._schedule_request_sync, add="+")
        self._request_sync_id = None
        self.after_idle(self._sync_requested_size)

    def _layout_surface(self, event=None) -> None:
        width = max(20, event.width if event is not None else self.winfo_width())
        height = max(20, event.height if event is not None else self.winfo_height())
        self.delete("card_background")
        _rounded_rectangle(
            self, 3, 5, width - 2, height - 1, 14,
            fill="#DFE6F0", outline="#DFE6F0", tags="card_background",
        )
        _rounded_rectangle(
            self, 1, 1, width - 4, height - 5, 14,
            fill=COLORS["surface"], outline=COLORS["border"], width=1,
            tags="card_background",
        )
        self.tag_lower("card_background")
        self.coords(self._surface_window, 6, 5)
        self.itemconfigure(
            self._surface_window,
            width=max(1, width - 13),
            height=max(1, height - 13),
        )

    def _schedule_request_sync(self, _event=None) -> None:
        if self._request_sync_id is not None:
            self.after_cancel(self._request_sync_id)
        self._request_sync_id = self.after_idle(self._sync_requested_size)

    def _sync_requested_size(self) -> None:
        self._request_sync_id = None
        requested_width = max(320, self._surface.winfo_reqwidth() + 13)
        requested_height = max(120, self._surface.winfo_reqheight() + 13)
        super().configure(width=requested_width, height=requested_height)
        self._layout_surface()


class Page(Frame):
    title = ""

    def __init__(self, parent, app):
        super().__init__(parent, padding=(22, 18))
        self.app = app
        self.columnconfigure(0, weight=1)

    def on_show(self) -> None:
        pass

    def header(self, title: str, description: str, row: int = 0) -> Frame:
        frame = Frame(self)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 16))
        Label(frame, text=title, variant="title").pack(anchor="w")
        Label(frame, text=description, variant="subtitle").pack(anchor="w", pady=(4, 0))
        return frame

    def section(self, title: str, row: int, **grid_options) -> LabelFrame:
        frame = LabelFrame(self, text=title)
        options = {"row": row, "column": 0, "sticky": "nsew", "pady": (0, 12)}
        options.update(grid_options)
        frame.grid(**options)
        return frame

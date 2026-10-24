from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk


COLORS = {
    "background": "#F3F6FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "subtle": "#EDF2F8",
    "interactive_hover": "#EEF3FA",
    "border": "#E2E8F1",
    "border_strong": "#C7D2E2",
    "hover_border": "#9FB1C9",
    "text": "#172033",
    "text_secondary": "#475569",
    "muted": "#64748B",
    "primary": "#3156A3",
    "primary_hover": "#27498E",
    "primary_pressed": "#203E7A",
    "primary_subtle": "#E9F0FC",
    "nav": "#17233A",
    "nav_hover": "#22324F",
    "nav_active": "#2B4778",
    "nav_text": "#DCE5F2",
    "nav_muted": "#94A3B8",
    "success": "#087F5B",
    "success_bg": "#E7F6EF",
    "warning": "#B8660B",
    "warning_bg": "#FFF4E5",
    "danger": "#C53030",
    "danger_bg": "#FDECEC",
    "info_bg": "#EAF0FA",
    "log": "#101827",
    "log_text": "#D5DEEA",
}


def _font_family(root: tk.Misc) -> str:
    available = set(tkfont.families(root))
    for candidate in (
        "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC",
        "Noto Sans CJK SC", "Source Han Sans SC", "Segoe UI", "Arial",
    ):
        if candidate in available:
            return candidate
    return "TkDefaultFont"


def setup_theme(root: tk.Misc) -> ttk.Style:
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    family = _font_family(root)
    root.option_add("*Font", (family, 10))
    root.option_add("*TButton.cursor", "arrow")
    root.option_add("*TCheckbutton.cursor", "arrow")
    root.option_add("*TCombobox.cursor", "arrow")
    root.option_add("*TCombobox*Listbox.background", COLORS["surface"])
    root.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", COLORS["primary_subtle"])
    root.option_add("*TCombobox*Listbox.selectForeground", COLORS["text"])
    root.option_add("*TCombobox*Listbox.relief", "flat")
    root.configure(background=COLORS["background"])
    style.configure("TFrame", background=COLORS["background"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure(
        "LogToolbar.TFrame", background=COLORS["surface"], borderwidth=1, relief="solid",
        bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"],
    )
    style.configure(
        "Directory.TFrame", background=COLORS["surface_alt"], borderwidth=1, relief="solid",
        bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"],
    )
    style.configure(
        "Card.TFrame", background=COLORS["surface"], borderwidth=1, relief="solid",
        bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"],
    )
    style.configure("Navigation.TFrame", background=COLORS["nav"])
    style.configure("Topbar.TFrame", background=COLORS["surface"])
    style.configure("Statusbar.TFrame", background=COLORS["surface"])
    style.configure("TLabel", background=COLORS["background"], foreground=COLORS["text"])
    style.configure("Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Muted.TLabel", background=COLORS["background"], foreground=COLORS["muted"])
    style.configure("SurfaceMuted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("FormLabel.TLabel", background=COLORS["surface"], foreground=COLORS["text_secondary"], font=(family, 10, "bold"))
    style.configure("Directory.TLabel", background=COLORS["surface_alt"], foreground=COLORS["text"], font=(family, 10, "bold"))
    style.configure("Title.TLabel", background=COLORS["background"], foreground=COLORS["text"], font=(family, 16, "bold"))
    style.configure("Subtitle.TLabel", background=COLORS["background"], foreground=COLORS["muted"], font=(family, 9))
    style.configure("Section.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=(family, 11, "bold"))
    style.configure("CardTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=(family, 12, "bold"))
    style.configure("CardMeta.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=(family, 9))
    style.configure("LoginTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=(family, 15, "bold"))
    style.configure("Brand.TLabel", background=COLORS["nav"], foreground="#FFFFFF", font=(family, 14, "bold"))
    style.configure("NavMeta.TLabel", background=COLORS["nav"], foreground=COLORS["nav_muted"], font=(family, 9))
    style.configure("TopbarTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=(family, 12, "bold"))
    style.configure("Statusbar.TLabel", background=COLORS["surface"], foreground=COLORS["text_secondary"], font=(family, 9))
    style.configure("LogMeta.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=(family, 9))
    style.configure("LogToolbarMuted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=(family, 9))

    style.configure("TButton", padding=(12, 7), background=COLORS["surface"], foreground=COLORS["text"], bordercolor=COLORS["border_strong"], focusthickness=2, focuscolor=COLORS["primary"])
    style.map("TButton", background=[("active", COLORS["interactive_hover"]), ("pressed", COLORS["border"])], foreground=[("disabled", "#94A3B8")], bordercolor=[("focus", COLORS["primary"])])
    style.configure("Primary.TButton", padding=(15, 8), background=COLORS["primary"], foreground="#FFFFFF", bordercolor=COLORS["primary"], font=(family, 10, "bold"))
    style.map("Primary.TButton", background=[("active", COLORS["primary_hover"]), ("pressed", COLORS["primary_pressed"]), ("disabled", "#9AAAC4")], foreground=[("disabled", "#EEF2F7")])
    style.configure("Link.TButton", padding=(7, 3), background=COLORS["surface"], foreground=COLORS["primary"], borderwidth=0)
    style.map("Link.TButton", background=[("active", COLORS["primary_subtle"])], foreground=[("active", COLORS["primary_hover"])])
    style.configure("DirectoryLink.TButton", padding=(6, 3), background=COLORS["surface_alt"], foreground=COLORS["primary"], borderwidth=0)
    style.map("DirectoryLink.TButton", background=[("active", COLORS["primary_subtle"])], foreground=[("active", COLORS["primary_hover"])])
    style.configure("Nav.TButton", anchor="w", padding=(13, 9), background=COLORS["nav"], foreground=COLORS["nav_text"], bordercolor=COLORS["nav"], borderwidth=0, relief="flat", focusthickness=0, font=(family, 10))
    style.map("Nav.TButton", background=[("active", COLORS["nav_hover"]), ("pressed", COLORS["nav_active"])], foreground=[("active", "#FFFFFF")])
    style.configure("Selected.Nav.TButton", anchor="w", padding=(13, 9), background=COLORS["nav_active"], foreground="#FFFFFF", bordercolor=COLORS["nav_active"], borderwidth=0, relief="flat", focusthickness=0, font=(family, 10, "bold"))
    style.map("Selected.Nav.TButton", background=[("active", COLORS["nav_active"]), ("pressed", COLORS["nav_active"])])

    style.configure(
        "TEntry", padding=(10, 7), fieldbackground=COLORS["surface"], foreground=COLORS["text"],
        bordercolor=COLORS["border_strong"], lightcolor=COLORS["border_strong"],
        darkcolor=COLORS["border_strong"], insertcolor=COLORS["text"], relief="flat", borderwidth=1,
    )
    style.map(
        "TEntry", bordercolor=[("focus", COLORS["primary"]), ("disabled", COLORS["border"])],
        lightcolor=[("focus", COLORS["primary"])], darkcolor=[("focus", COLORS["primary"])],
        fieldbackground=[("disabled", COLORS["surface_alt"])], foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "LogToolbar.TEntry", padding=(9, 5), fieldbackground=COLORS["surface"], foreground=COLORS["text"],
        bordercolor=COLORS["border_strong"], lightcolor=COLORS["border_strong"],
        darkcolor=COLORS["border_strong"], insertcolor=COLORS["text"], relief="flat", borderwidth=1,
    )
    style.map(
        "LogToolbar.TEntry", bordercolor=[("focus", COLORS["primary"])],
        lightcolor=[("focus", COLORS["primary"])], darkcolor=[("focus", COLORS["primary"])],
    )
    style.configure(
        "Rounded.TEntry", padding=(8, 6), background=COLORS["surface"], fieldbackground=COLORS["surface"],
        foreground=COLORS["text"], insertcolor=COLORS["text"], relief="flat", borderwidth=0,
    )
    style.map(
        "Rounded.TEntry",
        background=[("disabled", COLORS["surface_alt"])],
        fieldbackground=[("disabled", COLORS["surface_alt"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "RoundedLogToolbar.TEntry", padding=(7, 4), background=COLORS["surface"], fieldbackground=COLORS["surface"],
        foreground=COLORS["text"], insertcolor=COLORS["text"], relief="flat", borderwidth=0,
    )
    style.map(
        "RoundedLogToolbar.TEntry",
        background=[("disabled", COLORS["surface_alt"])],
        fieldbackground=[("disabled", COLORS["surface_alt"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    entry_layout = [
        ("Entry.padding", {
            "sticky": "nswe",
            "children": [("Entry.textarea", {"sticky": "nswe"})],
        }),
    ]
    style.layout("Rounded.TEntry", entry_layout)
    style.layout("RoundedLogToolbar.TEntry", entry_layout)
    style.configure(
        "TCombobox", padding=(10, 7), fieldbackground=COLORS["surface"], foreground=COLORS["text"],
        background=COLORS["surface"], bordercolor=COLORS["border_strong"],
        lightcolor=COLORS["border_strong"], darkcolor=COLORS["border_strong"],
        arrowcolor=COLORS["muted"], arrowsize=12, relief="flat", borderwidth=1,
    )
    style.map(
        "TCombobox", bordercolor=[("focus", COLORS["primary"])],
        lightcolor=[("focus", COLORS["primary"])], darkcolor=[("focus", COLORS["primary"])],
        fieldbackground=[("readonly", COLORS["surface"]), ("disabled", COLORS["surface_alt"])],
        background=[("readonly", COLORS["surface"]), ("active", COLORS["primary_subtle"])],
        arrowcolor=[("active", COLORS["primary"]), ("focus", COLORS["primary"])],
        selectbackground=[("readonly", COLORS["surface"])], selectforeground=[("readonly", COLORS["text"])],
        foreground=[("disabled", COLORS["muted"])],
    )
    style.configure(
        "LogToolbar.TCombobox", padding=(9, 5), fieldbackground=COLORS["surface"], foreground=COLORS["text"],
        background=COLORS["surface"], bordercolor=COLORS["border_strong"],
        lightcolor=COLORS["border_strong"], darkcolor=COLORS["border_strong"],
        arrowcolor=COLORS["muted"], arrowsize=11, relief="flat", borderwidth=1,
    )
    style.map(
        "LogToolbar.TCombobox", bordercolor=[("focus", COLORS["primary"])],
        lightcolor=[("focus", COLORS["primary"])], darkcolor=[("focus", COLORS["primary"])],
        fieldbackground=[("readonly", COLORS["surface"])], background=[("readonly", COLORS["surface"])],
        arrowcolor=[("active", COLORS["primary"]), ("focus", COLORS["primary"])],
        selectbackground=[("readonly", COLORS["surface"])], selectforeground=[("readonly", COLORS["text"])],
    )
    for combo_style, padding, arrow_size in (
        ("Rounded.TCombobox", (8, 6), 12),
        ("RoundedLogToolbar.TCombobox", (7, 4), 11),
    ):
        style.configure(
            combo_style, padding=padding, fieldbackground=COLORS["surface"],
            foreground=COLORS["text"], background=COLORS["surface"],
            borderwidth=0, relief="flat", arrowcolor=COLORS["muted"], arrowsize=arrow_size,
        )
        style.map(
            combo_style,
            fieldbackground=[("readonly", COLORS["surface"]), ("disabled", COLORS["surface_alt"])],
            background=[("readonly", COLORS["surface"]), ("active", COLORS["primary_subtle"])],
            arrowcolor=[("active", COLORS["primary"]), ("focus", COLORS["primary"])],
            selectbackground=[("readonly", COLORS["surface"])],
            selectforeground=[("readonly", COLORS["text"])],
            foreground=[("disabled", COLORS["muted"])],
        )
        style.layout(combo_style, [
            ("Combobox.padding", {
                "sticky": "nswe",
                "children": [("Combobox.textarea", {"sticky": "nswe"})],
            }),
        ])
    style.configure("TCheckbutton", background=COLORS["surface"], foreground=COLORS["text_secondary"], padding=(0, 3))
    style.map(
        "TCheckbutton",
        background=[("active", COLORS["surface"])],
        foreground=[("active", COLORS["primary"]), ("disabled", COLORS["muted"])],
    )
    style.configure("Horizontal.TProgressbar", troughcolor=COLORS["subtle"], background=COLORS["primary"], bordercolor=COLORS["subtle"], lightcolor=COLORS["primary"], darkcolor=COLORS["primary"])
    style.layout("Modern.Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"}),
        ]}),
    ])
    style.layout("Modern.Horizontal.TScrollbar", [
        ("Horizontal.Scrollbar.trough", {"sticky": "ew", "children": [
            ("Horizontal.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"}),
        ]}),
    ])
    for scrollbar_style in ("Modern.Vertical.TScrollbar", "Modern.Horizontal.TScrollbar"):
        style.configure(
            scrollbar_style, background=COLORS["border_strong"], troughcolor=COLORS["subtle"],
            bordercolor=COLORS["subtle"], lightcolor=COLORS["border_strong"],
            darkcolor=COLORS["border_strong"], relief="flat", borderwidth=0, width=9,
        )
        style.map(scrollbar_style, background=[("active", COLORS["hover_border"]), ("pressed", COLORS["primary"])])
    style.configure("Status.Success.TLabel", foreground=COLORS["success"])
    style.configure("Status.Warning.TLabel", foreground=COLORS["warning"])
    style.configure("Status.Danger.TLabel", foreground=COLORS["danger"])
    style.configure("TLabelframe", background=COLORS["surface"], bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"], relief="solid", padding=14)
    style.configure("TLabelframe.Label", background=COLORS["surface"], foreground=COLORS["text"], font=(family, 11, "bold"), padding=(0, 0, 8, 0))
    return style

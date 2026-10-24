import tkinter as tk
from tkinter import ttk
from pathlib import Path

from src.tk_pages.components import (
    Button, Card, Checkbutton, ColorFrame, ColorLabel, Combobox, Entry, Frame, Label,
    LabelFrame, Progressbar, Separator, StatusBadge, Text,
)


ACTUATOR_ROOT = Path(__file__).resolve().parents[1]
TK_PAGES_ROOT = ACTUATOR_ROOT / "src" / "tk_pages"


def test_component_package_replaces_legacy_single_file():
    assert (TK_PAGES_ROOT / "components" / "__init__.py").is_file()
    assert not (TK_PAGES_ROOT / "components.py").exists()


def test_component_widgets_inherit_standard_tk_widgets():
    assert issubclass(Frame, ttk.Frame)
    assert issubclass(Label, ttk.Label)
    assert issubclass(Button, tk.Canvas)
    assert issubclass(Entry, tk.Frame)
    assert issubclass(Combobox, tk.Frame)
    assert issubclass(Checkbutton, ttk.Checkbutton)
    assert issubclass(Separator, ttk.Separator)
    assert issubclass(Progressbar, ttk.Progressbar)
    assert issubclass(LabelFrame, ttk.LabelFrame)
    assert issubclass(ColorFrame, tk.Frame)
    assert issubclass(ColorLabel, tk.Label)
    assert issubclass(StatusBadge, tk.Canvas)
    assert issubclass(Card, tk.Canvas)
    assert issubclass(Text, tk.Text)


def test_pages_and_application_only_construct_visible_widgets_from_component_package():
    sources = [TK_PAGES_ROOT / "application.py", *(TK_PAGES_ROOT / "pages").glob("*.py")]
    forbidden = (
        "ttk.Button(", "ttk.Label(", "ttk.Entry(", "ttk.Combobox(", "ttk.Frame(",
        "ttk.Checkbutton(", "ttk.Progressbar(", "ttk.Separator(", "ttk.LabelFrame(",
        "tk.Label(", "tk.Frame(", "tk.Text(",
    )
    for source in sources:
        content = source.read_text(encoding="utf-8")
        for constructor in forbidden:
            assert constructor not in content, f"{source.name} 绕过统一组件：{constructor}"

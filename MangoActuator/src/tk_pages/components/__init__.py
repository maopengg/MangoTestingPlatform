"""MangoActuator's styled tkinter component library.

Pages should import visible widgets from this package instead of constructing raw
``tk``/``ttk`` widgets with page-local colors and style names.
"""

from .forms import FormGrid, Switch
from .layout import Card, ConstrainedFrame, Page
from .scrolling import AutoHideScrollbar, ScrollableFrame
from .utils import combo_value, run_in_thread, set_combo_by_value
from .widgets import (
    Button,
    Checkbutton,
    ColorFrame,
    ColorLabel,
    Combobox,
    Entry,
    Frame,
    Label,
    LabelFrame,
    Progressbar,
    Separator,
    StatusBadge,
    Text,
    readonly_combo,
)

__all__ = [
    "AutoHideScrollbar", "Button", "Card", "Checkbutton", "ColorFrame",
    "ColorLabel", "Combobox", "ConstrainedFrame", "Entry", "FormGrid",
    "Frame", "Label", "LabelFrame", "Page", "Progressbar", "ScrollableFrame",
    "Separator", "StatusBadge", "Switch", "Text", "combo_value",
    "readonly_combo", "run_in_thread", "set_combo_by_value",
]

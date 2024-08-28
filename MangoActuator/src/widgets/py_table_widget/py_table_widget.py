from PySide6.QtWidgets import QTableWidget

from src.settings.settings import THEME
from src.widgets.py_table_widget.style import style


class PyTableWidget(QTableWidget):
    def __init__(
            self,
            radius=8,
            color=THEME.text_foreground,
            bg_color=THEME.bg_two,
            selection_color=THEME.context_color,
            header_horizontal_color=THEME.dark_two,
            header_vertical_color=THEME.bg_three,
            bottom_line_color=THEME.bg_three,
            grid_line_color=THEME.bg_one,
            scroll_bar_bg_color=THEME.bg_one,
            scroll_bar_btn_color=THEME.dark_four,
            context_color=THEME.context_color
    ):
        super().__init__()

        # PARAMETERS
        self.setStyleSheet(style.format(
            _radius=radius,
            _color=color,
            _bg_color=bg_color,
            _header_horizontal_color=header_horizontal_color,
            _header_vertical_color=header_vertical_color,
            _selection_color=selection_color,
            _bottom_line_color=bottom_line_color,
            _grid_line_color=grid_line_color,
            _scroll_bar_bg_color=scroll_bar_bg_color,
            _scroll_bar_btn_color=scroll_bar_btn_color,
            _context_color=context_color
        ))

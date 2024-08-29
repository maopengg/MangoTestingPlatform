from PySide6.QtWidgets import QLineEdit

from src.settings.settings import THEME

style = '''
QLineEdit {{
	background-color: {_bg_color};
	border-radius: {_radius}px;
	border: {_border_size}px solid transparent;
	padding-left: 10px;
    padding-right: 10px;
	selection-color: {_selection_color};
	selection-background-color: {_context_color};
    color: {_color};
}}
QLineEdit:focus {{
	border: {_border_size}px solid {_context_color};
    background-color: {_bg_color_active};
}}
'''


# PY PUSH BUTTON

class PyLineEdit(QLineEdit):
    def __init__(
            self,
            text,
            place_holder_text,
            is_password: bool = False,
            radius=8,
            border_size=2,
            color=THEME.text_foreground,
            selection_color=THEME.white,
            bg_color=THEME.white,
            bg_color_active=THEME.dark_three,
            context_color=THEME.context_color
    ):
        super().__init__()

        # PARAMETERS
        if text:
            self.setText(text)
        if is_password:
            self.setEchoMode(QLineEdit.Password)
        if place_holder_text:
            self.setPlaceholderText(place_holder_text)

        # SET STYLESHEET
        self.set_stylesheet(
            radius,
            border_size,
            color,
            selection_color,
            bg_color,
            bg_color_active,
            context_color
        )

    # SET STYLESHEET
    def set_stylesheet(
            self,
            radius,
            border_size,
            color,
            selection_color,
            bg_color,
            bg_color_active,
            context_color
    ):
        # APPLY STYLESHEET
        style_format = style.format(
            _radius=radius,
            _border_size=border_size,
            _color=color,
            _selection_color=selection_color,
            _bg_color=bg_color,
            _bg_color_active=bg_color_active,
            _context_color=context_color
        )
        self.setStyleSheet(style_format)

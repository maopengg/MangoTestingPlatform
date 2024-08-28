from PySide6.QtGui import QColor, Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QGraphicsDropShadowEffect

from src.settings.settings import STYLE, THEME
from src.widgets.py_window.styles import Styles


class PyWindow(QFrame):
    def __init__(
            self,
            parent,
            layout=Qt.Vertical,
            margin=0,
            spacing=2,
            bg_color=THEME.bg_one,
            text_color=THEME.text_foreground,
            text_font="9pt 'Segoe UI'",
            border_radius=10,
            border_size=2,
            border_color=THEME.bg_two,
            enable_shadow=True
    ):
        super().__init__()

        # PROPERTIES

        self.parent = parent
        self.layout = layout
        self.margin = margin
        self.bg_color = bg_color
        self.text_color = text_color
        self.text_font = text_font
        self.border_radius = border_radius
        self.border_size = border_size
        self.border_color = border_color
        self.enable_shadow = enable_shadow

        # OBJECT NAME

        self.setObjectName("pod_bg_app")

        # APPLY STYLESHEET

        self.set_stylesheet()

        # ADD LAYOUT
        if layout == Qt.Vertical:
            # VERTICAL LAYOUT
            self.layout = QHBoxLayout(self)
        else:
            # HORIZONTAL LAYOUT
            self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(margin, margin, margin, margin)
        self.layout.setSpacing(spacing)

        # ADD DROP SHADOW

        if STYLE.custom_title_bar:
            if enable_shadow:
                self.shadow = QGraphicsDropShadowEffect()
                self.shadow.setBlurRadius(20)
                self.shadow.setXOffset(0)
                self.shadow.setYOffset(0)
                self.shadow.setColor(QColor(0, 0, 0, 160))
                self.setGraphicsEffect(self.shadow)

    # APPLY AND UPDATE STYLESHEET

    def set_stylesheet(
            self,
            bg_color=None,
            border_radius=None,
            border_size=None,
            border_color=None,
            text_color=None,
            text_font=None
    ):
        # CHECK BG COLOR
        if bg_color != None:
            internal_bg_color = bg_color
        else:
            internal_bg_color = self.bg_color

        # CHECK BORDER RADIUS
        if border_radius != None:
            internal_border_radius = border_radius
        else:
            internal_border_radius = self.border_radius

        # CHECK BORDER SIZE
        if border_size != None:
            internal_border_size = border_size
        else:
            internal_border_size = self.border_size

        # CHECK BORDER COLOR
        if text_color != None:
            internal_text_color = text_color
        else:
            internal_text_color = self.text_color

        # CHECK TEXT COLOR
        if border_color != None:
            internal_border_color = border_color
        else:
            internal_border_color = self.border_color

        # CHECK TEXT COLOR
        if text_font != None:
            internal_text_font = text_font
        else:
            internal_text_font = self.text_font

        self.setStyleSheet(Styles.bg_style.format(
            _bg_color=internal_bg_color,
            _border_radius=internal_border_radius,
            _border_size=internal_border_size,
            _border_color=internal_border_color,
            _text_color=internal_text_color,
            _text_font=internal_text_font
        ))

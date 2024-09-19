# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *


class MangoIconButton(QPushButton):
    def __init__(
            self,
            parent,
            app_parent,
            icon_path=":/icons/icon_heart.svg",
            tooltip_text="",
            btn_id=None,
            width=30,
            height=30,
            radius=8,
            bg_color=THEME.dark_one,
            bg_color_hover=THEME.dark_three,
            bg_color_pressed=THEME.pink,
            icon_color=THEME.icon_color,
            icon_color_hover=THEME.icon_hover,
            icon_color_pressed=THEME.icon_active,  # THEME.icon_active
            icon_color_active=THEME.icon_active,
            dark_one=THEME.dark_one,
            text_foreground="#8a95aa",
            context_color="#568af2",
            top_margin=40,
            is_active=False
    ):
        super().__init__()

        self.setFixedSize(width, height)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName(btn_id)

        self._bg_color = bg_color
        self._bg_color_hover = bg_color_hover
        self._bg_color_pressed = bg_color_pressed
        self._icon_color = icon_color
        self._icon_color_hover = icon_color_hover
        self._icon_color_pressed = icon_color_pressed
        self._icon_color_active = icon_color_active
        self._context_color = context_color
        self._top_margin = top_margin
        self._is_active = is_active
        self._set_bg_color = bg_color
        self._set_icon_path = icon_path
        self._set_icon_color = icon_color
        self._set_border_radius = radius
        self._parent = parent
        self._app_parent = app_parent

        self._tooltip_text = tooltip_text
        self._tooltip = _ToolTip(
            app_parent,
            tooltip_text,
            dark_one,
            text_foreground
        )
        self._tooltip.hide()

    def set_active(self, is_active):
        self._is_active = is_active
        self.repaint()

    def is_active(self):
        return self._is_active

    def paintEvent(self, event):
        paint = QPainter()
        paint.begin(self)
        paint.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._is_active:
            brush = QBrush(QColor(self._context_color))
        else:
            brush = QBrush(QColor(self._set_bg_color))

        rect = QRect(0, 0, self.width(), self.height())
        paint.setPen(Qt.NoPen)
        paint.setBrush(brush)
        paint.drawRoundedRect(
            rect,
            self._set_border_radius,
            self._set_border_radius
        )

        self.icon_paint(paint, self._set_icon_path, rect)

        paint.end()

    def change_style(self, event):
        if event == QEvent.Enter:
            self._set_bg_color = self._bg_color_hover
            self._set_icon_color = self._icon_color_hover
            self.repaint()
        elif event == QEvent.Leave:
            self._set_bg_color = self._bg_color
            self._set_icon_color = self._icon_color
            self.repaint()
        elif event == QEvent.MouseButtonPress:
            self._set_bg_color = self._bg_color_pressed
            self._set_icon_color = self._icon_color_pressed
            self.repaint()
        elif event == QEvent.MouseButtonRelease:
            self._set_bg_color = self._bg_color_hover
            self._set_icon_color = self._icon_color_hover
            self.repaint()

    def enterEvent(self, event):
        self.change_style(QEvent.Enter)
        self.move_tooltip()
        self._tooltip.show()

    def leaveEvent(self, event):
        self.change_style(QEvent.Leave)
        self.move_tooltip()
        self._tooltip.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.change_style(QEvent.MouseButtonPress)
            self.setFocus()
            return self.clicked.emit()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.change_style(QEvent.MouseButtonRelease)
            return self.released.emit()

    def icon_paint(self, qp, image, rect):
        icon = QPixmap(image)
        painter = QPainter(icon)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        if self._is_active:
            painter.fillRect(icon.rect(), self._icon_color_active)
        else:
            painter.fillRect(icon.rect(), self._set_icon_color)
        qp.drawPixmap(
            (rect.width() - icon.width()) / 2,
            (rect.height() - icon.height()) / 2,
            icon
        )
        painter.end()

    def set_icon(self, icon_path):
        self._set_icon_path = icon_path
        self.repaint()

    def move_tooltip(self):
        gp = self.mapToGlobal(QPoint(0, 0))

        pos = self._parent.mapFromGlobal(gp)

        pos_x = (pos.x() - (self._tooltip.width() // 2)) + (self.width() // 2)
        pos_y = pos.y() - self._top_margin

        self._tooltip.move(pos_x, pos_y)


class _ToolTip(QLabel):
    style_tooltip = """ 
    QLabel {{		
        background-color: {_dark_one};	
        color: {_text_foreground};
        padding-left: 10px;
        padding-right: 10px;
        border-radius: 17px;
        border: 0px solid transparent;
        font: 800 9pt "Segoe UI";
    }}
    """

    def __init__(
            self,
            parent,
            tooltip,
            dark_one,
            text_foreground
    ):
        QLabel.__init__(self)

        style = self.style_tooltip.format(
            _dark_one=dark_one,
            _text_foreground=text_foreground
        )
        self.setObjectName(u"label_tooltip")
        self.setStyleSheet(style)
        self.setMinimumHeight(34)
        self.setParent(parent)
        self.setText(tooltip)
        self.adjustSize()
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(30)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self.shadow)

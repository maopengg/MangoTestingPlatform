# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
import os

from PySide6.QtCore import QRect, QEvent, QPoint
from PySide6.QtGui import QColor, Qt, QPainter, QPixmap
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QLabel, QPushButton

from src.settings.settings import THEME


class MangoLeftMenuButton(QPushButton):
    def __init__(
            self,
            app_parent,
            text,
            btn_id=None,
            tooltip_text="",
            margin=4,
            dark_one=THEME.dark_one,
            dark_three=THEME.dark_three,
            dark_four=THEME.dark_four,
            bg_one=THEME.bg_one,
            icon_color=THEME.icon_color,
            icon_color_hover=THEME.icon_hover,
            icon_color_pressed=THEME.icon_pressed,
            icon_color_active=THEME.icon_active,
            context_color=THEME.context_color,
            text_foreground=THEME.text_foreground,
            text_active=THEME.text_active,
            icon_path=":/icons/icon_add_user.svg",
            icon_active_menu=":/icons/active_menu.svg",
            is_active=False,
            is_active_tab=False,
            is_toggle_active=False
    ):
        super().__init__()
        self.setText(text)
        self.setCursor(Qt.PointingHandCursor)
        self.setMaximumHeight(50)
        self.setMinimumHeight(50)
        self.setObjectName(btn_id)

        self._icon_path = icon_path
        self._icon_active_menu = icon_active_menu

        self._margin = margin
        self._dark_one = dark_one
        self._dark_three = dark_three
        self._dark_four = dark_four
        self._bg_one = bg_one
        self._context_color = context_color
        self._icon_color = icon_color
        self._icon_color_hover = icon_color_hover
        self._icon_color_pressed = icon_color_pressed
        self._icon_color_active = icon_color_active
        self._set_icon_color = self._icon_color
        self._set_bg_color = self._dark_one
        self._set_text_foreground = text_foreground
        self._set_text_active = text_active
        self._parent = app_parent
        self._is_active = is_active
        self._is_active_tab = is_active_tab
        self._is_toggle_active = is_toggle_active

        # 工具提示
        self._tooltip_text = tooltip_text
        self.tooltip = _ToolTip(
            app_parent,
            tooltip_text,
            dark_one,
            context_color,
            text_foreground
        )
        self.tooltip.hide()

    # PAINT EVENT

    def paintEvent(self, event):
        # PAINTER
        p = QPainter()
        p.begin(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setFont(self.font())

        # RECTANGLES
        rect = QRect(4, 5, self.width(), self.height() - 10)
        rect_inside = QRect(4, 5, self.width() - 8, self.height() - 10)
        rect_icon = QRect(0, 0, 50, self.height())
        rect_blue = QRect(4, 5, 20, self.height() - 10)
        rect_inside_active = QRect(7, 5, self.width(), self.height() - 10)
        rect_text = QRect(45, 0, self.width() - 50, self.height())

        if self._is_active:
            # DRAW BG BLUE
            p.setBrush(QColor(self._context_color))
            p.drawRoundedRect(rect_blue, 8, 8)

            # BG INSIDE
            p.setBrush(QColor(self._bg_one))
            p.drawRoundedRect(rect_inside_active, 8, 8)

            # DRAW ACTIVE
            icon_path = self._icon_active_menu
            app_path = os.path.abspath(os.getcwd())
            icon_path = os.path.normpath(os.path.join(app_path, icon_path))
            self._set_icon_color = self._icon_color_active
            self.icon_active(p, icon_path, self.width())

            # DRAW TEXT
            p.setPen(QColor(self._set_text_active))
            p.drawText(rect_text, Qt.AlignVCenter, self.text())

            # DRAW ICONS
            self.icon_paint(p, self._icon_path, rect_icon, self._set_icon_color)

        elif self._is_active_tab:
            # DRAW BG BLUE
            p.setBrush(QColor(self._dark_four))
            p.drawRoundedRect(rect_blue, 8, 8)

            # BG INSIDE
            p.setBrush(QColor(self._bg_one))
            p.drawRoundedRect(rect_inside_active, 8, 8)

            # DRAW ACTIVE
            icon_path = self._icon_active_menu
            app_path = os.path.abspath(os.getcwd())
            icon_path = os.path.normpath(os.path.join(app_path, icon_path))
            self._set_icon_color = self._icon_color_active
            self.icon_active(p, icon_path, self.width())

            # DRAW TEXT
            p.setPen(QColor(self._set_text_active))
            p.drawText(rect_text, Qt.AlignVCenter, self.text())

            # DRAW ICONS
            self.icon_paint(p, self._icon_path, rect_icon, self._set_icon_color)

        # NORMAL BG
        else:
            if self._is_toggle_active:
                # BG INSIDE
                p.setBrush(QColor(self._dark_three))
                p.drawRoundedRect(rect_inside, 8, 8)

                # DRAW TEXT
                p.setPen(QColor(self._set_text_foreground))
                p.drawText(rect_text, Qt.AlignVCenter, self.text())

                # DRAW ICONS
                if self._is_toggle_active:
                    self.icon_paint(p, self._icon_path, rect_icon, self._context_color)
                else:
                    self.icon_paint(p, self._icon_path, rect_icon, self._set_icon_color)
            else:
                # BG INSIDE
                p.setBrush(QColor(self._set_bg_color))
                p.drawRoundedRect(rect_inside, 8, 8)

                # DRAW TEXT
                p.setPen(QColor(self._set_text_foreground))
                p.drawText(rect_text, Qt.AlignVCenter, self.text())

                # DRAW ICONS
                self.icon_paint(p, self._icon_path, rect_icon, self._set_icon_color)

        p.end()

    # SET ACTIVE MENU

    def set_active(self, is_active):
        self._is_active = is_active
        if not is_active:
            self._set_icon_color = self._icon_color
            self._set_bg_color = self._dark_one

        self.repaint()

    # SET ACTIVE TAB MENU

    def set_active_tab(self, is_active):
        self._is_active_tab = is_active
        if not is_active:
            self._set_icon_color = self._icon_color
            self._set_bg_color = self._dark_one

        self.repaint()

    # 如果是活动菜单，则返回
    def is_active(self):
        return self._is_active

    # 如果选项卡菜单处于活动状态，则返回
    def is_active_tab(self):
        return self._is_active_tab

    # 设置活动切换
    def set_active_toggle(self, is_active):
        self._is_toggle_active = is_active

    # 设置图标
    def set_icon(self, icon_path):
        self._icon_path = icon_path
        self.repaint()

    # 用颜色绘制图标
    def icon_paint(self, qp, image, rect, color):
        icon = QPixmap(image)
        painter = QPainter(icon)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(icon.rect(), color)
        qp.drawPixmap(
            (rect.width() - icon.width()) / 2,
            (rect.height() - icon.height()) / 2,
            icon
        )
        painter.end()

    # 在右侧绘制活动图标
    def icon_active(self, qp, image, width):
        icon = QPixmap(image)
        painter = QPainter(icon)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(icon.rect(), self._bg_one)
        qp.drawPixmap(width - 5, 0, icon)
        painter.end()

    # 更改样式
    def change_style(self, event):
        if event == QEvent.Enter:
            if not self._is_active:
                self._set_icon_color = self._icon_color_hover
                self._set_bg_color = self._dark_three
            self.repaint()
        elif event == QEvent.Leave:
            if not self._is_active:
                self._set_icon_color = self._icon_color
                self._set_bg_color = self._dark_one
            self.repaint()
        elif event == QEvent.MouseButtonPress:
            if not self._is_active:
                self._set_icon_color = self._context_color
                self._set_bg_color = self._dark_four
            self.repaint()
        elif event == QEvent.MouseButtonRelease:
            if not self._is_active:
                self._set_icon_color = self._icon_color_hover
                self._set_bg_color = self._dark_three
            self.repaint()

    # 当鼠标位于BTN上时触发的事件
    def enterEvent(self, event):
        self.change_style(QEvent.Enter)
        if self.width() == 50 and self._tooltip_text:
            self.move_tooltip()
            self.tooltip.show()

    # 鼠标离开BTN时触发的事件
    def leaveEvent(self, event):
        self.change_style(QEvent.Leave)
        self.tooltip.hide()

    # 按下左键时触发的事件
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.change_style(QEvent.MouseButtonPress)
            self.tooltip.hide()
            return self.clicked.emit()

    # 松开鼠标按钮后触发的事件
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.change_style(QEvent.MouseButtonRelease)
            return self.released.emit()

    def move_tooltip(self):
        gp = self.mapToGlobal(QPoint(0, 0))

        pos = self._parent.mapFromGlobal(gp)

        pos_x = pos.x() + self.width() + 5
        pos_y = pos.y() + (self.width() - self.tooltip.height()) // 2

        self.tooltip.move(pos_x, pos_y)


class _ToolTip(QLabel):
    style_tooltip = """ 
    QLabel {{		
        background-color: {_dark_one};	
        color: {_text_foreground};
        padding-left: 10px;
        padding-right: 10px;
        border-radius: 17px;
        border: 0px solid transparent;
        border-left: 3px solid {_context_color};
        font: 800 9pt "Segoe UI";
    }}
    """

    def __init__(
            self,
            parent,
            tooltip,
            dark_one,
            context_color,
            text_foreground
    ):
        QLabel.__init__(self)

        style = self.style_tooltip.format(
            _dark_one=dark_one,
            _context_color=context_color,
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

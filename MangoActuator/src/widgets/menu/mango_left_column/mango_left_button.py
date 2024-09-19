# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *


class MangoLeftButton(QPushButton):
    def __init__(
            self,
            parent,
            app_parent=None,
            tooltip_text="",
            btn_id=None,
            width=30,
            height=30,
            radius=8,
            bg_color="#343b48",
            bg_color_hover="#3c4454",
            bg_color_pressed="#2c313c",
            icon_color="#c3ccdf",
            icon_color_hover="#dce1ec",
            icon_color_pressed="#edf0f5",
            icon_color_active="#f5f6f9",
            icon_path="",
            dark_one="#1b1e23",
            context_color="#568af2",
            text_foreground="#8a95aa",
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
        self._top_margin = self.height() + 6
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
            context_color,
            text_foreground
        )
        self._tooltip.hide()

    #设置活动菜单
    def set_active(self, is_active):
        self._is_active = is_active
        self.repaint()

    # 如果是活动菜单，则返回
    def is_active(self):
        return self._is_active

    # 绘制按钮和图标
    def paintEvent(self, event):
        paint = QPainter()
        paint.begin(self)
        paint.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._is_active:
            brush = QBrush(QColor(self._bg_color_pressed))
        else:
            brush = QBrush(QColor(self._set_bg_color))

        # 创建矩形
        rect = QRect(0, 0, self.width(), self.height())
        paint.setPen(Qt.NoPen)
        paint.setBrush(brush)
        paint.drawRoundedRect(
            rect,
            self._set_border_radius,
            self._set_border_radius
        )

        # 绘制图标
        self.icon_paint(paint, self._set_icon_path, rect)

        # 末端油漆工
        paint.end()

    # 更新样式
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

    # 鼠标悬停
    # 当鼠标位于BTN上时触发的事件
    def enterEvent(self, event):
        self.change_style(QEvent.Enter)
        self.move_tooltip()
        self._tooltip.show()

    # 鼠标离开
    # 鼠标离开BTN时触发的事件
    def leaveEvent(self, event):
        self.change_style(QEvent.Leave)
        self.move_tooltip()
        self._tooltip.hide()

    # 鼠标按压
    # 按下左键时触发的事件
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.change_style(QEvent.MouseButtonPress)
            self.setFocus()
            return self.clicked.emit()

    # 鼠标释放
    # 松开鼠标按钮后触发的事件
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.change_style(QEvent.MouseButtonRelease)
            return self.released.emit()

    # 用颜色绘制图标
    def icon_paint(self, qp, image, rect):
        icon = QPixmap(image)
        painter = QPainter(icon)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        if self._is_active:
            painter.fillRect(icon.rect(), self._context_color)
        else:
            painter.fillRect(icon.rect(), self._set_icon_color)
        qp.drawPixmap(
            (rect.width() - icon.width()) / 2,
            (rect.height() - icon.height()) / 2,
            icon
        )
        painter.end()

    # 设置图标
    def set_icon(self, icon_path):
        self._set_icon_path = icon_path
        self.repaint()

    # 移动工具提示
    def move_tooltip(self):
        # 获取主窗口父窗口
        gp = self.mapToGlobal(QPoint(0, 0))

        # 设置小部件以获取位置
        # 返回小部件在应用程序中的绝对位置
        pos = self._parent.mapFromGlobal(gp)

        # 使用偏移调整工具提示位置
        pos_x = (pos.x() - self._tooltip.width()) + self.width() + 5
        pos_y = pos.y() + self._top_margin

        # 移动工具提示位置
        self._tooltip.move(pos_x, pos_y)


# TOOLTIP

class _ToolTip(QLabel):
    style_tooltip = """ 
    QLabel {{		
        background-color: {_dark_one};	
        color: {_text_foreground};
        padding-left: 10px;
        padding-right: 10px;
        border-radius: 17px;
        border: 0px solid transparent;
        border-right: 3px solid {_context_color};
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

        # 设置阴影
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(30)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(self.shadow)

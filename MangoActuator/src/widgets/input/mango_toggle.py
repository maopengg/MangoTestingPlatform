# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2024-08-16 17:05
# @Author : 毛鹏
from src import *
from src.enums.tools_enum import StatusEnum


class MangoToggle(QCheckBox):
    clicked = Signal(object)

    def __init__(
            self,
            value=False,
            data=StatusEnum.get_select(),
            theme=THEME,
    ):
        QCheckBox.__init__(self)
        self.value = value
        self.data = data
        self.theme = theme
        self.setFixedSize(50, 28)
        self.setCursor(Qt.PointingHandCursor)

        self._position = 3
        self.animation = QPropertyAnimation(self, b"position")
        self.animation.setEasingCurve(QEasingCurve.OutBounce)
        self.animation.setDuration(500)
        self.stateChanged.connect(self.setup_animation)
        self.set_value(self.value)

    def get_value(self) -> int:

        return int(self.isChecked())

    def set_value(self, value: bool | StatusEnum):
        if value is None:
            return
        self.value = value
        if isinstance(value, StatusEnum):
            self.value = bool(value)
        else:
            self.value = value
        self.setChecked(self.value)

    @Property(float)
    def position(self):
        return self._position

    @position.setter
    def position(self, pos):
        self._position = pos
        self.update()

    # START STOP ANIMATION
    def setup_animation(self, value):
        self.animation.stop()
        if value:
            self.animation.setEndValue(self.width() - 26)
        else:
            self.animation.setEndValue(4)
        self.animation.start()
        self.clicked.emit({'value': int(self.isChecked())})


    def hitButton(self, pos: QPoint):
        return self.contentsRect().contains(pos)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setFont(QFont("Segoe UI", 9))

        p.setPen(Qt.NoPen)

        rect = QRect(0, 0, self.width(), self.height())
        if not self.isChecked():
            p.setBrush(QColor(self.theme.dark_two))
            p.drawRoundedRect(0, 0, rect.width(), 28, 14, 14)
            p.setBrush(QColor(self.theme.dark_one))
            p.drawEllipse(self._position, 3, 22, 22)
        else:
            p.setBrush(QColor(self.theme.green))
            p.drawRoundedRect(0, 0, rect.width(), 28, 14, 14)
            p.setBrush(QColor(self.theme.dark_one))
            p.drawEllipse(self._position, 3, 22, 22)
        p.end()

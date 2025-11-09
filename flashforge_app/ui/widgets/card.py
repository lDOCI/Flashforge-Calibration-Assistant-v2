from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class CardWidget(QWidget):
    """
    Elevated information card with subtle glow and hover animation.
    """

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str | None = None,
        accent_color: str = "#5C6BF5",
        parent: QWidget | None = None,
        compact: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self._accent_color = QColor(accent_color)
        if accent_color != "#5C6BF5":
            self.setProperty("variant", "accent")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._hover_progress = 0.0
        self._hover_animation = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_animation.setDuration(220)
        self._hover_animation.setEasingCurve(QEasingCurve.InOutSine)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 10, 12, 10) if compact else layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)
        self.setLayout(layout)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("CardTitle")
        layout.addWidget(self._title_label)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("CardValue")
        self._value_label.setWordWrap(True)
        self._value_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._value_label)
        self._default_value_font = self._value_label.font()

        self._subtitle_label: QLabel | None = None
        if subtitle is not None:
            self._subtitle_label = QLabel(subtitle)
            self._subtitle_label.setObjectName("Subtitle")
            layout.addWidget(self._subtitle_label)

        if not compact:
            layout.addStretch(1)

        self.setAttribute(Qt.WA_Hover)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._hover_progress <= 0:
            return

        radius = 18
        pen = QPen(QColor(self._accent_color))
        pen.setWidth(2)
        pen.setColor(self._accent_color)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(pen)
        painter.setOpacity(0.2 * self._hover_progress)
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()

    def enterEvent(self, event) -> None:
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_to(0.0)
        super().leaveEvent(event)

    def _animate_to(self, value: float) -> None:
        self._hover_animation.stop()
        self._hover_animation.setStartValue(self._hover_progress)
        self._hover_animation.setEndValue(value)
        self._hover_animation.start()

    def getHoverProgress(self) -> float:
        return self._hover_progress

    def setHoverProgress(self, value: float) -> None:
        self._hover_progress = value
        self.update()

    hoverProgress = Property(float, getHoverProgress, setHoverProgress)

    # ------------------------------------------------------------------ public API
    def set_title(self, text: str) -> None:
        self._title_label.setText(text)

    def set_value(self, text: str) -> None:
        self._value_label.setText(text)
        self._value_label.setAlignment(Qt.AlignCenter)

    def set_subtitle(self, text: str | None) -> None:
        if text is None:
            if self._subtitle_label is not None:
                self._subtitle_label.hide()
        else:
            if self._subtitle_label is None:
                self._subtitle_label = QLabel(text)
                self._subtitle_label.setObjectName("Subtitle")
                self.layout().addWidget(self._subtitle_label)
            self._subtitle_label.setText(text)
            self._subtitle_label.show()

    def set_value_font(self, point_size: int) -> None:
        font = self._value_label.font()
        font.setPointSize(point_size)
        self._value_label.setFont(font)

    def reset_value_font(self) -> None:
        self._value_label.setFont(self._default_value_font)

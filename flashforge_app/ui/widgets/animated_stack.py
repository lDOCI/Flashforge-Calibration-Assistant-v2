from __future__ import annotations

from PySide6.QtCore import QEasingCurve, Property, QPropertyAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


class AnimatedStackedWidget(QStackedWidget):
    """
    QStackedWidget with cross-fade animation between pages.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_opacity = 1.0
        self._pending_index: int | None = None

        self._fade_effect = QGraphicsOpacityEffect(self)
        self._fade_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._fade_effect)

        self._animation = QPropertyAnimation(self, b"opacity", self)
        self._animation.setDuration(240)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

    def setCurrentIndex(self, index: int) -> None:
        if index == self.currentIndex():
            return

        self._pending_index = index
        self._start_fade_out()

    def _start_fade_out(self) -> None:
        try:
            self._animation.finished.disconnect()
        except TypeError:
            pass
        self._animation.setStartValue(1.0)
        self._animation.setEndValue(0.0)
        self._animation.finished.connect(self._on_fade_out_finished)
        self._animation.start()

    def _on_fade_out_finished(self) -> None:
        if self._pending_index is not None:
            super().setCurrentIndex(self._pending_index)
        try:
            self._animation.finished.disconnect()
        except TypeError:
            pass
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.finished.connect(self._on_fade_in_finished)
        self._animation.start()

    def _on_fade_in_finished(self) -> None:
        try:
            self._animation.finished.disconnect()
        except TypeError:
            pass
        self._pending_index = None
        self._fade_effect.setOpacity(1.0)

    def getOpacity(self) -> float:
        return self._current_opacity

    def setOpacity(self, value: float) -> None:
        self._current_opacity = value
        self._fade_effect.setOpacity(value)

    opacity = Property(float, getOpacity, setOpacity)

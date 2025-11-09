from __future__ import annotations

from typing import Iterable, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QToolButton,
    QWidget,
)


class TopBar(QFrame):
    """Header toolbar with search, quick actions, and status display."""

    theme_toggle_requested = Signal()
    language_selected = Signal(str)
    author_button_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopBar")

        layout = QHBoxLayout()
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        self.setLayout(layout)

        self.app_title = QLabel("Flashforge Calibration Assistant")
        self.app_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(self.app_title)

        layout.addStretch(1)

        self.status_label = QLabel()
        self.status_label.setObjectName("Subtitle")
        layout.addWidget(self.status_label)

        self.theme_button = QToolButton()
        self.theme_button.setText("☾")
        self.theme_button.setCursor(Qt.PointingHandCursor)
        self.theme_button.clicked.connect(self.theme_toggle_requested.emit)
        layout.addWidget(self.theme_button)

        self.language_button = QToolButton()
        self.language_button.setCursor(Qt.PointingHandCursor)
        self.language_button.setPopupMode(QToolButton.InstantPopup)
        self.language_menu = QMenu(self)
        self.language_button.setMenu(self.language_menu)
        layout.addWidget(self.language_button)

        self.author_button = QPushButton("Operator")
        self.author_button.setCursor(Qt.PointingHandCursor)
        self.author_button.setIcon(QIcon.fromTheme("user"))
        self.author_button.clicked.connect(self.author_button_clicked.emit)
        layout.addWidget(self.author_button)

    # ------------------------------------------------------------------ translation support
    def apply_translations(
        self,
        *,
        title: str,
        theme_hint: str,
        language_hint: str,
        author_label: str,
    ) -> None:
        self.app_title.setText(title)
        self.theme_button.setToolTip(theme_hint)
        self.language_button.setToolTip(language_hint)
        self.author_button.setText(author_label)

    def set_languages(self, languages: Iterable[Tuple[str, str]], current: str) -> None:
        self.language_menu.clear()
        for code, name in languages:
            action = self.language_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(code == current)
            # capture code in default argument to avoid late binding
            action.triggered.connect(lambda checked=False, c=code: self.language_selected.emit(c))
        self.language_button.setText(current.upper())

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_theme_icon(self, theme: str) -> None:
        self.theme_button.setText("☾" if theme == "dark" else "☀")

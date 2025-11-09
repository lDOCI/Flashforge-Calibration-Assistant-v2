from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QListWidget, QListWidgetItem


class SideMenu(QListWidget):
    """
    Styled side navigation with icons and selection signals.
    """

    activated = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SideMenu")
        self.setSpacing(6)
        self.setIconSize(QSize(20, 20))
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setFocusPolicy(Qt.NoFocus)
        self._items: Dict[str, QListWidgetItem] = {}

        self.currentItemChanged.connect(self._handle_selection_change)

    def add_entry(self, key: str, label: str, icon_path: Optional[Path] = None) -> None:
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, key)
        if icon_path and icon_path.exists():
            item.setIcon(QIcon(str(icon_path)))
        self.addItem(item)
        self._items[key] = item

    def set_current(self, key: str) -> None:
        if key in self._items:
            self.setCurrentItem(self._items[key])

    def set_label(self, key: str, label: str) -> None:
        item = self._items.get(key)
        if item:
            item.setText(label)

    def _handle_selection_change(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if not current:
            return
        key = current.data(Qt.UserRole)
        if key:
            self.activated.emit(key)

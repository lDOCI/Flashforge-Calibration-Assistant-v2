from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from flashforge_app.services.localization import LocalizationService


class AuthorDialog(QDialog):
    """Informational dialog with author details and a small easter egg."""

    _TARGET_CLICKS = 15

    def __init__(self, localization: LocalizationService, parent=None) -> None:
        super().__init__(parent)
        self.localization = localization
        self._clicks = 0
        self._image_loaded = False

        self.setWindowTitle(self.localization.translate("neo_ui.author.title"))
        self.setModal(True)
        self.setAttribute(Qt.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        nickname = self.localization.translate("neo_ui.author.nickname")
        message_text = self.localization.translate("neo_ui.author.message")
        hyperlink = f"<a href='author'>{nickname}</a>"
        message_html = message_text.replace(nickname, hyperlink)

        self.message_label = QLabel(message_html)
        self.message_label.setWordWrap(True)
        self.message_label.setTextFormat(Qt.RichText)
        self.message_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.message_label.setOpenExternalLinks(False)
        self.message_label.linkActivated.connect(self._handle_nickname_click)
        layout.addWidget(self.message_label)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setVisible(False)
        layout.addWidget(self.image_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _handle_nickname_click(self) -> None:
        if self._image_loaded:
            return
        self._clicks += 1
        if self._clicks >= self._TARGET_CLICKS:
            self._show_easter_egg()

    def _show_easter_egg(self) -> None:
        self._image_loaded = True
        image_path = (
            Path(__file__).resolve().parent.parent / "assets" / "images" / "author_easter_egg.webp"
        )
        if image_path.exists():
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(360, 360, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setVisible(True)
        # subtly update the caption to acknowledge the discovery
        self.message_label.setText(
            self.localization.translate("neo_ui.author.message_revealed")
        )

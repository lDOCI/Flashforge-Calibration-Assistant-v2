from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile, QTextStream
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from .palette import Palette


THEME_DIR = Path(__file__).resolve().parent


def apply_theme(app: QApplication, theme: str = "dark") -> None:
    """Load the global stylesheet for the requested theme."""
    _load_fonts()
    if theme not in {"dark", "light"}:
        theme = "dark"
    stylesheet_path = THEME_DIR / f"style_{theme}.qss"
    if not stylesheet_path.exists():
        stylesheet_path = THEME_DIR / "style_dark.qss"
    if stylesheet_path.exists():
        file = QFile(str(stylesheet_path))
        if file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(file)
            stylesheet = stream.readAll()
            app.setStyleSheet(stylesheet)
            file.close()
    app.setProperty("currentTheme", theme)


def _load_fonts() -> None:
    """
    Attempt to load bundled fonts; quietly ignore if unavailable.
    """
    fonts_dir = THEME_DIR / "fonts"
    if not fonts_dir.exists():
        return
    for font_file in fonts_dir.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(font_file))

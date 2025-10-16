from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from flashforge_app.services.localization import LocalizationService
from flashforge_app.services.settings import SettingsService
from flashforge_app.state import AppState
from flashforge_app.ui.main_window import MainWindow
from flashforge_app.ui.theme import apply_theme


class FlashforgeApplication:
    """
    Application bootstrapper responsible for wiring services and UI.
    """

    def __init__(self, argv: Optional[list[str]] = None) -> None:
        self._argv = argv or sys.argv
        self.qt_app = QApplication(self._argv)
        self.settings_service = SettingsService()
        self.localization_service = LocalizationService()
        self.app_state: AppState | None = None
        self.main_window: Optional[MainWindow] = None

    def initialise(self) -> None:
        """
        Prepare services and build the main application window.
        """
        settings = self.settings_service.load()
        if settings.language:
            self.localization_service.set_language(settings.language)

        apply_theme(self.qt_app, settings.theme)

        self.app_state = AppState(self.settings_service)

        self.main_window = MainWindow(
            settings_service=self.settings_service,
            localization_service=self.localization_service,
            app_state=self.app_state,
        )
        self.main_window.resize(1280, 840)
        self._apply_branding()

    def _apply_branding(self) -> None:
        """
        Configure application-wide branding and icons.
        """
        app_icon_path = Path(__file__).resolve().parent / "ui" / "assets" / "icons" / "app.svg"
        if app_icon_path.exists():
            icon = QIcon(str(app_icon_path))
            self.qt_app.setWindowIcon(icon)
            if self.main_window:
                self.main_window.setWindowIcon(icon)

        self.qt_app.setApplicationName("Flashforge Calibration Assistant")
        self.qt_app.setApplicationDisplayName("Flashforge Calibration Assistant")

    def run(self) -> int:
        """
        Start the Qt event loop.
        """
        if self.main_window is None:
            self.initialise()

        assert self.main_window is not None
        self.main_window.show()
        return self.qt_app.exec()


def create_app(argv: Optional[list[str]] = None) -> FlashforgeApplication:
    """
    Factory for the flashforge application.
    """
    app = FlashforgeApplication(argv)
    app.initialise()
    return app

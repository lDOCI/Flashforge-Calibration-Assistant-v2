from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from flashforge_app.services.localization import LocalizationService
from flashforge_app.services.settings import SettingsService
from flashforge_app.state import AppState, BedWorkspace
from flashforge_app.ui.dialogs import AuthorDialog, VisualRecommendationsDialog
from flashforge_app.ui.views.input_shaper import InputShaperView
from flashforge_app.ui.views.leveling import BedLevelingView
from flashforge_app.ui.views.settings import SettingsView
from flashforge_app.ui.views.ssh_tab import SSHTab
from flashforge_app.ui.widgets import AnimatedStackedWidget, SideMenu, TopBar
from flashforge_app.ui.theme import apply_theme


class MainWindow(QMainWindow):
    """Main window combining navigation, top bar, and functional views."""

    def __init__(
        self,
        *,
        settings_service: SettingsService,
        localization_service: LocalizationService,
        app_state: AppState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings_service = settings_service
        self.localization = localization_service
        self.app_state = app_state

        self.setWindowTitle("Flashforge Calibration Assistant")
        self.setAcceptDrops(True)

        self._stack = AnimatedStackedWidget()
        self._navigation = SideMenu()
        self._views: Dict[str, QWidget] = {}

        self.bed_view = BedLevelingView(self.localization, self.app_state, self)
        self.shaper_view = InputShaperView(self.localization, self.app_state, self)
        self.settings_view = SettingsView(self.settings_service, self.localization, self.app_state, self)
        self.ssh_view = SSHTab(self.localization, self.app_state, self)

        self._build_ui()
        self._populate_views()
        self._connect_signals()
        self._apply_translations()
        self._restore_last_file()

    # ------------------------------------------------------------------ UI construction
    def _build_ui(self) -> None:
        container = QWidget()
        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(14)
        container.setLayout(root_layout)

        sidebar = self._build_sidebar()
        sidebar.setFixedWidth(220)
        root_layout.addWidget(sidebar)

        content_container = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        content_container.setLayout(content_layout)

        self._top_bar = TopBar()
        content_layout.addWidget(self._top_bar)

        scroll_area = QScrollArea()
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_layout.setContentsMargins(4, 4, 4, 32)
        scroll_layout.setSpacing(12)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll_content.setLayout(scroll_layout)

        self._stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        scroll_layout.addWidget(self._stack)

        scroll_area.setWidget(scroll_content)
        content_layout.addWidget(scroll_area, 1)

        root_layout.addWidget(content_container, 1)
        self.setCentralWidget(container)

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        sidebar.setLayout(layout)

        header = self._build_sidebar_header()
        layout.addWidget(header)
        layout.addWidget(self._navigation, 1)
        return sidebar

    def _build_sidebar_header(self) -> QWidget:
        wrapper = QFrame()
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        wrapper.setLayout(layout)

        icon_label = QFrame()
        icon_label.setFixedSize(40, 40)
        icon_label.setStyleSheet(
            "background-color: rgba(92, 107, 245, 0.15);"
            "border-radius: 12px;"
            f"background-image: url('{self._icon_path('app.svg').as_posix()}');"
            "background-position: center;"
            "background-repeat: no-repeat;"
        )
        layout.addWidget(icon_label)

        text_container = QWidget()
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_container.setLayout(text_layout)
        self.sidebar_title = QLabel("Flashforge")
        self.sidebar_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.sidebar_caption = QLabel("Calibration Suite")
        self.sidebar_caption.setObjectName("Subtitle")
        text_layout.addWidget(self.sidebar_title)
        text_layout.addWidget(self.sidebar_caption)
        layout.addWidget(text_container)
        layout.addStretch(1)
        return wrapper

    # ------------------------------------------------------------------ view population
    def _populate_views(self) -> None:
        self._views = {
            "bed": self.bed_view,
            "shaper": self.shaper_view,
            "ssh": self.ssh_view,
            "settings": self.settings_view,
        }
        for view in self._views.values():
            self._stack.addWidget(view)

        self._navigation.add_entry("bed", "Bed Leveling", self._icon_path("bed.svg"))
        self._navigation.add_entry("shaper", "Input Shaper", self._icon_path("shaper.svg"))
        self._navigation.add_entry("ssh", "SSH", self._icon_path("settings.svg"))
        self._navigation.add_entry("settings", "Settings", self._icon_path("settings.svg"))
        self._navigation.set_current("bed")
        self._stack.setCurrentWidget(self.bed_view)

    def _connect_signals(self) -> None:
        self._navigation.activated.connect(self._switch_view)
        self._top_bar.theme_toggle_requested.connect(self._toggle_theme)
        self._top_bar.language_selected.connect(self._change_language)
        self._top_bar.author_button_clicked.connect(self._show_author_dialog)
        self.bed_view.load_printer_requested.connect(self._trigger_load_printer)
        self.bed_view.visual_recommendations_requested.connect(self._show_visual_recommendations)
        self.shaper_view.csv_loaded.connect(self._on_shaper_csv_loaded)
        self.ssh_view.config_downloaded.connect(self._on_config_downloaded)
        self.ssh_view.shaper_files_downloaded.connect(self._on_shaper_files_downloaded)

    # ------------------------------------------------------------------ translations
    def _apply_translations(self) -> None:
        tr = self.localization.translate
        self.sidebar_title.setText(tr("neo_ui.sidebar.title"))
        self.sidebar_caption.setText(tr("neo_ui.sidebar.caption"))

        self._navigation.set_label("bed", tr("neo_ui.nav.bed"))
        self._navigation.set_label("shaper", tr("neo_ui.nav.shaper"))
        self._navigation.set_label("ssh", tr("neo_ui.nav.ssh"))
        self._navigation.set_label("settings", tr("neo_ui.nav.settings"))

        self.bed_view.apply_translations()
        self.shaper_view.apply_translations()
        self.ssh_view.apply_translations()
        self.settings_view.apply_translations()

        self._top_bar.apply_translations(
            title=tr("neo_ui.top_bar.title"),
            theme_hint=tr("neo_ui.top_bar.theme"),
            language_hint=tr("neo_ui.top_bar.language"),
            author_label=tr("neo_ui.top_bar.author"),
        )
        self._top_bar.set_languages(self.localization.available_languages(), self.localization.current_language)
        self._top_bar.set_status(tr("neo_ui.top_bar.status.ready"))
        self._top_bar.set_theme_icon(self.app_state.current_settings.theme)

    # ------------------------------------------------------------------ navigation + data
    def _switch_view(self, key: str) -> None:
        widget = self._views.get(key)
        if not widget:
            return
        self._stack.setCurrentWidget(widget)
        if hasattr(widget, "on_view_activated"):
            widget.on_view_activated()

    def _trigger_load_printer(self) -> None:
        tr = self.localization.translate
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("neo_ui.dialogs.open_printer"),
            str(Path.home()),
            "Klipper Config (*.cfg *.conf);;All Files (*)",
        )
        if not file_path:
            return
        self._load_printer_file(Path(file_path), notify=True)

    def _load_printer_file(self, path: Path, notify: bool) -> None:
        tr = self.localization.translate
        try:
            workspace = self.app_state.load_printer_config(path)
        except Exception:  # noqa: BLE001
            QMessageBox.critical(self, tr("neo_ui.common.error"), tr("neo_ui.errors.load_failed"))
            self._top_bar.set_status(tr("neo_ui.top_bar.status.error"))
            return

        self.bed_view.set_workspace(workspace)
        self._top_bar.set_status(tr("neo_ui.top_bar.status.loaded").format(file=path.name))
        if notify:
            QMessageBox.information(self, tr("neo_ui.common.success"), tr("neo_ui.dialogs.load_success"))

    def _restore_last_file(self) -> None:
        last_file = self.app_state.current_settings.last_file
        if last_file:
            path = Path(last_file)
            if path.exists():
                self._load_printer_file(path, notify=False)

    def _show_visual_recommendations(self) -> None:
        workspace = self.app_state.workspace
        if not workspace or not workspace.workflow:
            workflow = self.app_state.recompute_workflow()
        else:
            workflow = workspace.workflow

        if not workflow:
            QMessageBox.warning(
                self,
                self.localization.translate("neo_ui.common.warning"),
                self.localization.translate("neo_ui.bed.recommendations.placeholder"),
            )
            return

        dialog = VisualRecommendationsDialog(
            self.localization,
            workflow,
            self.app_state.current_settings,
            self.app_state.current_settings.theme,
            self,
        )
        dialog.exec()

    def _show_author_dialog(self) -> None:
        dialog = AuthorDialog(self.localization, self)
        dialog.exec()

    # ------------------------------------------------------------------ language & theme
    def _change_language(self, language_code: str) -> None:
        if not self.localization.set_language(language_code):
            return
        self.app_state.current_settings.language = language_code
        self.settings_service.save()
        self._apply_translations()

    def _toggle_theme(self) -> None:
        current = self.app_state.current_settings.theme
        new_theme = "light" if current == "dark" else "dark"
        self.app_state.current_settings.theme = new_theme
        self.settings_service.save()
        apply_theme(QApplication.instance(), new_theme)
        self._top_bar.set_theme_icon(new_theme)
        self.bed_view.on_theme_changed()
        self.shaper_view.on_theme_changed()
        self.settings_view.apply_translations()
        self.ssh_view.apply_translations()

    # ------------------------------------------------------------------ helpers
    def _icon_path(self, icon: str) -> Path:
        return Path(__file__).resolve().parent / "assets" / "icons" / icon

    def _on_shaper_csv_loaded(self, path: Path) -> None:
        self._top_bar.set_status(
            self.localization.translate("neo_ui.shaper.status.loaded").format(file=path.name)
        )

    def _on_config_downloaded(self, path: Path) -> None:
        self._top_bar.set_status(
            self.localization.translate("neo_ui.top_bar.status.loaded").format(file=path.name)
        )
        if self.app_state.workspace:
            self.bed_view.set_workspace(self.app_state.workspace)

    def _on_shaper_files_downloaded(self, files: list[Path]) -> None:
        ordered: list[Path] = []
        for axis in ('x', 'y'):
            ordered.extend([f for f in files if self.shaper_view._infer_axis_from_filename(f) == axis])
        ordered.extend([f for f in files if f not in ordered])

        for file in ordered:
            axis_hint = self.shaper_view._infer_axis_from_filename(file)
            self.shaper_view.load_csv_file(file, axis_hint=axis_hint)

    # ------------------------------------------------------------------ drag and drop support
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return

        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        handled = False
        for path in paths:
            if path.suffix.lower() in {".cfg", ".conf"}:
                self._load_printer_file(path, notify=True)
                handled = True
            elif path.suffix.lower() == ".csv":
                if self.shaper_view.load_csv_file(path):
                    self._top_bar.set_status(
                        self.localization.translate("neo_ui.shaper.status.loaded").format(file=path.name)
                    )
                    handled = True

        if not handled:
            QMessageBox.warning(
                self,
                self.localization.translate("neo_ui.common.warning"),
                self.localization.translate("neo_ui.dialogs.drop_unsupported"),
            )
        event.acceptProposedAction()

    QDragEnterEvent,
    QDropEvent,
    QMessageBox,

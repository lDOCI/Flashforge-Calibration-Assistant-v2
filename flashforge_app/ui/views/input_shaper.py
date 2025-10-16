from __future__ import annotations

from pathlib import Path
import html
import sys
from typing import Dict, List, Optional
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2].parent
BASE_ANALYSIS = PROJECT_ROOT / "input_shaper" / "analysis"
if str(BASE_ANALYSIS) not in sys.path:
    sys.path.append(str(BASE_ANALYSIS))
if str(BASE_ANALYSIS / "extras") not in sys.path:
    sys.path.append(str(BASE_ANALYSIS / "extras"))

import calibrate_shaper  # type: ignore  # noqa: E402
import shaper_calibrate  # type: ignore  # noqa: E402

from flashforge_app.services.localization import LocalizationService
from flashforge_app.state import AppState


class _AxisPlot(QFrame):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.canvas: FigureCanvasQTAgg | None = None
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        self.setLayout(layout)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(self.title_label)

        self.placeholder = QLabel("—")
        self.placeholder.setObjectName("Subtitle")
        self.placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.placeholder, 1)

    def render(self, figure: Figure) -> None:
        if self.canvas:
            self.layout().removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()
        self.canvas = FigureCanvasQTAgg(figure)
        self.canvas.setStyleSheet("background: transparent;")
        self.canvas.setMinimumHeight(320)
        self.layout().addWidget(self.canvas)
        self.placeholder.hide()

    def clear(self, placeholder: str) -> None:
        if self.canvas:
            self.layout().removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()
            self.canvas = None
        self.placeholder.setText(placeholder)
        self.placeholder.show()


class _AxisInfo(QFrame):
    def __init__(
        self,
        axis_key: str,
        title: str,
        on_select,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.axis_key = axis_key
        self.on_select = on_select
        self.setObjectName("Card")
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        self.setLayout(layout)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        layout.addWidget(self.title_label)

        self.recommend_label = QLabel("—")
        self.recommend_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.recommend_label)

        self.lines_container = QVBoxLayout()
        self.lines_container.setSpacing(4)
        layout.addLayout(self.lines_container)
        self.lines_container.setAlignment(Qt.AlignTop)

        self.buttons_container = QHBoxLayout()
        self.buttons_container.setSpacing(6)
        layout.addLayout(self.buttons_container)

        self._line_labels: list[QLabel] = []
        self._buttons: list[QPushButton] = []

    def _make_click_handler(self, name: str, freq: float):
        def handler(checked: bool = False) -> None:  # noqa: ARG001
            self.on_select(self.axis_key, name.upper(), freq)
        return handler

    def update_info(self, recommended_text: str, entries: list[dict]) -> None:
        self.recommend_label.setText(recommended_text)
        for label in self._line_labels:
            self.lines_container.removeWidget(label)
            label.deleteLater()
        for button in self._buttons:
            self.buttons_container.removeWidget(button)
            button.deleteLater()
        self._line_labels = []
        self._buttons = []

        while self.lines_container.count():
            item = self.lines_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        while self.buttons_container.count():
            item = self.buttons_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._line_labels = []
        self._buttons = []

        for entry in entries:
            bullet = f"<span style='color:{entry['color']}; font-size:16px;'>●</span> "
            safe_text = html.escape(entry['text'])
            text = bullet + safe_text
            label = QLabel(text)
            label.setTextFormat(Qt.RichText)
            label.setWordWrap(True)
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            if entry.get('selected'):
                label.setStyleSheet("font-weight: 600;")
            self.lines_container.addWidget(label)
            self._line_labels.append(label)

            button = QPushButton(entry['name'].upper())
            button.setCursor(Qt.PointingHandCursor)
            if entry.get('selected'):
                button.setStyleSheet(
                    f"border-radius: 12px; padding:4px 10px; border:1px solid {entry['color']}; "
                    f"background:{entry['color']}; color:#FFFFFF;"
                )
            else:
                button.setStyleSheet(
                    f"border-radius: 12px; padding:4px 10px; border:1px solid {entry['color']}; "
                    f"color:{entry['color']}; background: transparent;"
                )
            button.clicked.connect(self._make_click_handler(entry['name'], entry['freq']))
            self.buttons_container.addWidget(button)
            self._buttons.append(button)

        self.buttons_container.addStretch(1)

    def clear(self, placeholder: str) -> None:
        self.recommend_label.setText(placeholder)
        while self.lines_container.count():
            item = self.lines_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        while self.buttons_container.count():
            item = self.buttons_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._line_labels = []
        self._buttons = []


class InputShaperView(QWidget):
    """PySide6 implementation of the legacy Input Shaper layout."""

    csv_loaded = Signal(Path)

    def __init__(
        self,
        localization: LocalizationService,
        app_state: AppState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.localization = localization
        self.app_state = app_state

        self._results: Dict[str, tuple[str, float]] = {}
        self._calibration_data: Dict[str, shaper_calibrate.CalibrationData] = {}
        self._shaper_lists: Dict[str, List] = {}
        self._shaper_objects: Dict[str, List] = {}
        self._palette = ["#5C6BF5", "#42C29E", "#FF6EA1", "#FFB347", "#8E44AD", "#2ECC71"]

        root = QVBoxLayout()
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignTop)
        self.setLayout(root)

        self.header_label = QLabel()
        self.header_label.setStyleSheet("font-size: 20px; font-weight: 600;")
        root.addWidget(self.header_label)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        root.addLayout(content_layout, stretch=1)

        # Left panel -----------------------------------------------------
        left_panel = QFrame()
        left_panel.setObjectName("Card")
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(12)
        left_panel.setLayout(left_layout)
        content_layout.addWidget(left_panel, stretch=1)

        self.load_x_button = QPushButton()
        self.load_x_button.clicked.connect(lambda: self._trigger_load_dialog('x'))
        self.load_y_button = QPushButton()
        self.load_y_button.clicked.connect(lambda: self._trigger_load_dialog('y'))
        self.help_button = QPushButton()
        self.help_button.clicked.connect(self._show_help)
        self.copy_button = QPushButton()
        self.copy_button.clicked.connect(self._copy_config)

        left_layout.addWidget(self.load_x_button)
        left_layout.addWidget(self.load_y_button)
        left_layout.addWidget(self.help_button)
        left_layout.addWidget(self.copy_button)

        self.status_label = QLabel()
        self.status_label.setObjectName("Subtitle")
        left_layout.addWidget(self.status_label)

        self.axis_info: Dict[str, _AxisInfo] = {
            'x': _AxisInfo('x', "Axis X", self._on_shaper_selected, self),
            'y': _AxisInfo('y', "Axis Y", self._on_shaper_selected, self),
        }
        left_layout.addWidget(self.axis_info['x'])
        left_layout.addWidget(self.axis_info['y'])

        self.summary_card = QFrame()
        self.summary_card.setObjectName("Card")
        summary_layout = QVBoxLayout()
        summary_layout.setContentsMargins(16, 16, 16, 16)
        summary_layout.setSpacing(8)
        self.summary_card.setLayout(summary_layout)
        self.summary_label = QLabel("—")
        self.summary_label.setObjectName("Subtitle")
        summary_layout.addWidget(self.summary_label)
        left_layout.addWidget(self.summary_card)
        left_layout.addStretch(1)

        # Right panel ----------------------------------------------------
        right_panel = QGridLayout()
        right_panel.setContentsMargins(0, 0, 0, 0)
        right_panel.setHorizontalSpacing(12)
        right_panel.setVerticalSpacing(12)
        right_container = QWidget()
        right_container.setLayout(right_panel)
        content_layout.addWidget(right_container, stretch=2)

        self.axis_plots = {
            'x': _AxisPlot("Axis X", self),
            'y': _AxisPlot("Axis Y", self),
        }
        right_panel.addWidget(self.axis_plots['x'], 0, 0)
        right_panel.addWidget(self.axis_plots['y'], 1, 0)

        root.addStretch(1)

        self.apply_translations()
        self._refresh_placeholders()

    # ------------------------------------------------------------------ translations/theme
    def apply_translations(self) -> None:
        tr = self.localization.translate
        self.header_label.setText(tr("neo_ui.shaper.header"))
        self.load_x_button.setText(tr("shaper_tab.load_x"))
        self.load_y_button.setText(tr("shaper_tab.load_y"))
        self.help_button.setText(tr("shaper_tab.what_is_it"))
        self.copy_button.setText(tr("shaper_tab.copy_klipper"))
        self.axis_info['x'].title_label.setText(tr("shaper_tab.axis_x"))
        self.axis_info['y'].title_label.setText(tr("shaper_tab.axis_y"))
        if not self._results:
            self.summary_label.setText(tr("neo_ui.shaper.result_placeholder"))
            self.axis_info['x'].clear(tr("neo_ui.shaper.no_file"))
            self.axis_info['y'].clear(tr("neo_ui.shaper.no_file"))
        theme = self.app_state.current_settings.theme
        if theme == 'dark':
            text_color = '#F7F9FF'
        else:
            text_color = '#1C1E24'
        self.status_label.setStyleSheet(f"color: {text_color}")
        for axis in ('x', 'y'):
            entries = self._shaper_lists.get(axis)
            if entries:
                selected = self._results.get(axis)
                if selected:
                    shaper_name, freq = selected
                else:
                    shaper_name, freq = entries[0]['name'].upper(), entries[0]['freq']
                    self._results[axis] = (shaper_name, freq)
                axis_title = tr("shaper_tab.axis_x") if axis == 'x' else tr("shaper_tab.axis_y")
                for entry in entries:
                    entry['selected'] = entry['name'].upper() == shaper_name
                self.axis_info[axis].update_info(
                    tr("neo_ui.shaper.recommend_line").format(axis=axis_title, shaper=shaper_name, freq=freq),
                    entries,
                )
        self._update_summary()

    def on_theme_changed(self) -> None:
        self.apply_translations()
        for axis in ('x', 'y'):
            if axis in self._calibration_data and axis in self._shaper_objects:
                self._plot_axis(axis, self._calibration_data[axis], self._shaper_objects[axis], self._results.get(axis))
            else:
                placeholder = self.localization.translate("shaper_tab.no_data_x" if axis == 'x' else "shaper_tab.no_data_y")
                self.axis_plots[axis].clear(placeholder)

    def _refresh_placeholders(self) -> None:
        tr = self.localization.translate
        self.axis_plots['x'].clear(tr("shaper_tab.no_data_x"))
        self.axis_plots['y'].clear(tr("shaper_tab.no_data_y"))
        self.axis_info['x'].clear(tr("neo_ui.shaper.no_file"))
        self.axis_info['y'].clear(tr("neo_ui.shaper.no_file"))
        self.summary_label.setText(tr("neo_ui.shaper.result_placeholder"))

    # ------------------------------------------------------------------ UI actions
    def _trigger_load_dialog(self, axis: str | None = None) -> None:
        tr = self.localization.translate
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("neo_ui.shaper.dialog"),
            str(Path.home()),
            "CSV (*.csv);;All Files (*)",
        )
        if not file_path:
            return
        self.load_csv_file(Path(file_path), axis_hint=axis)

    def _show_help(self) -> None:
        QMessageBox.information(self, self.localization.translate("neo_ui.common.information"), self.localization.translate("shaper_tab.help_text"))

    # ------------------------------------------------------------------ data handling
    def load_csv_file(self, path: Path, axis_hint: Optional[str] = None) -> bool:
        tr = self.localization.translate
        try:
            raw_data = calibrate_shaper.parse_log(str(path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, tr("Warning"), tr("shaper_tab.error_loading").format(str(exc)))
            return False

        axis = axis_hint or self._infer_axis_from_filename(path)
        if axis not in {'x', 'y'}:
            axis = 'x' if 'x' not in self._calibration_data else 'y'

        result = self._analyze_axis(axis, raw_data)
        if result:
            shaper, freq, calibration_data, entries = result
            self._results[axis] = (shaper, freq)
            self._calibration_data[axis] = calibration_data
            self._shaper_lists[axis] = entries
            axis_title = self.localization.translate("shaper_tab.axis_x") if axis == 'x' else self.localization.translate("shaper_tab.axis_y")
            for entry in entries:
                entry['selected'] = entry['name'].upper() == shaper
            self.axis_info[axis].update_info(
                self.localization.translate("neo_ui.shaper.recommend_line").format(axis=axis_title, shaper=shaper, freq=freq),
                entries,
            )
            self._update_summary()
            self.status_label.setText(tr("neo_ui.shaper.status.loaded").format(file=path.name))
            self.csv_loaded.emit(path)
            return True
        return False

    def _infer_axis_from_filename(self, path: Path) -> Optional[str]:
        name = path.name.lower()
        if 'axis_x' in name or '_x' in name or '-x' in name:
            return 'x'
        if 'axis_y' in name or '_y' in name or '-y' in name:
            return 'y'
        return None

    def _analyze_axis(self, axis: str, data) -> Optional[tuple[str, float, shaper_calibrate.CalibrationData, List[dict]]]:
        try:
            if not isinstance(data, shaper_calibrate.CalibrationData):
                data = shaper_calibrate.ShaperCalibrate(None).process_accelerometer_data(data)

            selected, shapers, calibration_data = calibrate_shaper.calibrate_shaper([data], csv_output=None, max_smoothing=None)
            entries = self._format_shaper_list(shapers)
            freq = next((s.freq for s in shapers if s.name == selected), 0.0)
            for entry in entries:
                entry['selected'] = entry['name'].upper() == selected.upper()
            self._shaper_objects[axis] = shapers
            self._plot_axis(axis, calibration_data, shapers, (selected.upper(), freq))
            return selected.upper(), freq, calibration_data, entries
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(self.localization.translate("neo_ui.shaper.error") + f" ({exc})")
            return None

    def _plot_axis(self, axis: str, calibration_data: shaper_calibrate.CalibrationData, shapers: List, result: Optional[tuple[str, float]]) -> None:
        figure = calibrate_shaper.plot_freq_response([axis.upper()], calibration_data, shapers, result[0].lower() if result else None, 200.0)
        self._style_plot(figure)
        placeholder = self.localization.translate("shaper_tab.no_data_x" if axis == 'x' else "shaper_tab.no_data_y")
        self.axis_plots[axis].render(figure)
        self.axis_plots[axis].title_label.setText(
            (self.localization.translate("shaper_tab.axis_x") if axis == 'x' else self.localization.translate("shaper_tab.axis_y"))
            + (f" — {result[0]}@{result[1]:.1f} Hz" if result else "")
        )
        if axis not in self._results:
            self.axis_plots[axis].placeholder.setText(placeholder)

    def _style_plot(self, fig: Figure) -> None:
        is_dark = self.app_state.current_settings.theme == 'dark'
        text_color = '#F7F9FF' if is_dark else '#1C1E24'
        bg_color = '#1E1E1E' if is_dark else '#FFFFFF'
        major_grid = '#666666' if is_dark else '#C0C0C0'
        minor_grid = '#444444' if is_dark else '#E0E0E0'

        fig.patch.set_facecolor(bg_color)
        for ax in fig.axes:
            ax.set_facecolor(bg_color)
            ax.tick_params(colors=text_color)
            ax.xaxis.label.set_color(text_color)
            ax.yaxis.label.set_color(text_color)
            for spine in ax.spines.values():
                spine.set_color(text_color if is_dark else '#888888')
            ax.title.set_color(text_color)
            ax.grid(True, which='major', linestyle='--', color=major_grid, alpha=0.6)
            ax.grid(True, which='minor', linestyle=':', color=minor_grid, alpha=0.4)
            legend = ax.get_legend()
            if legend:
                legend.get_frame().set_alpha(0.0)
                for text in legend.get_texts():
                    text.set_color(text_color)
        fig.tight_layout()

    def _format_shaper_list(self, shapers: List) -> List[str]:
        lines: List[dict] = []
        for idx, sh in enumerate(shapers):
            freq = getattr(sh, 'freq', 0.0)
            vibr = getattr(sh, 'vibrs', 0.0) * 100.0
            smoothing = getattr(sh, 'smoothing', 0.0)
            accel = getattr(sh, 'max_accel', 0.0)
            line = f"{sh.name.upper()} ({freq:.1f} Hz, vibr={vibr:.1f}%, sm~={smoothing:.2f}, accel<={round(accel/100.)*100:.0f})"
            lines.append({
                'name': sh.name.upper(),
                'freq': freq,
                'text': line,
                'color': self._palette[idx % len(self._palette)],
                'selected': False,
            })
        return lines

    # ------------------------------------------------------------------ clipboard
    def _copy_config(self) -> None:
        tr = self.localization.translate
        if not self._results:
            QMessageBox.warning(self, tr("Warning"), tr("shaper_tab.perform_analysis_first"))
            return
        x_type, x_freq = self._results.get('x', ('mzv', 45.0))
        y_type, y_freq = self._results.get('y', ('mzv', 45.0))
        config_lines = [
            "#*# [input_shaper]",
            f"#*# shaper_type_x = {x_type.lower()}",
            f"#*# shaper_freq_x = {x_freq:.1f}",
            f"#*# shaper_type_y = {y_type.lower()}",
            f"#*# shaper_freq_y = {y_freq:.1f}",
        ]
        config = "\n".join(config_lines) + "\n"
        QApplication.clipboard().setText(config)
        self.status_label.setText(tr("shaper_tab.copied"))

    def _on_shaper_selected(self, axis: str, shaper: str, freq: float) -> None:
        entries = self._shaper_lists.get(axis)
        if not entries:
            return
        tr = self.localization.translate
        for entry in entries:
            entry['selected'] = entry['name'].upper() == shaper
        axis_title = tr("shaper_tab.axis_x") if axis == 'x' else tr("shaper_tab.axis_y")
        self._results[axis] = (shaper, freq)
        self.axis_info[axis].update_info(
            tr("neo_ui.shaper.recommend_line").format(axis=axis_title, shaper=shaper, freq=freq),
            entries,
        )
        if axis in self._calibration_data and axis in self._shaper_objects:
            self._plot_axis(axis, self._calibration_data[axis], self._shaper_objects[axis], (shaper, freq))
        self._update_summary()

    def _update_summary(self) -> None:
        tr = self.localization.translate
        if not self._results:
            self.summary_label.setText(tr("neo_ui.shaper.result_placeholder"))
            return
        summary_lines = [
            tr("neo_ui.shaper.summary_line").format(
                axis=tr("shaper_tab.axis_x" if axis == 'x' else "shaper_tab.axis_y"),
                shaper=info[0],
                freq=info[1],
            )
            for axis, info in self._results.items()
        ]
        self.summary_label.setText("\n".join(summary_lines))

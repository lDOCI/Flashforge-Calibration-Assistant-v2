from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from flashforge_app.services.localization import LocalizationService
from flashforge_app.state import AppState, BedWorkspace
from flashforge_app.ui.widgets import CardWidget
from visualization.bed_mesh.heatmap_2d import BedMeshHeatmap
from visualization.bed_mesh.surface_3d import BedMesh3D


class BedLevelingView(QWidget):
    """Workspace responsible for bed mesh analysis and recommendations."""

    load_printer_requested = Signal()
    visual_recommendations_requested = Signal()

    def __init__(
        self,
        localization: LocalizationService,
        app_state: AppState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.localization = localization
        self.app_state = app_state
        self.workspace: Optional[BedWorkspace] = None
        self.heatmap_canvas: Optional[FigureCanvasQTAgg] = None
        self.surface_canvas: Optional[FigureCanvasQTAgg] = None
        self._heatmap = BedMeshHeatmap()
        self._surface = BedMesh3D()
        self._heatmap.set_translator(self.localization.translate)
        self._surface.set_translator(self.localization.translate)
        self._fig_width_inches = 5.6
        self._fig_height_inches = 3.8
        self._fig_pixel_height = int(self._fig_height_inches * 100)
        self._last_render_size: tuple[int, int] = (0, 0)
        self._render_lock = False

        self._build_ui()
        self.apply_translations()
        self._update_visual_controls()

    # ------------------------------------------------------------------ UI construction
    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 0, 8, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignTop)
        self.setLayout(layout)

        self.load_button = QPushButton()
        self.load_button.setCursor(Qt.PointingHandCursor)
        self.load_button.clicked.connect(self.load_printer_requested.emit)

        self.visual_button = QPushButton()
        self.visual_button.setCursor(Qt.PointingHandCursor)
        self.visual_button.clicked.connect(self.visual_recommendations_requested.emit)
        self.visual_button.setVisible(False)

        meta_container = QWidget()
        meta_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        meta_layout = QVBoxLayout()
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(6)
        meta_layout.setAlignment(Qt.AlignTop)
        meta_container.setLayout(meta_layout)
        layout.addWidget(meta_container, 0, Qt.AlignTop)

        self.summary_cards_container = QWidget()
        summary_layout = QHBoxLayout()
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(8)
        summary_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.summary_cards_container.setLayout(summary_layout)
        meta_layout.addWidget(self.summary_cards_container)

        self.card_delta = CardWidget("-", "0.000 mm", compact=True)
        self.card_average = CardWidget("-", "0.000 mm", compact=True)
        self.card_status = CardWidget("-", "-", compact=True)
        for card in (self.card_delta, self.card_average, self.card_status):
            card.setMaximumWidth(200)
            card.setFixedHeight(84)
            summary_layout.addWidget(card)

        self.recommendations_frame = QFrame()
        self.recommendations_frame.setObjectName("Card")
        self.recommendations_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.recommendations_frame.setMaximumWidth(240)
        self.recommendations_frame.setFixedHeight(92)
        rec_layout = QVBoxLayout()
        rec_layout.setContentsMargins(16, 12, 16, 12)
        rec_layout.setSpacing(6)
        self.recommendations_frame.setLayout(rec_layout)
        self.recommendations_title = QLabel()
        self.recommendations_title.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.recommendations_body = QLabel()
        self.recommendations_body.setObjectName("Subtitle")
        self.recommendations_body.setWordWrap(True)
        self.recommendations_body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.recommendations_body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        rec_layout.addWidget(self.recommendations_title)
        rec_layout.addWidget(self.recommendations_body, 1)
        summary_layout.addWidget(self.recommendations_frame, 2)
        summary_layout.addStretch(1)

        controls_frame = QFrame()
        controls_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(6)
        controls_frame.setLayout(controls_layout)
        meta_layout.addWidget(controls_frame)
        meta_layout.addSpacing(30)

        self.visual_button_cta = QPushButton()
        self.visual_button_cta.setCursor(Qt.PointingHandCursor)
        self.visual_button_cta.setObjectName("PrimaryActionButton")
        self.visual_button_cta.clicked.connect(self.visual_recommendations_requested.emit)
        self.export_png_button = QPushButton("Export PNG")
        self.last_file_label: Optional[QLabel] = None

        button_bar = QHBoxLayout()
        button_bar.setContentsMargins(0, 0, 0, 0)
        button_bar.setSpacing(8)
        button_bar.addWidget(self.load_button)
        button_bar.addWidget(self.visual_button_cta)
        button_bar.addWidget(self.export_png_button)

        controls_layout.addLayout(button_bar)

        self.figure_frame = QFrame()
        self.figure_frame.setObjectName("Card")
        self.figure_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        figure_layout = QGridLayout()
        figure_layout.setContentsMargins(0, 0, 0, 0)
        figure_layout.setHorizontalSpacing(10)
        figure_layout.setVerticalSpacing(0)
        self.figure_frame.setLayout(figure_layout)
        layout.addWidget(self.figure_frame, 0, Qt.AlignTop)
        self.figure_grid = figure_layout

        self.heatmap_holder = QWidget()
        self.heatmap_holder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        heatmap_layout = QVBoxLayout()
        heatmap_layout.setContentsMargins(0, 0, 0, 0)
        heatmap_layout.setSpacing(0)
        heatmap_layout.setAlignment(Qt.AlignTop)
        self.heatmap_holder.setLayout(heatmap_layout)

        self.heatmap_placeholder = QLabel()
        self.heatmap_placeholder.setAlignment(Qt.AlignCenter)
        self.heatmap_placeholder.setObjectName("Subtitle")
        heatmap_layout.addWidget(self.heatmap_placeholder)

        self.surface_holder = QWidget()
        self.surface_holder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        surface_layout = QVBoxLayout()
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)
        surface_layout.setAlignment(Qt.AlignTop)
        self.surface_holder.setLayout(surface_layout)

        self.surface_placeholder = QLabel()
        self.surface_placeholder.setAlignment(Qt.AlignCenter)
        self.surface_placeholder.setObjectName("Subtitle")
        surface_layout.addWidget(self.surface_placeholder)

        figure_layout.addWidget(self.heatmap_holder, 0, 0)
        figure_layout.addWidget(self.surface_holder, 0, 1)
        figure_layout.setColumnStretch(0, 1)
        figure_layout.setColumnStretch(1, 1)
        figure_layout.setRowStretch(0, 1)

        self.export_png_button.clicked.connect(lambda: self._export_current_figure("png"))

    # ------------------------------------------------------------------ translation
    def apply_translations(self) -> None:
        tr = self.localization.translate
        self._heatmap.set_translator(tr)
        self._surface.set_translator(tr)
        self.load_button.setText(tr("neo_ui.bed.actions.load"))
        self.card_delta.set_title(tr("neo_ui.bed.cards.max_delta"))
        self.card_average.set_title(tr("neo_ui.bed.cards.average"))
        self.card_status.set_title(tr("neo_ui.bed.cards.status"))
        self.visual_button_cta.setText(tr("neo_ui.bed.actions.visual_cta"))
        self.export_png_button.setText(tr("neo_ui.bed.export.png"))
        self.heatmap_placeholder.setText(tr("neo_ui.bed.no_data"))
        self.surface_placeholder.setText(tr("neo_ui.bed.no_data"))
        self.recommendations_title.setText(tr("neo_ui.bed.recommendations.title"))
        self._update_recommendations()
        self._refresh_cards()

        if self.workspace:
            self._render_visualizations()
            if self.app_state.last_printer_cfg:
                self._update_last_file_label(self.app_state.last_printer_cfg)
        else:
            self._update_last_file_label(None)

    def on_theme_changed(self) -> None:
        self.apply_translations()

    # ------------------------------------------------------------------ workspace updates
    def set_workspace(self, workspace: BedWorkspace) -> None:
        self.workspace = workspace
        self._refresh_cards()
        self._update_recommendations()
        self._render_visualizations()
        self._update_visual_controls()
        self._update_last_file_label(self.app_state.last_printer_cfg)

    def clear_workspace(self) -> None:
        self.workspace = None
        self._refresh_cards()
        self._update_recommendations()
        self._update_visual_controls()
        self._remove_canvas()
        self.heatmap_placeholder.show()
        self.surface_placeholder.show()
        self._update_last_file_label(None)

    # ------------------------------------------------------------------ UI helpers
    def _refresh_cards(self) -> None:
        tr = self.localization.translate
        unit_mm = tr("neo_ui.units.mm", "mm")
        if not self.workspace or self.workspace.bed.mesh_data is None:
            self.card_status.reset_value_font()
            zero_value = f"{0.0:.3f} {unit_mm}"
            self.card_delta.set_value(zero_value)
            self.card_average.set_value(zero_value)
            self.card_status.set_value(tr("neo_ui.bed.status.waiting"))
            self.card_status.set_subtitle(tr("neo_ui.bed.status.load_hint"))
            return

        matrix = self.workspace.mesh_matrix
        max_delta = float(np.max(matrix) - np.min(matrix))
        average = float(np.mean(matrix))
        self.card_delta.set_value(f"{max_delta:.3f} {unit_mm}")
        self.card_average.set_value(f"{average:+.3f} {unit_mm}")

        thresholds = self.app_state.current_settings.thresholds
        if max_delta >= thresholds.belt_threshold:
            status_key = "neo_ui.bed.status.need_belt"
        elif max_delta >= thresholds.screw_threshold:
            status_key = "neo_ui.bed.status.need_screws"
        elif max_delta >= thresholds.tape_threshold:
            status_key = "neo_ui.bed.status.need_tape"
        else:
            status_key = "neo_ui.bed.status.ok"
        status_text = self.localization.translate(status_key)
        self.card_status.set_value(status_text)
        self.card_status.reset_value_font()
        if len(status_text) > 18:
            self.card_status.set_value_font(16)
        self.card_status.set_subtitle(None)

    def _update_recommendations(self) -> None:
        tr = self.localization.translate
        if not self.workspace or not self.workspace.workflow:
            self.recommendations_body.setText(tr("neo_ui.bed.recommendations.placeholder"))
            return

        workflow = self.workspace.workflow
        best_stage = workflow.best_stage
        if best_stage:
            summary_text = tr("neo_ui.bed.recommendations.summary").format(
                stage=tr(best_stage.label),
                deviation=getattr(best_stage, "deviation", 0.0),
            )
        else:
            summary_text = tr("neo_ui.bed.recommendations.modal_placeholder")
        self.recommendations_body.setText(summary_text)

    def _render_visualizations(self) -> None:
        if not self.workspace:
            return
        if self._render_lock:
            return
        self._render_lock = True

        self._remove_canvas()
        self.heatmap_placeholder.show()
        self.surface_placeholder.show()

        self._update_fig_dimensions()
        frame_height = self._fig_pixel_height + 32

        heatmap_figure = self._create_figure("2d")
        surface_figure = self._create_figure("3d")
        if heatmap_figure:
            self.heatmap_canvas = FigureCanvasQTAgg(heatmap_figure)
            self.heatmap_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.heatmap_canvas.setStyleSheet("background: transparent;")
            self.heatmap_canvas.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.heatmap_holder.layout().insertWidget(0, self.heatmap_canvas, alignment=Qt.AlignTop)
            self.heatmap_canvas.setMinimumHeight(self._fig_pixel_height)
            self.heatmap_placeholder.hide()
        if surface_figure:
            self.surface_canvas = FigureCanvasQTAgg(surface_figure)
            self.surface_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.surface_canvas.setStyleSheet("background: transparent;")
            self.surface_holder.layout().insertWidget(0, self.surface_canvas, alignment=Qt.AlignTop)
            self.surface_canvas.setMinimumHeight(self._fig_pixel_height)
            self.surface_placeholder.hide()

        self.figure_frame.setMinimumHeight(frame_height)
        self.figure_frame.setMaximumHeight(frame_height)
        self._last_render_size = (self.figure_frame.width(), self.figure_frame.height())
        self._render_lock = False

    def _remove_canvas(self) -> None:
        for canvas in (self.heatmap_canvas, self.surface_canvas):
            if canvas:
                canvas.setParent(None)
                canvas.deleteLater()
        self.heatmap_placeholder.show()
        self.surface_placeholder.show()
        self.heatmap_canvas = None
        self.surface_canvas = None
        self.figure_frame.setMaximumHeight(16777215)
        self.figure_frame.setMinimumHeight(0)

    def _export_current_figure(self, extension: str) -> None:
        if not self.heatmap_canvas:
            QMessageBox.information(
                self,
                self.localization.translate("neo_ui.common.warning"),
                self.localization.translate("neo_ui.bed.export.no_data"),
            )
            return

        tr = self.localization.translate
        filters = {
            "png": "PNG (*.png)",
            "pdf": "PDF (*.pdf)",
        }
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("neo_ui.bed.export.dialog_title"),
            str(Path.home() / f"bed_visualization.{extension}"),
            filters.get(extension, "All Files (*)"),
        )
        if not file_path:
            return

        self.heatmap_canvas.figure.savefig(file_path)
        QMessageBox.information(
            self,
            tr("neo_ui.common.success"),
            tr("neo_ui.bed.export.success").format(path=file_path),
        )

    def _update_visual_controls(self) -> None:
        enabled = self.workspace is not None
        self.export_png_button.setEnabled(enabled)
        self.visual_button_cta.setEnabled(enabled)

    def _is_dark_theme(self) -> bool:
        return self.app_state.current_settings.theme == "dark"

    def _update_last_file_label(self, file_path: Optional[Path]) -> None:
        if self.last_file_label is None:
            return
        tr = self.localization.translate
        if file_path:
            self.last_file_label.setText(tr("neo_ui.bed.last_file").format(file=file_path.name))
        else:
            self.last_file_label.setText(tr("neo_ui.bed.last_file_none"))

    def _create_figure(self, mode: str):
        if not self.workspace:
            return None

        width_inches = self._fig_width_inches
        height_inches = self._fig_height_inches

        mesh = self.workspace.mesh_matrix
        if mesh is None:
            return None

        if mode == "2d":
            self._heatmap.set_theme(self._is_dark_theme())
            self._heatmap.set_mesh_data(mesh)
            self._heatmap.set_figsize(width_inches, height_inches)
            return self._heatmap.create_2d_figure()
        if mode == "3d":
            self._surface.set_theme(self._is_dark_theme())
            self._surface.set_mesh_data(mesh)
            self._surface.set_figsize(width_inches, height_inches)
            return self._surface.create_3d_figure()
        return None

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if not self.workspace:
            return
        width = self.figure_frame.width()
        height = self.figure_frame.height()
        if width <= 0 or height <= 0:
            return
        last_w, last_h = self._last_render_size
        if abs(width - last_w) < 40 and abs(height - last_h) < 40:
            return
        self._render_visualizations()

    def _update_fig_dimensions(self) -> None:
        dpi = 100
        frame_width = self.figure_frame.width()
        width_inches = frame_width / dpi if frame_width > 0 else self._fig_width_inches
        self._fig_width_inches = max(4.5, width_inches)
        # keep a compact, fixed height so the card doesn't stretch endlessly
        self._fig_height_inches = 3.6
        self._fig_pixel_height = int(self._fig_height_inches * dpi)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PySide6 dialog that presents visual recommendations for bed leveling.

The dialog integrates tightly with the Qt-based workflow and relies on the
animated visualizers from ``visualization.bed_mesh.animated_recommendations``.
"""

from __future__ import annotations

import html
from typing import Iterable, Optional

import numpy as np
from matplotlib import animation
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from calibration.hardware.screw import RotationDirection
from calibration.workflow import StageAction, StageResult, WorkflowData

from flashforge_app.services.localization import LocalizationService
from flashforge_app.services.settings import ApplicationSettings
from visualization.bed_mesh.animated_recommendations import (
    ScrewAdjustmentVisualizer,
    TapeCell,
    TapeLayoutVisualizer,
)


class VisualRecommendationsDialog(QDialog):
    """
    Диалог визуальных рекомендаций с оптимизированной компоновкой:

    • Увеличенная область визуализации
    • Компактное расположение метрик и действий
    • Улучшенная анимация винтов (как в референсе)
    """

    def __init__(
        self,
        localization: LocalizationService,
        workflow: WorkflowData,
        settings: ApplicationSettings,
        theme: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.localization = localization
        self.workflow = workflow
        self.settings = settings
        self.theme = theme
        self.show_minutes = bool(settings.visualization.show_minutes)
        self.show_degrees = bool(settings.visualization.show_degrees)

        self._current_animation: Optional[animation.FuncAnimation] = None
        self._qt_anim_timer: Optional[QTimer] = None
        self.figure_canvas: Optional[FigureCanvasQTAgg] = None

        self.setWindowTitle(self.localization.translate("neo_ui.visual.title"))
        self.resize(1100, 720)

        self._build_ui()
        self._populate_stage_list()
        if self.stage_list.count():
            self.stage_list.setCurrentRow(0)

    # ------------------------------------------------------------------ UI construction
    def _build_ui(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        self.setLayout(root)

        # Body - основная область
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)
        root.addLayout(body, stretch=1)

        # Stage list (узкий)
        self.stage_list = QListWidget()
        self.stage_list.setObjectName("Card")
        self.stage_list.setFixedWidth(260)
        self.stage_list.setSpacing(3)
        self.stage_list.setSelectionMode(QListWidget.SingleSelection)
        self.stage_list.currentRowChanged.connect(self._handle_stage_changed)
        body.addWidget(self.stage_list, 0)

        # Details panel - расширяемый
        detail_container = QFrame()
        detail_container.setObjectName("Card")
        detail_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(12)
        detail_container.setLayout(detail_layout)
        body.addWidget(detail_container, 1)

        # Header блок - компактный
        header_block = QVBoxLayout()
        header_block.setContentsMargins(0, 0, 0, 0)
        header_block.setSpacing(8)
        detail_layout.addLayout(header_block)

        self.stage_title_label = QLabel()
        self.stage_title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        header_block.addWidget(self.stage_title_label)

        self.stage_description_label = QLabel()
        self.stage_description_label.setObjectName("Subtitle")
        self.stage_description_label.setWordWrap(True)
        header_block.addWidget(self.stage_description_label)

        metrics_row = QHBoxLayout()
        metrics_row.setContentsMargins(0, 0, 0, 0)
        metrics_row.setSpacing(8)
        header_block.addLayout(metrics_row)

        self.metric_widgets: dict[str, QLabel] = {}
        for key, tr_key in [
            ("deviation", "neo_ui.visual.deviation"),
            ("baseline", "neo_ui.visual.baseline"),
            ("improvement", "neo_ui.visual.improvement"),
        ]:
            wrapper = QFrame()
            wrapper.setObjectName("MetricChip")
            wrapper.setStyleSheet(
                "QFrame#MetricChip { border: 1px solid #3B82F6; border-radius: 6px; padding: 4px 8px; }"
            )
            chip_layout = QVBoxLayout()
            chip_layout.setContentsMargins(0, 0, 0, 0)
            chip_layout.setSpacing(1)
            wrapper.setLayout(chip_layout)

            label = QLabel(self.localization.translate(tr_key))
            label.setObjectName("Caption")
            label.setStyleSheet("font-size: 10px;")
            value = QLabel("—")
            value.setStyleSheet("font-size: 13px; font-weight: 600;")

            chip_layout.addWidget(label)
            chip_layout.addWidget(value)
            metrics_row.addWidget(wrapper)
            self.metric_widgets[key] = value

        metrics_row.addStretch(1)

        self.stage_meta_label = QLabel()
        self.stage_meta_label.setObjectName("Caption")
        self.stage_meta_label.setWordWrap(True)
        self.stage_meta_label.hide()
        header_block.addWidget(self.stage_meta_label)

        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #F87171; font-weight: 600; font-size: 12px;")
        self.warning_label.hide()
        header_block.addWidget(self.warning_label)

        # ГЛАВНАЯ ОБЛАСТЬ - Figure (максимально большая)
        self.figure_frame = QFrame()
        self.figure_frame.setObjectName("FigureHolder")
        self.figure_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.figure_frame.setMinimumHeight(330)
        figure_layout = QVBoxLayout()
        figure_layout.setContentsMargins(0, 0, 0, 0)
        figure_layout.setSpacing(0)
        self.figure_frame.setLayout(figure_layout)
        detail_layout.addWidget(self.figure_frame, stretch=5)

        self.figure_placeholder = QLabel(self.localization.translate("neo_ui.visual.figure_placeholder"))
        self.figure_placeholder.setObjectName("Subtitle")
        self.figure_placeholder.setAlignment(Qt.AlignCenter)
        self.figure_frame.layout().addWidget(self.figure_placeholder, alignment=Qt.AlignCenter)

        # Нижняя панель - компактная, горизонтальная
        bottom_panel = QHBoxLayout()
        bottom_panel.setContentsMargins(0, 0, 0, 0)
        bottom_panel.setSpacing(12)
        detail_layout.addLayout(bottom_panel, stretch=5)

        # Actions - компактный список слева
        actions_container = QVBoxLayout()
        actions_container.setContentsMargins(0, 0, 0, 0)
        actions_container.setSpacing(6)
        bottom_panel.addLayout(actions_container, stretch=2)

        actions_title = QLabel(self.localization.translate("neo_ui.visual.actions"))
        actions_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        actions_container.addWidget(actions_title)

        actions_scroll = QScrollArea()
        actions_scroll.setWidgetResizable(True)
        actions_scroll.setFrameStyle(QFrame.NoFrame)
        actions_scroll.setMaximumHeight(300)
        actions_container.addWidget(actions_scroll)

        actions_widget = QWidget()
        self.actions_layout = QVBoxLayout()
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(6)
        actions_widget.setLayout(self.actions_layout)
        actions_scroll.setWidget(actions_widget)

        # Hints - справа
        hints_container = QVBoxLayout()
        hints_container.setContentsMargins(0, 0, 0, 0)
        hints_container.setSpacing(6)
        bottom_panel.addLayout(hints_container, stretch=3)

        hints_title = QLabel(self.localization.translate("neo_ui.visual.hints.instructions_short"))
        hints_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        hints_container.addWidget(hints_title)

        self.hints_text = QTextEdit()
        self.hints_text.setReadOnly(True)
        self.hints_text.setObjectName("Caption")
        self.hints_text.setMaximumHeight(300)
        hints_container.addWidget(self.hints_text)

        # Footer
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)
        footer.addStretch(1)
        close_button = QPushButton(self.localization.translate("neo_ui.visual.close"))
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        root.addLayout(footer)

    # ------------------------------------------------------------------ header
    # ------------------------------------------------------------------ stages
    def _populate_stage_list(self) -> None:
        self.stage_list.clear()
        tr = self.localization.translate
        best = self._best_stage()
        for stage in self.workflow.stages:
            if stage.key == "initial":
                continue
            label = tr(stage.label)
            if stage.key == "after_temperature":
                model = self._active_thermal_model()
                label = f"{label} ({model['measurement_temp']:.0f}°C → {model['target_temp']:.0f}°C)"
            deviation = f"{stage.deviation:.3f} mm"
            if best and stage.key == best.key:
                label = f"★ {label}"
            item = QListWidgetItem(f"{label}\n{deviation}")
            item.setData(Qt.UserRole, stage)
            size = item.sizeHint()
            item.setSizeHint(QSize(size.width(), size.height() + 8))
            self.stage_list.addItem(item)

    def _handle_stage_changed(self, row: int) -> None:
        item = self.stage_list.item(row)
        if not item:
            return
        stage: StageResult = item.data(Qt.UserRole)
        self._display_stage(stage)

    def _display_stage(self, stage: StageResult) -> None:
        tr = self.localization.translate
        self.stage_title_label.setText(tr(stage.label))
        self.stage_description_label.setText(self._stage_description(stage))

        self._update_metrics(stage)
        self._update_stage_meta(stage)
        self._render_warnings(stage)
        self._render_actions(stage.actions)
        self._render_hints(stage)
        self._render_stage_figure(stage)

    # ------------------------------------------------------------------ metrics & warnings
    def _update_metrics(self, stage: StageResult) -> None:
        def _fmt(value: Optional[float]) -> str:
            if value is None:
                return "—"
            return f"{value:.3f} mm"

        deviation = stage.deviation
        baseline = stage.baseline
        improvement = None
        if baseline is not None:
            improvement = baseline - deviation

        self.metric_widgets["deviation"].setText(_fmt(deviation))
        self.metric_widgets["baseline"].setText(_fmt(baseline))
        if improvement is not None:
            sign = "+" if improvement >= 0 else ""
            self.metric_widgets["improvement"].setText(f"{sign}{improvement:.3f} mm")
        else:
            self.metric_widgets["improvement"].setText("—")

    def _update_stage_meta(self, stage: StageResult) -> None:
        if stage.key != "after_temperature":
            self.stage_meta_label.hide()
            self.stage_meta_label.clear()
            return

        tr = self.localization.translate
        model = self._active_thermal_model()
        info = stage.metadata or {}
        name = model.get("name") or tr("temperature_preset_custom", "Custom preset")
        measurement = model.get("measurement_temp", self.settings.environment.measurement_temp)
        target = model.get("target_temp", self.settings.environment.target_temp)
        gamma = model.get("chamber_factor", 0.0)
        beta_uniform = model.get("beta_uniform", 0.0)
        pei = model.get("pei_thickness", 0.0)
        steel = model.get("steel_thickness", 0.0)
        alpha_pe = model.get("alpha_pei", 0.0)
        alpha_steel = model.get("alpha_steel", 0.0)

        delta_through = info.get("delta_through", 0.0)
        delta_uniform = info.get("delta_uniform", 0.0)
        kappa_total = info.get("kappa_total", 0.0)
        warp_range = info.get("warp_range", 0.0)
        warp_half = max(abs(info.get("warp_max", 0.0)), abs(info.get("warp_min", 0.0)))

        preset_tpl = tr(
            "temperature_preset_line",
            "Preset: {name} ({measurement:.0f}°C → {target:.0f}°C)",
        )
        profile_tpl = tr(
            "temperature_profile_line",
            "PEI {pei:.2f} mm • Steel {steel:.2f} mm • γ={gamma:.2f} • β={beta:.2f}",
        )
        coeff_tpl = tr(
            "temperature_coeff_line",
            "α_PE={alpha_pe:.2e} • α steel={alpha_steel:.2e}",
        )
        delta_tpl = tr(
            "temperature_delta_line",
            "Surface ΔT={delta_through:.1f}°C • Chamber ΔT={delta_uniform:.1f}°C",
        )
        curvature_tpl = tr(
            "temperature_curvature_line",
            "Curvature ≈ {kappa:.3e} 1/mm • Warp ±{warp:.3f} mm (range {warp_range:.3f} mm)",
        )

        lines = [
            preset_tpl.format(name=name, measurement=measurement, target=target),
            profile_tpl.format(pei=pei, steel=steel, gamma=gamma, beta=beta_uniform),
            coeff_tpl.format(alpha_pe=alpha_pe, alpha_steel=alpha_steel),
            delta_tpl.format(delta_through=delta_through, delta_uniform=delta_uniform),
            curvature_tpl.format(kappa=kappa_total, warp=warp_half, warp_range=warp_range),
        ]
        self.stage_meta_label.setText("<br>".join(html.escape(line) for line in lines))
        self.stage_meta_label.show()

    def _render_warnings(self, stage: StageResult) -> None:
        tr = self.localization.translate
        if stage.warnings:
            warnings_html = "<br>".join(html.escape(tr(w)) for w in stage.warnings)
            self.warning_label.setText(warnings_html)
            self.warning_label.show()
        else:
            self.warning_label.clear()
            self.warning_label.hide()

    # ------------------------------------------------------------------ actions & hints
    def _render_actions(self, actions: Iterable[StageAction]) -> None:
        self._clear_layout(self.actions_layout)
        actions = list(actions)
        tr = self.localization.translate
        if not actions:
            empty = QLabel(tr("neo_ui.visual.no_actions"))
            empty.setObjectName("Caption")
            self.actions_layout.addWidget(empty)
            self.actions_layout.addStretch(1)
            return

        for action in actions:
            frame = QFrame()
            frame.setObjectName("ActionCard")
            frame.setStyleSheet(
                "QFrame#ActionCard { border: 1px solid #3B82F6; border-radius: 4px; background: rgba(59, 130, 246, 0.1); }"
            )
            layout = QVBoxLayout()
            layout.setContentsMargins(8, 6, 8, 6)
            layout.setSpacing(3)
            frame.setLayout(layout)

            title = QLabel(tr(action.label))
            title.setStyleSheet("font-weight: 600; font-size: 12px;")
            layout.addWidget(title)

            details = QLabel(self._format_action(action))
            details.setWordWrap(True)
            details.setStyleSheet("font-size: 11px;")
            layout.addWidget(details)

            self.actions_layout.addWidget(frame)

        self.actions_layout.addStretch(1)

    def _render_hints(self, stage: StageResult) -> None:
        hints = self._stage_hints(stage)
        if hints:
            html_text = "<ul style='margin: 0; padding-left: 20px;'>"
            for line in hints:
                html_text += f"<li style='margin-bottom: 4px;'>{html.escape(line)}</li>"
            html_text += "</ul>"
        else:
            html_text = self.localization.translate("neo_ui.visual.hints.instructions_short")
        self.hints_text.setHtml(html_text)

    # ------------------------------------------------------------------ figures
    def _render_stage_figure(self, stage: StageResult) -> None:
        self._clear_figure()
        fig: Optional[Figure] = None
        animator: Optional[animation.FuncAnimation] = None

        if stage.key == "after_screws":
            fig, animator = self._build_screw_figure(stage)
        elif stage.key == "after_belts":
            fig, animator = self._build_belt_figure(stage)
        elif stage.key == "after_tape":
            fig = self._build_tape_figure(stage)
        elif stage.mesh is not None:
            fig = self._build_heatmap(stage)

        if fig is None:
            self.figure_placeholder.show()
            return

        self.figure_canvas = FigureCanvasQTAgg(fig)
        self.figure_canvas.setStyleSheet("background: transparent;")
        self.figure_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.figure_frame.layout().addWidget(self.figure_canvas)
        self.figure_placeholder.hide()

        # Сохраняем анимацию
        self._current_animation = animator
        if animator:
            # КРИТИЧНО: подключаем анимацию к canvas через _draw_event
            def on_draw(_event) -> None:
                pass

            self.figure_canvas.mpl_connect("draw_event", on_draw)
            QTimer.singleShot(100, lambda: self._start_animation(animator))

    def _start_animation(self, animator: animation.FuncAnimation) -> None:
        """Запускает анимацию после того как canvas отрисован."""
        if not animator or not self.figure_canvas:
            return
        try:
            original_update = animator._func  # type: ignore[attr-defined]
            canvas = self.figure_canvas

            # Выполняем первый кадр до старта, чтобы клин стал видимым
            try:
                original_update(1)
            except Exception:
                pass

            def patched_update(frame):
                result = original_update(frame)
                canvas.draw_idle()
                return result

            animator._func = patched_update  # type: ignore[attr-defined]
            self.figure_canvas.draw()

            # Переводим управление таймером в Qt, чтобы гарантировать обновление
            if self._qt_anim_timer:
                self._qt_anim_timer.stop()
                self._qt_anim_timer.deleteLater()
            interval = 120
            native_timer = getattr(animator, "event_source", None)
            if native_timer is not None:
                try:
                    interval = int(native_timer.interval)
                    native_timer.stop()
                except Exception:
                    pass
            self._qt_anim_timer = QTimer(self)
            self._qt_anim_timer.setInterval(max(30, interval))

            def step_animation() -> None:
                try:
                    animator._step()  # type: ignore[attr-defined]
                except Exception:
                    pass

            self._qt_anim_timer.timeout.connect(step_animation)
            self._qt_anim_timer.start()
            step_animation()
        except (AttributeError, RuntimeError):
            pass

    def _build_screw_figure(self, stage: StageResult) -> tuple[Optional[Figure], Optional[animation.FuncAnimation]]:
        """Построение анимированной фигуры винтов (как в референсе)."""
        adjustments: dict[str, tuple[float, RotationDirection]] = {}

        for action in stage.actions:
            minutes = action.minutes
            if minutes is None and action.degrees is not None:
                minutes = action.degrees / 6.0
            if minutes is None and action.metadata and action.metadata.get("turns") is not None:
                minutes = float(action.metadata["turns"]) * 60.0
            if minutes is None:
                continue

            direction = RotationDirection.COUNTERCLOCKWISE
            if action.direction:
                dir_lower = action.direction.lower()
                if dir_lower in {"clockwise", "down", "cw"}:
                    direction = RotationDirection.CLOCKWISE
                elif dir_lower in {"counterclockwise", "up", "ccw"}:
                    direction = RotationDirection.COUNTERCLOCKWISE

            adjustments[action.identifier] = (abs(float(minutes)), direction)

        if not adjustments:
            return None, None

        visualizer = ScrewAdjustmentVisualizer(
            translator=self.localization.translate,
            is_dark_theme=self.theme == "dark",
            show_minutes=self.show_minutes,
            show_degrees=self.show_degrees,
            screw_mode=self.settings.hardware.screw_mode,
        )

        fig = visualizer.create_adjustment_figure(adjustments)
        fig.set_size_inches(11, 8)
        fig.set_dpi(100)
        animator = getattr(fig, "animation", None)
        return fig, animator

    def _build_belt_figure(self, stage: StageResult) -> tuple[Optional[Figure], Optional[animation.FuncAnimation]]:
        """Построение фигуры синхронизации валов."""
        adjustments: dict[str, dict[str, object]] = {}

        for action in stage.actions:
            if action.kind != "belt":
                continue
            teeth = action.teeth
            if teeth is None and action.metadata:
                teeth = action.metadata.get("teeth")
            if teeth is None or int(teeth) <= 0:
                continue
            adjustments[action.identifier] = {
                "teeth": int(teeth),
                "direction": action.direction or "",
                "delta_mm": float(action.magnitude_mm or 0.0),
            }

        if not adjustments:
            return None, None

        visualizer = ScrewAdjustmentVisualizer(
            translator=self.localization.translate,
            is_dark_theme=self.theme == "dark",
            show_minutes=self.show_minutes,
            show_degrees=self.show_degrees,
            screw_mode=self.settings.hardware.screw_mode,
        )

        fig = visualizer.create_belt_animation_figure(adjustments)
        fig.set_size_inches(11, 8)
        fig.set_dpi(100)
        animator = getattr(fig, "animation", None)
        return fig, animator

    def _build_tape_figure(self, stage: StageResult) -> Optional[Figure]:
        if stage.mesh is None:
            return None

        cells: list[TapeCell] = []
        for action in stage.actions:
            identifier = action.identifier or ""
            coords = self._parse_grid_identifier(identifier)
            if not coords:
                continue
            row, col = coords
            layers = 0
            if action.metadata:
                layers = int(action.metadata.get("layers", 0) or 0)
            delta = abs(float(action.magnitude_mm or 0.0))
            cells.append(TapeCell(row=row, col=col, layers=layers, delta=delta))

        thresholds = getattr(self.settings, "thresholds", None)
        hardware = getattr(self.settings, "hardware", None)
        tape_threshold = getattr(thresholds, "tape_threshold", None) if thresholds else None
        tape_thickness = getattr(hardware, "tape_thickness", None) if hardware else None

        visualizer = TapeLayoutVisualizer(
            translator=self.localization.translate,
            is_dark_theme=self.theme == "dark",
        )
        fig = visualizer.create_tape_figure(
            np.array(stage.mesh, dtype=float),
            cells,
            threshold_mm=tape_threshold,
            tape_thickness=tape_thickness,
        )

        if fig:
            fig.set_size_inches(11, 8)
            fig.set_dpi(100)
            fig.tight_layout(pad=0.5)

        return fig

    def _build_heatmap(self, stage: StageResult) -> Optional[Figure]:
        if stage.mesh is None:
            return None
        data = np.array(stage.mesh, dtype=float)
        rows, cols = data.shape

        fig = Figure(figsize=(11, 8), dpi=100)
        fig.patch.set_alpha(0.0)
        ax = fig.add_subplot(111)
        ax.set_facecolor("none")
        text_color = "#F8FAFC" if self.theme == "dark" else "#1E293B"

        is_temperature = stage.key == "after_temperature"
        info = stage.metadata or {}

        if is_temperature:
            bed_x = float(info.get("bed_size_x", cols))
            bed_y = float(info.get("bed_size_y", rows))
            half_x = bed_x / 2.0
            half_y = bed_y / 2.0
            x_axis = np.linspace(-half_x, half_x, cols)
            y_axis = np.linspace(-half_y, half_y, rows)
            extent = (-half_x, half_x, -half_y, half_y)
            heatmap_data = np.flipud(data)
            im = ax.imshow(
                heatmap_data,
                cmap="coolwarm_r",
                interpolation="bilinear",
                origin="lower",
                extent=extent,
                aspect="equal",
            )

            x_ticks = np.linspace(-half_x, half_x, min(cols, 7))
            y_ticks = np.linspace(-half_y, half_y, min(rows, 7))
            ax.set_xticks(x_ticks)
            ax.set_yticks(y_ticks)
            ax.set_xticklabels([f"{tick:.0f}" for tick in x_ticks], color=text_color, fontsize=11)
            ax.set_yticklabels([f"{tick:.0f}" for tick in y_ticks], color=text_color, fontsize=11)
            ax.set_xlabel("X offset (mm)", color=text_color, fontsize=11)
            ax.set_ylabel("Y offset (mm)", color=text_color, fontsize=11)
            ax.set_xlim(-half_x, half_x)
            ax.set_ylim(-half_y, half_y)

            Xg, Yg = np.meshgrid(x_axis, np.linspace(-half_y, half_y, rows))
            levels = np.linspace(np.min(data), np.max(data), 9)
            ax.contour(
                Xg,
                Yg,
                np.flipud(data),
                levels=levels,
                colors="#64748B",
                linewidths=0.6,
                alpha=0.6,
            )
            if np.min(data) <= 0.0 <= np.max(data):
                ax.contour(
                    Xg,
                    Yg,
                    np.flipud(data),
                    levels=[0.0],
                    colors="#2563EB",
                    linewidths=1.2,
                )

            # annotate center and corners
            def _annotate(point_x: float, point_y: float, value: float, weight: str = "normal") -> None:
                ax.text(
                    point_x,
                    point_y,
                    f"{value:+.2f}",
                    ha="center",
                    va="center",
                    fontsize=11,
                    fontweight=weight,
                    color=text_color,
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#ffffff" if self.theme != "dark" else "#1f2937", alpha=0.6, edgecolor="none"),
                )

            center_value = data[rows // 2, cols // 2]
            _annotate(0.0, 0.0, center_value, weight="bold")
            for px, py, vx in [
                (-half_x, -half_y, data[-1, 0]),
                (-half_x, half_y, data[0, 0]),
                (half_x, -half_y, data[-1, -1]),
                (half_x, half_y, data[0, -1]),
            ]:
                _annotate(px, py, vx)

            ax.set_aspect('equal')
            ax.grid(which="both", linestyle=":", linewidth=0.6, color="#94A3B8", alpha=0.3)
        else:
            flipped = np.flipud(data)
            im = ax.imshow(flipped, cmap="coolwarm_r", aspect="equal", interpolation="bilinear")
            ax.set_xlim(-0.5, cols - 0.5)
            ax.set_ylim(rows - 0.5, -0.5)
            ax.set_xticks(range(cols))
            ax.set_yticks(range(rows))
            ax.set_xticklabels([chr(65 + c) for c in range(cols)], color=text_color, fontsize=12)
            ax.set_yticklabels([str(rows - r) for r in range(rows)], color=text_color, fontsize=12)
            ax.grid(which="both", linestyle=":", linewidth=0.8, color="#64748B", alpha=0.4)

        # Используем встроенную ось для шкалы, чтобы карта оставалась по центру
        cax = inset_axes(ax, width="3%", height="75%", loc="center right", borderpad=1.2)
        colorbar = fig.colorbar(im, cax=cax)
        colorbar.ax.tick_params(labelsize=10, colors=text_color)

        title_text = self.localization.translate(stage.label)
        colorbar_label = "Height (mm)"
        if stage.key == "after_temperature":
            model = self._active_thermal_model()
            info = stage.metadata or {}
            title_tpl = self.localization.translate(
                "temperature_map_title",
                "Predicted thermal warp {measure:.0f}°C → {target:.0f}°C (κ={coeff:.1e})",
            )
            title_text = title_tpl.format(
                measure=model["measurement_temp"],
                target=model["target_temp"],
                coeff=info.get("kappa_total", 0.0),
            )
            colorbar_label = self.localization.translate(
                "temperature_delta_label",
                "Δ height (mm)",
            )
        colorbar.set_label(colorbar_label, color=text_color, fontsize=11)

        self._annotate_heatmap_actions(ax, stage, data.shape, text_color)

        ax.set_title(title_text, color=text_color, fontsize=15, fontweight="bold", pad=12)
        fig.tight_layout(pad=0.5)
        return fig

    # ------------------------------------------------------------------ helpers
    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._stop_animation()
        super().closeEvent(event)

    def _stop_animation(self) -> None:
        if self._current_animation and getattr(self._current_animation, "event_source", None):
            try:
                self._current_animation.event_source.stop()
            except (AttributeError, RuntimeError):
                pass
        self._current_animation = None
        if self._qt_anim_timer:
            self._qt_anim_timer.stop()
            self._qt_anim_timer.deleteLater()
            self._qt_anim_timer = None

    def _clear_figure(self) -> None:
        self._stop_animation()
        if self.figure_canvas:
            self.figure_canvas.setParent(None)
            self.figure_canvas.deleteLater()
            self.figure_canvas = None
        self.figure_placeholder.show()

    def _best_stage(self) -> Optional[StageResult]:
        actionable = [
            stage
            for stage in self.workflow.stages
            if stage.key != "initial" and stage.enabled and stage.actions
        ]
        if actionable:
            return min(actionable, key=lambda st: st.deviation)
        candidates = [
            stage for stage in self.workflow.stages if stage.key != "initial" and stage.enabled
        ]
        if candidates:
            return min(candidates, key=lambda st: st.deviation)
        return next((st for st in self.workflow.stages if st.key != "initial"), None)

    def _stage_description(self, stage: StageResult) -> str:
        tr = self.localization.translate
        if stage.description:
            return tr(stage.description)
        return tr("neo_ui.visual.hints.instructions_short")

    def _stage_hints(self, stage: StageResult) -> list[str]:
        tr = self.localization.translate
        thresholds = self.settings.thresholds
        hardware = self.settings.hardware
        env = self.settings.environment

        key = stage.key
        hints: list[str] = []
        if key == "after_belts":
            hints.append(
                tr("neo_ui.visual.hints.belts.threshold").format(
                    threshold=thresholds.belt_threshold,
                    tooth=hardware.belt_tooth_mm,
                )
            )
            hints.append(tr("neo_ui.visual.hints.belts.overview"))
            hints.append(tr("neo_ui.visual.hints.belts.tip"))
        elif key == "after_screws":
            hints.append(
                tr("neo_ui.visual.hints.screws.threshold").format(
                    threshold=thresholds.screw_threshold,
                    pitch=hardware.screw_pitch,
                )
            )
            hints.append(tr("neo_ui.visual.hints.screws.legend"))
            hints.append("Анимированные дуги показывают направление и величину поворота каждого винта")
        elif key == "after_tape":
            hints.append(
                tr("neo_ui.visual.hints.tape.thickness").format(
                    thickness=hardware.tape_thickness,
                )
            )
            hints.append(tr("neo_ui.visual.hints.tape.title"))
            hints.append(tr("neo_ui.visual.hints.tape.step_1"))
            hints.append(tr("neo_ui.visual.hints.tape.step_2"))
            hints.append(tr("neo_ui.visual.hints.tape.step_3"))
            hints.append(tr("neo_ui.visual.hints.tape.step_4"))
        elif key == "after_temperature":
            model = self._active_thermal_model()
            info = stage.metadata or {}
            name = model.get("name") or tr("temperature_preset_custom")
            hints.append(tr(
                "temperature_preset_line",
                "Preset: {name} ({measurement:.0f}°C → {target:.0f}°C)",
            ).format(name=name, measurement=model["measurement_temp"], target=model["target_temp"]))
            hints.append(tr(
                "temperature_profile_line",
                "PEI {pei:.2f} mm • Steel {steel:.2f} mm • γ={gamma:.2f} • β={beta:.2f}",
            ).format(pei=model["pei_thickness"], steel=model["steel_thickness"], gamma=model["chamber_factor"], beta=model["beta_uniform"]))
            hints.append(tr(
                "temperature_coeff_line",
                "α_PE={alpha_pe:.2e} • α_steel={alpha_steel:.2e}",
            ).format(alpha_pe=model["alpha_pei"], alpha_steel=model["alpha_steel"]))
            hints.append(tr(
                "temperature_delta_line",
                "Surface ΔT={delta_through:.1f}°C • Chamber ΔT={delta_uniform:.1f}°C",
            ).format(delta_through=info.get("delta_through", 0.0), delta_uniform=info.get("delta_uniform", 0.0)))
            hints.append(tr(
                "temperature_curvature_line",
                "Curvature ≈ {kappa:.3e} 1/mm • Warp ±{warp:.3f} mm (range {warp_range:.3f} mm)",
            ).format(
                kappa=info.get("kappa_total", 0.0),
                warp=max(abs(info.get("warp_max", 0.0)), abs(info.get("warp_min", 0.0))),
                warp_range=info.get("warp_range", 0.0),
            ))
            hints.append(tr("neo_ui.visual.hints.temperature.tip"))
        elif stage.description:
            hints.append(tr(stage.description))
        return hints

    def _format_action(self, action: StageAction) -> str:
        tr = self.localization.translate
        if action.kind == "belt":
            direction = tr(
                "neo_ui.visual.belt.direction.up"
                if action.direction == "up"
                else "neo_ui.visual.belt.direction.down"
            )
            parts = [direction]
            if action.teeth:
                parts.append(tr("neo_ui.visual.belt.teeth").format(count=action.teeth))
            if action.magnitude_mm is not None:
                parts.append(tr("neo_ui.visual.delta").format(value=action.magnitude_mm))
            return " | ".join(parts)
        if action.kind == "screw":
            parts = []
            if action.minutes is not None:
                parts.append(tr("neo_ui.visual.screw.minutes").format(value=action.minutes))
            if action.degrees is not None:
                parts.append(tr("neo_ui.visual.screw.degrees").format(value=action.degrees))
            turns = action.metadata.get("turns") if action.metadata else None
            if turns is not None:
                parts.append(tr("neo_ui.visual.screw.turns").format(value=turns))
            direction = tr(
                "neo_ui.visual.screw.counterclockwise"
                if action.direction == "counterclockwise"
                else "neo_ui.visual.screw.clockwise"
            )
            parts.append(direction)
            return " | ".join(parts)
        if action.kind == "tape":
            layers = action.metadata.get("layers", 0) if action.metadata else 0
            thickness = action.metadata.get("thickness", 0.0) if action.metadata else 0.0
            return " | ".join(
                [
                    tr("neo_ui.visual.tape.layers").format(value=layers),
                    tr("neo_ui.visual.delta").format(value=thickness),
                ]
            )
        if action.magnitude_mm is not None:
            return tr("neo_ui.visual.delta").format(value=action.magnitude_mm)
        return tr(action.label)

    def _annotate_heatmap_actions(self, ax, stage: StageResult, shape: tuple[int, int], text_color: str) -> None:
        rows, cols = shape
        for action in stage.actions:
            coords = self._resolve_identifier(action.identifier, rows, cols)
            if not coords:
                continue
            r, c = coords
            r = rows - 1 - r  # account for flipped heatmap
            color = "#F59E0B" if action.kind == "tape" else "#F97316"
            ax.scatter([c], [r], s=130, c=color, edgecolors="black", linewidths=1.6, zorder=3, alpha=0.9)
            ax.text(
                c,
                r - 0.35,
                action.identifier.upper(),
                ha="center",
                va="top",
                fontsize=10,
                fontweight="bold",
                color=text_color,
                zorder=4,
            )

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _active_thermal_model(self) -> dict[str, float]:
        model = dict(getattr(self.workflow, "active_thermal_model", None) or {})
        env = self.settings.environment
        defaults = {
            "name": model.get("name", ""),
            "measurement_temp": model.get("measurement_temp", env.measurement_temp),
            "target_temp": model.get("target_temp", env.target_temp),
            "chamber_factor": model.get("chamber_factor", 0.0),
            "pei_thickness": model.get("pei_thickness", 0.55),
            "steel_thickness": model.get("steel_thickness", 1.50),
            "alpha_pei": model.get("alpha_pei", 5.0e-5),
            "alpha_steel": model.get("alpha_steel", 1.2e-5),
            "beta_uniform": model.get("beta_uniform", 0.2),
        }
        if not defaults["name"]:
            defaults["name"] = self.localization.translate("temperature_preset_custom")
        return defaults

    @staticmethod
    def _parse_grid_identifier(identifier: str) -> Optional[tuple[int, int]]:
        numeric = "".join(ch for ch in identifier if ch.isdigit())
        alpha = "".join(ch for ch in identifier if ch.isalpha())
        if not numeric or not alpha:
            return None
        try:
            row = int(numeric) - 1
            col = ord(alpha.upper()) - 65
        except ValueError:
            return None
        if row < 0 or col < 0:
            return None
        return row, col

    @staticmethod
    def _resolve_identifier(identifier: str, rows: int, cols: int) -> Optional[tuple[int, int]]:
        mapping = {
            "front_left": (0, 0),
            "front_right": (0, cols - 1),
            "back_left": (rows - 1, 0),
            "back_right": (rows - 1, cols - 1),
            "back": (rows - 1, cols // 2),
            "back_center": (rows - 1, cols // 2),
        }
        if identifier in mapping:
            return mapping[identifier]
        parsed = VisualRecommendationsDialog._parse_grid_identifier(identifier)
        if not parsed:
            return None
        row, col = parsed
        if row >= rows or col >= cols:
            return None
        return row, col

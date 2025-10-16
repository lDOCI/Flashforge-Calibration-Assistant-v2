#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Визуализации рекомендаций по регулировке стола для Qt-интерфейса.

Модуль реализует две фигуры matplotlib:
* ScrewAdjustmentVisualizer — анимация регулировки винтов с подсказками
* TapeLayoutVisualizer — схема наклейки скотча с легендой и инструкциями
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np
import matplotlib.animation as animation
import matplotlib.patches as patches
from matplotlib.figure import Figure

from calibration.hardware.screw import RotationDirection

Translator = Callable[[str, Optional[str]], str]

DEGREES_PER_TOOTH = 22.5


class ScrewAdjustmentVisualizer:
    """
    Создает фигуру с визуализацией винтов и анимацией дуг.

    Интерфейс совместим с Qt: фон прозрачный, blit отключен, ссылка на анимацию
    сохраняется внутри Figure.
    """

    def __init__(
        self,
        *,
        translator: Optional[Translator],
        is_dark_theme: bool,
        show_minutes: bool,
        show_degrees: bool,
        screw_mode: str = "hold_nut",
    ) -> None:
        self._tr = translator or (lambda key, default=None: default or key)
        self.is_dark_theme = is_dark_theme
        self.show_minutes = show_minutes
        self.show_degrees = show_degrees
        self.screw_mode = screw_mode
        self._corner_positions: Dict[str, Tuple[float, float]] = {}
        self._corner_colors = {
            'front_left': '#3498db',
            'front_right': '#2ecc71',
            'back_left': '#e74c3c',
            'back_right': '#f39c12',
        }
        self._belt_positions: Dict[str, Tuple[float, float]] = {}
        self.animation: Optional[animation.FuncAnimation] = None

    def set_mode(self, screw_mode: str) -> None:
        self.screw_mode = screw_mode

    def _mode_caption(self) -> str:
        if self.screw_mode == "hold_screw":
            mode_text = self._tr("settings_tab.screw_mode_hold_screw", "Turn nuts, hold screws")
        else:
            mode_text = self._tr("settings_tab.screw_mode_hold_nut", "Turn screws, hold nuts")
        template = self._tr("visual_rec.screw_mode_caption", "Mode: {mode}")
        try:
            return template.format(mode=mode_text)
        except (KeyError, IndexError, ValueError):
            return f"{template} {mode_text}"

    def _setup_axes(self) -> Tuple[Figure, object, float, str, str, str, str]:
        bed_size = 70.0
        fig = Figure(figsize=(12.0, 9.6), dpi=110)
        ax = fig.add_subplot(111)
        offset = bed_size / 3.0
        self._corner_positions = {
            'front_left': (-offset, -offset),
            'front_right': (offset, -offset),
            'back_left': (-offset, offset),
            'back_right': (offset, offset),
        }
        self._belt_positions = {
            'front_left': self._corner_positions['front_left'],
            'front_right': self._corner_positions['front_right'],
            'back': (0.0, offset),
        }

        if self.is_dark_theme:
            fig.patch.set_facecolor('#0f172a')
            ax.set_facecolor('#0f172a')
            text_color = '#F8FAFC'
            panel_bg = '#172554'
            accent_color = '#334155'
            edge_color = '#64748b'
        else:
            fig.patch.set_facecolor('#f8fafc')
            ax.set_facecolor('#f8fafc')
            text_color = '#1e293b'
            panel_bg = '#e2e8f0'
            accent_color = '#cbd5f5'
            edge_color = '#475569'

        bed = patches.Rectangle(
            (-bed_size / 2, -bed_size / 2),
            bed_size,
            bed_size,
            fill=True,
            facecolor=panel_bg,
            edgecolor=edge_color,
            linewidth=2,
        )
        ax.add_patch(bed)
        return fig, ax, bed_size, text_color, panel_bg, accent_color, edge_color

    # ------------------------------------------------------------------ public API
    def create_adjustment_figure(
        self,
        adjustments: Dict[str, Tuple[float, RotationDirection]],
    ) -> Figure:
        """
        Строит фигуру регулировки.

        Args:
            adjustments: словарь вида {угол: (минуты, направление вращения)}.
        """
        fig, ax, bed_size, text_color, panel_bg, accent_color, edge_color = self._setup_axes()

        ax.set_title(
            self._mode_caption(),
            color=text_color,
            fontsize=12,
            fontweight='bold',
            pad=12,
        )

        animation_data: List[Dict[str, object]] = []

        for corner, (x, y) in self._corner_positions.items():
            base_circle = patches.Circle(
                (x, y),
                bed_size / 10,
                fill=True,
                facecolor=accent_color,
                edgecolor=edge_color,
                linewidth=1,
                alpha=0.55,
                zorder=1,
            )
            ax.add_patch(base_circle)

            corner_label = self._tr(f"neo_ui.visual.corners.{corner}", corner.replace("_", " ").title())
            ax.text(
                x,
                y - bed_size / 6,
                corner_label.replace(" ", "\n"),
                ha='center',
                va='center',
                fontsize=10,
                fontweight='bold',
                color=text_color,
                bbox=dict(facecolor=panel_bg, alpha=0.7, boxstyle='round'),
            )

            data = adjustments.get(corner)
            if not data:
                normal_text = self._tr("visual_rec.normal", "Normal")
                ax.text(
                    x,
                    y,
                    "✓",
                    ha='center',
                    va='center',
                    fontsize=20,
                    fontweight='bold',
                    color='#7f8c8d',
                )
                ax.text(
                    x,
                    y + bed_size / 6,
                    normal_text,
                    ha='center',
                    va='center',
                    fontsize=9,
                    color='#7f8c8d',
                )
                continue

            minutes, direction = data
            minutes = float(minutes or 0.0)
            if minutes <= 0.0:
                normal_text = self._tr("visual_rec.normal", "Normal")
                ax.text(
                    x,
                    y,
                    "✓",
                    ha='center',
                    va='center',
                    fontsize=20,
                    fontweight='bold',
                    color='#7f8c8d',
                )
                ax.text(
                    x,
                    y + bed_size / 6,
                    normal_text,
                    ha='center',
                    va='center',
                    fontsize=9,
                    color='#7f8c8d',
                )
                continue

            actual_clockwise = direction == RotationDirection.CLOCKWISE
            user_clockwise = actual_clockwise if self.screw_mode != "hold_screw" else not actual_clockwise
            wedge_color = '#fb7185' if user_clockwise else '#34d399'
            rotation_symbol = '↻' if user_clockwise else '↺'
            start_angle = 90.0
            total_degrees = float(minutes) * 6.0
            end_angle = start_angle - total_degrees if user_clockwise else start_angle + total_degrees

            wedge = patches.Wedge(
                (x, y),
                bed_size / 8,
                start_angle,
                start_angle,
                color=wedge_color,
                alpha=0.5,
                zorder=3,
            )
            ax.add_patch(wedge)
            animation_data.append(
                {
                    'wedge': wedge,
                    'start_angle': start_angle,
                    'end_angle': end_angle,
                    'clockwise': user_clockwise,
                }
            )

            info_lines: List[str] = []
            if self.show_minutes:
                info_lines.append(
                    self._tr("visual_rec.minutes_short", "{value:.0f} мин").format(value=minutes)
                )
            if self.show_degrees:
                info_lines.append(
                    self._tr("visual_rec.degrees_short", "{value:.0f}°").format(value=total_degrees)
                )
            direction_text = self._tr(
                "visual_rec.counterclockwise" if not user_clockwise else "visual_rec.clockwise",
                "Counterclockwise" if not user_clockwise else "Clockwise",
            )
            info_lines.append(direction_text)

            ax.text(
                x,
                y,
                rotation_symbol,
                ha='center',
                va='center',
                fontsize=22,
                fontweight='bold',
                color=wedge_color,
            )
            info_offset = bed_size / 2.6
            info_x = x + (info_offset if x >= 0 else -info_offset)
            info_align = 'left' if x >= 0 else 'right'
            ax.text(
                info_x,
                y,
                "\n".join(info_lines),
                ha=info_align,
                va='center',
                fontsize=9,
                linespacing=1.25,
                color=wedge_color,
                bbox=dict(
                    facecolor=panel_bg,
                    edgecolor=edge_color,
                    linewidth=0.8,
                    alpha=0.9,
                ),
            )

        if animation_data:
            anim = self._build_animation(
                fig,
                animation_data,
                frames=60,
                interval=60,
                repeat_delay=2000,
            )
            if anim:
                fig.animation = anim
                self.animation = anim

        margin = 4.0
        info_offset = bed_size / 2.6
        x_extent = bed_size / 2 + margin + info_offset + 0.8
        ax.set_xlim(-x_extent, x_extent)
        ax.set_ylim(-bed_size / 2 - margin, bed_size / 2 + margin)
        ax.set_aspect('equal')
        ax.axis('off')
        fig.subplots_adjust(left=0.08, right=0.92, top=0.86, bottom=0.08)
        return fig

    def create_belt_animation_figure(
        self,
        adjustments: Dict[str, Dict[str, object]],
    ) -> Figure:
        """
        Построение фигуры для синхронизации валов с анимацией дуг (аналогично винтам).

        Args:
            adjustments: словарь вида {положение: {'teeth': int, 'direction': str, 'delta_mm': float}}
        """
        fig, ax, bed_size, text_color, panel_bg, accent_color, edge_color = self._setup_axes()
        ax.set_title("", color=text_color)

        animation_data: List[Dict[str, object]] = []

        for corner, (x, y) in self._belt_positions.items():
            gear = patches.RegularPolygon(
                (x, y),
                numVertices=12,
                radius=bed_size / 10,
                orientation=np.deg2rad(15.0),
                facecolor=accent_color,
                edgecolor=edge_color,
                linewidth=1.2,
                alpha=0.8,
                zorder=1,
            )
            hub = patches.Circle(
                (x, y),
                bed_size / 20,
                facecolor=panel_bg,
                edgecolor=edge_color,
                linewidth=1.0,
                zorder=2,
            )
            ax.add_patch(gear)
            ax.add_patch(hub)

            label_key = 'back_center' if corner == 'back' else corner
            corner_label = self._tr(f"visual_rec.{label_key}", None)
            if not corner_label or corner_label == f"visual_rec.{label_key}":
                corner_label = self._tr(
                    f"neo_ui.visual.corners.{label_key}",
                    label_key.replace("_", " ").title(),
                )
            ax.text(
                x,
                y - bed_size / 6,
                corner_label.replace(" ", "\n"),
                ha='center',
                va='center',
                fontsize=10,
                fontweight='bold',
                color=text_color,
                bbox=dict(facecolor=panel_bg, alpha=0.7, boxstyle='round'),
            )

            data = adjustments.get(corner)
            if not data:
                ok_text = self._tr("visual_rec.belt_action_ok", "In tolerance")
                ax.text(
                    x,
                    y,
                    "✓",
                    ha='center',
                    va='center',
                    fontsize=20,
                    fontweight='bold',
                    color='#7f8c8d',
                )
                ax.text(
                    x,
                    y + bed_size / 6,
                    ok_text,
                    ha='center',
                    va='center',
                    fontsize=9,
                    color='#7f8c8d',
                )
                continue

            teeth = int(abs(int(data.get('teeth', 0) or 0)))
            if teeth <= 0:
                ok_text = self._tr("visual_rec.belt_action_ok", "In tolerance")
                ax.text(
                    x,
                    y,
                    "✓",
                    ha='center',
                    va='center',
                    fontsize=20,
                    fontweight='bold',
                    color='#7f8c8d',
                )
                ax.text(
                    x,
                    y + bed_size / 6,
                    ok_text,
                    ha='center',
                    va='center',
                    fontsize=9,
                    color='#7f8c8d',
                )
                continue

            direction_token = str(data.get('direction', 'counterclockwise')).lower()
            clockwise = direction_token in {'clockwise', 'down', 'cw'}

            wedge_color = '#fb7185' if clockwise else '#34d399'
            rotation_symbol = '↻' if clockwise else '↺'
            start_angle = 90.0
            total_degrees = min(float(teeth) * DEGREES_PER_TOOTH, 270.0)
            end_angle = start_angle - total_degrees if clockwise else start_angle + total_degrees

            wedge = patches.Wedge(
                (x, y),
                bed_size / 8,
                start_angle,
                start_angle,
                color=wedge_color,
                alpha=0.5,
                zorder=3,
            )
            ax.add_patch(wedge)
            animation_data.append(
                {
                    'wedge': wedge,
                    'start_angle': start_angle,
                    'end_angle': end_angle,
                    'clockwise': clockwise,
                }
            )

            info_lines: List[str] = []
            info_lines.append(
                self._tr("visual_rec.belt_teeth_count", "Teeth to move: {count}").format(count=teeth)
            )
            delta_mm = float(data.get('delta_mm') or 0.0)
            if delta_mm > 0.0:
                info_lines.append(
                    self._tr("visual_rec.spot_height_diff", "{value:.2f} mm").format(value=delta_mm)
                )
            direction_text = self._tr(
                "visual_rec.belt_action_loosen" if clockwise else "visual_rec.belt_action_tighten",
                "Rotate clockwise" if clockwise else "Rotate counterclockwise",
            )
            info_lines.append(direction_text)

            ax.text(
                x,
                y,
                str(teeth),
                ha='center',
                va='center',
                fontsize=18,
                fontweight='bold',
                color=wedge_color,
            )
            info_offset = bed_size / 2.6
            info_x = x + (info_offset if x >= 0 else -info_offset)
            info_align = 'left' if x >= 0 else 'right'
            ax.text(
                info_x,
                y,
                "\n".join(info_lines),
                ha=info_align,
                va='center',
                fontsize=9,
                linespacing=1.25,
                color=wedge_color,
                bbox=dict(
                    facecolor=panel_bg,
                    edgecolor=edge_color,
                    linewidth=0.8,
                    alpha=0.9,
                ),
            )

        if animation_data:
            anim = self._build_animation(
                fig,
                animation_data,
                frames=60,
                interval=120,
                repeat_delay=2000,
            )
            if anim:
                fig.animation = anim
                self.animation = anim

        margin = 4.0
        info_offset = bed_size / 2.6
        x_extent = bed_size / 2 + margin + info_offset + 0.8
        legend_y = -bed_size / 2 - margin + 0.6
        ax.set_xlim(-x_extent, x_extent)
        ax.set_ylim(-bed_size / 2 - margin, bed_size / 2 + margin)
        ax.set_aspect('equal')
        ax.axis('off')
        fig.subplots_adjust(left=0.08, right=0.92, top=0.86, bottom=0.08)
        return fig

    def create_teeth_figure(
        self,
        adjustments: Dict[str, Dict[str, object]],
    ) -> Figure:
        """
        Строит фигуру регулировки Z-валов по количеству зубьев.

        Args:
            adjustments: словарь вида {положение: {'teeth': int, 'direction': str}}.
        """
        fig, ax, bed_size, text_color, panel_bg, accent_color, edge_color = self._setup_axes()
        ax.set_title("", color=text_color)

        animation_data: List[Dict[str, object]] = []

        for corner, (x, y) in self._belt_positions.items():
            gear = patches.RegularPolygon(
                (x, y),
                numVertices=12,
                radius=bed_size / 10,
                orientation=np.deg2rad(15.0),
                facecolor=accent_color,
                edgecolor=edge_color,
                linewidth=1.2,
                alpha=0.8,
                zorder=1,
            )
            hub = patches.Circle(
                (x, y),
                bed_size / 20,
                facecolor=panel_bg,
                edgecolor=edge_color,
                linewidth=1.0,
                zorder=2,
            )
            ax.add_patch(gear)
            ax.add_patch(hub)

            label_key = 'back_center' if corner == 'back' else corner
            corner_label = self._tr(f"visual_rec.{label_key}", None)
            if not corner_label or corner_label == f"visual_rec.{label_key}":
                corner_label = self._tr(
                    f"neo_ui.visual.corners.{label_key}",
                    label_key.replace("_", " ").title(),
                )
            ax.text(
                x,
                y - bed_size / 6,
                corner_label.replace(" ", "\n"),
                ha='center',
                va='center',
                fontsize=10,
                fontweight='bold',
                color=text_color,
                bbox=dict(facecolor=panel_bg, alpha=0.7, boxstyle='round'),
            )

            data = adjustments.get(corner)
            if not data:
                ok_text = self._tr("visual_rec.belt_action_ok", "In tolerance")
                ax.text(
                    x,
                    y,
                    "✓",
                    ha='center',
                    va='center',
                    fontsize=20,
                    fontweight='bold',
                    color='#7f8c8d',
                )
                ax.text(
                    x,
                    y + bed_size / 6,
                    ok_text,
                    ha='center',
                    va='center',
                    fontsize=9,
                    color='#7f8c8d',
                )
                continue

            teeth = int(abs(int(data.get('teeth', 0) or 0)))
            if teeth <= 0:
                ok_text = self._tr("visual_rec.belt_action_ok", "In tolerance")
                ax.text(
                    x,
                    y,
                    "✓",
                    ha='center',
                    va='center',
                    fontsize=20,
                    fontweight='bold',
                    color='#7f8c8d',
                )
                ax.text(
                    x,
                    y + bed_size / 6,
                    ok_text,
                    ha='center',
                    va='center',
                    fontsize=9,
                    color='#7f8c8d',
                )
                continue

            direction_token = str(data.get('direction', 'counterclockwise')).lower()
            clockwise = direction_token in {'clockwise', 'down', 'cw'}

            wedge_color = '#fb7185' if clockwise else '#34d399'
            rotation_symbol = '↻' if clockwise else '↺'
            start_angle = 90.0
            total_degrees = min(float(teeth) * DEGREES_PER_TOOTH, 270.0)
            end_angle = start_angle - total_degrees if clockwise else start_angle + total_degrees

            wedge = patches.Wedge(
                (x, y),
                bed_size / 8,
                start_angle,
                start_angle,
                color=wedge_color,
                alpha=0.5,
                zorder=3,
            )
            ax.add_patch(wedge)
            animation_data.append(
                {
                    'wedge': wedge,
                    'start_angle': start_angle,
                    'end_angle': end_angle,
                    'clockwise': clockwise,
                }
            )

            info_lines: List[str] = []
            info_lines.append(
                self._tr("visual_rec.belt_teeth_count", "Teeth to move: {count}").format(count=teeth)
            )
            delta_mm = float(data.get('delta_mm') or 0.0)
            if delta_mm > 0.0:
                info_lines.append(
                    self._tr("visual_rec.spot_height_diff", "{value:.2f} mm").format(value=delta_mm)
                )
            direction_text = self._tr(
                "visual_rec.belt_action_loosen" if clockwise else "visual_rec.belt_action_tighten",
                "Rotate clockwise" if clockwise else "Rotate counterclockwise",
            )
            info_lines.append(direction_text)

            ax.text(
                x,
                y,
                rotation_symbol,
                ha='center',
                va='center',
                fontsize=22,
                fontweight='bold',
                color=wedge_color,
            )
            info_offset = bed_size / 2.6
            info_x = x + (info_offset if x >= 0 else -info_offset)
            info_align = 'left' if x >= 0 else 'right'
            ax.text(
                info_x,
                y,
                "\n".join(info_lines),
                ha=info_align,
                va='center',
                fontsize=9,
                linespacing=1.25,
                color=wedge_color,
                bbox=dict(
                    facecolor=panel_bg,
                    edgecolor=edge_color,
                    linewidth=0.8,
                    alpha=0.9,
                ),
            )

        if animation_data:
            anim = self._build_animation(
                fig,
                animation_data,
                frames=60,
                interval=120,
                repeat_delay=2000,
            )
            if anim:
                fig.animation = anim
                self.animation = anim

        margin = 4.0
        info_offset = bed_size / 2.6
        x_extent = bed_size / 2 + margin + info_offset + 0.8
        legend_y = -bed_size / 2 - margin + 0.6
        legend_blocks = [
            self._tr(
                "visual_rec.belt_instruction_overview",
                "Sequence:\n1. Power off the printer\n2. Lay the printer on its back\n3. Loosen the tensioner lock bolts before turning the screws",
            ),
            self._tr(
                "visual_rec.belt_instruction_finish",
                "After adjustment:\n• Re-tension the belts\n• Return the printer upright\n• Re-run the bed mesh",
            ),
            self._tr(
                "visual_rec.belt_extra_tip",
                "Tip: release the synchronising belt clamp before turning the shaft, then tighten it again.",
            ),
        ]
        legend_text = "\n\n".join(block for block in legend_blocks if block)
        ax.text(
            0.0,
            legend_y,
            legend_text,
            ha='center',
            va='top',
            fontsize=9,
            linespacing=1.35,
            color=text_color,
            bbox=dict(
                facecolor=panel_bg,
                edgecolor=edge_color,
                linewidth=0.8,
                alpha=0.9,
            ),
        )
        ax.set_xlim(-x_extent, x_extent)
        ax.set_ylim(-bed_size / 2 - margin, bed_size / 2 + margin)
        ax.set_aspect('equal')
        ax.axis('off')
        fig.subplots_adjust(left=0.08, right=0.92, top=0.86, bottom=0.08)
        return fig

    # ------------------------------------------------------------------ internals
    @staticmethod
    def _build_animation(
        fig: Figure,
        entries: Iterable[Dict[str, object]],
        *,
        frames: int = 20,
        interval: int = 50,
        repeat_delay: int = 1000,
    ) -> Optional[animation.FuncAnimation]:
        items = list(entries)
        if not items:
            return None

        total_frames = max(frames, 2)

        def init():
            patches_to_update = []
            for data in items:
                wedge: patches.Wedge = data['wedge']  # type: ignore[assignment]
                start = float(data['start_angle'])    # type: ignore[arg-type]
                wedge.set_theta1(start)
                wedge.set_theta2(start)
                patches_to_update.append(wedge)
            return patches_to_update

        def update(frame: int):
            divisor = max(total_frames - 1, 1)
            progress = frame / divisor
            patches_to_update = []
            for data in items:
                wedge: patches.Wedge = data['wedge']  # type: ignore[assignment]
                start = float(data['start_angle'])    # type: ignore[arg-type]
                end = float(data['end_angle'])        # type: ignore[arg-type]
                clockwise = bool(data['clockwise'])
                current = start + (end - start) * progress
                if clockwise:
                    wedge.set_theta1(current)
                else:
                    wedge.set_theta2(current)
                patches_to_update.append(wedge)
            return patches_to_update

        return animation.FuncAnimation(
            fig,
            update,
            init_func=init,
            frames=total_frames,
            interval=interval,
            blit=False,
            repeat=True,
            repeat_delay=repeat_delay,
        )


@dataclass(frozen=True)
class TapeCell:
    row: int
    col: int
    layers: int
    delta: float


class TapeLayoutVisualizer:
    """Визуализация схемы наклейки скотча."""

    def __init__(self, *, translator: Optional[Translator], is_dark_theme: bool) -> None:
        self._tr = translator or (lambda key, default=None: default or key)
        self.is_dark_theme = is_dark_theme

    def create_tape_figure(
        self,
        mesh: np.ndarray,
        cells: Iterable[TapeCell],
        *,
        threshold_mm: Optional[float] = None,
        tape_thickness: Optional[float] = None,
    ) -> Figure:
        cells = [cell for cell in cells if cell.layers > 0]
        rows, cols = mesh.shape

        fig = Figure(figsize=(8.0, 6.0), dpi=110)
        if self.is_dark_theme:
            fig.patch.set_facecolor('#0f172a')
            ax_bg = '#172554'
            text_color = '#F8FAFC'
            grid_color = '#2d3f73'
            outline_color = '#64748b'
        else:
            fig.patch.set_facecolor('#f8fafc')
            ax_bg = '#e2e8f0'
            text_color = '#1f2937'
            grid_color = '#cbd5f5'
            outline_color = '#475569'

        ax = fig.add_subplot(111)
        ax.set_facecolor(ax_bg)
        ax.axis('off')
        ax.set_aspect('equal')

        inner_rect = patches.Rectangle(
            (-0.55, -0.55),
            cols + 0.1,
            rows + 0.1,
            linewidth=0,
            facecolor=ax_bg,
            alpha=0.95,
        )
        ax.add_patch(inner_rect)

        outline = patches.Rectangle(
            (-0.5, -0.5),
            cols,
            rows,
            linewidth=1.6,
            edgecolor=outline_color,
            facecolor='none',
        )
        ax.add_patch(outline)

        for i in range(rows + 1):
            ax.axhline(i - 0.5, linestyle=':', linewidth=0.8, color=grid_color, alpha=0.55)
        for j in range(cols + 1):
            ax.axvline(j - 0.5, linestyle=':', linewidth=0.8, color=grid_color, alpha=0.55)

        for r in range(rows):
            ax.text(-0.9, r, str(r + 1), ha='center', va='center', fontsize=9, color=text_color)
        for c in range(cols):
            ax.text(c, -0.9, chr(65 + c), ha='center', va='center', fontsize=9, color=text_color)

        color_palette = {
            1: '#fde047',
            2: '#fb923c',
            3: '#f97316',
        }

        legend_entries: list[str] = []
        for idx, cell in enumerate(cells):
            face = color_palette.get(min(cell.layers, 3), '#EA580C')
            alpha = min(0.35 + 0.15 * cell.layers, 0.92)
            rect = patches.Rectangle(
                (cell.col - 0.4, cell.row - 0.4),
                0.8,
                0.8,
                facecolor=face,
                edgecolor='#EA580C',
                linewidth=1.4,
                alpha=alpha,
            )
            ax.add_patch(rect)

            ax.text(
                cell.col,
                cell.row,
                str(cell.layers),
                ha='center',
                va='center',
                fontsize=12,
                fontweight='bold',
                color=text_color,
            )

            coords = f"{cell.row + 1}{chr(65 + cell.col)}"
            info = (
                f"{coords} • "
                + self._tr("visual_rec.tape_layers_short", "{value}×").format(value=cell.layers)
                + " • "
                + self._tr("neo_ui.visual.delta", "Δ {value:.3f} mm").format(value=float(cell.delta))
            )
            legend_entries.append(info)

        label_kwargs = dict(fontsize=8, color=text_color, ha='right', va='top')
        ax.text(-0.45, -0.55, self._tr("neo_ui.visual.corners.front_left", "Front left"), **label_kwargs)
        ax.text(
            cols - 0.05,
            -0.55,
            self._tr("neo_ui.visual.corners.front_right", "Front right"),
            ha='left',
            va='top',
            fontsize=8,
            color=text_color,
        )
        ax.text(
            -0.45,
            rows - 0.05,
            self._tr("neo_ui.visual.corners.back_left", "Back left"),
            ha='right',
            va='bottom',
            fontsize=8,
            color=text_color,
        )
        ax.text(
            cols - 0.05,
            rows - 0.05,
            self._tr("neo_ui.visual.corners.back_right", "Back right"),
            ha='left',
            va='bottom',
            fontsize=8,
            color=text_color,
        )

        if not cells:
            ax.text(
                cols / 2,
                rows / 2,
                self._tr("visual_rec.tape_no_adjustment", "No tape correction required"),
                ha='center',
                va='center',
                fontsize=12,
                fontweight='bold',
                color=text_color,
            )
        else:
            # no explicit title to keep layout compact
            pass

        pad = max(0.8, cols * 0.08)
        if legend_entries:
            info_padding = 0.4
            legend_width = max(2.6, max(len(entry) for entry in legend_entries) * 0.18 + 1.2)
            legend_height = len(legend_entries) * 0.85 + 0.6
            legend_box = patches.Rectangle(
                (cols - 0.5 + pad + info_padding, (rows - legend_height) / 2),
                legend_width,
                legend_height,
                linewidth=1.0,
                edgecolor=outline_color,
                facecolor=ax_bg,
                alpha=0.95,
            )
            ax.add_patch(legend_box)
            ax.text(
                cols - 0.5 + pad + info_padding + 0.3,
                (rows - legend_height) / 2 + 0.3,
                "\n".join(legend_entries),
                ha='left',
                va='top',
                fontsize=10,
                color=text_color,
                linespacing=1.35,
            )

        ax.set_xlim(-0.5 - pad, cols - 0.5 + pad)
        ax.set_ylim(-0.5 - pad, rows - 0.5 + pad)
        fig.subplots_adjust(left=0.08, right=0.94, top=0.9, bottom=0.08)
        return fig

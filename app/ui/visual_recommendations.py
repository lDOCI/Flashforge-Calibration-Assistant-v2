#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Визуализации рекомендаций по регулировке стола для Qt-интерфейса.

Модуль реализует две фигуры matplotlib:
* ScrewAdjustmentVisualizer — анимация заполнения кружков винтов
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


class ScrewAdjustmentVisualizer:
    """
    Создает фигуру с визуализацией винтов где серые кружки заполняются цветом.
    Анимация показывает прогресс регулировки.
    """

    def __init__(
        self,
        *,
        translator: Optional[Translator],
        is_dark_theme: bool,
        show_minutes: bool,
        show_degrees: bool,
    ) -> None:
        self._tr = translator or (lambda key, default=None: default or key)
        self.is_dark_theme = is_dark_theme
        self.show_minutes = show_minutes
        self.show_degrees = show_degrees
        self._corner_positions: Dict[str, Tuple[float, float]] = {
            'front_left': (-1.8, -1.8),
            'front_right': (1.8, -1.8),
            'back_left': (-1.8, 1.8),
            'back_right': (1.8, 1.8),
        }
        self._corner_colors = {
            'front_left': '#38BDF8',
            'front_right': '#34D399',
            'back_left': '#F97316',
            'back_right': '#F87171',
        }

    def create_adjustment_figure(
        self,
        adjustments: Dict[str, Tuple[float, RotationDirection]],
    ) -> Figure:
        """Строит фигуру регулировки с анимацией заполнения."""
        fig = Figure(figsize=(5.8, 4.8), dpi=110)
        fig.patch.set_alpha(0.0)
        ax = fig.add_subplot(111)
        ax.set_facecolor('none')
        ax.axis('off')
        ax.set_aspect('equal')

        text_color = '#F8FAFC' if self.is_dark_theme else '#1E293B'
        panel_fill = '#1F2933' if self.is_dark_theme else '#F1F5F9'
        gray_color = '#64748B'

        # Background frame
        frame = patches.Rectangle(
            (-2.6, -2.6), 5.2, 5.2,
            fill=False, linewidth=2.2, linestyle='-',
            edgecolor='#64748B' if self.is_dark_theme else '#94A3B8',
        )
        ax.add_patch(frame)

        # Legend
        legend_text = self._tr(
            "neo_ui.visual.screw.legend",
            "• По часовой стрелке - опускает угол\n"
            "• Против часовой - поднимает угол\n"
            "• Заполнение показывает величину поворота",
        )
        legend_box = patches.FancyBboxPatch(
            (-2.6, -3.4), 5.2, 1.2,
            boxstyle='round,pad=0.35', linewidth=0,
            facecolor=panel_fill, alpha=0.9,
        )
        ax.add_patch(legend_box)
        ax.text(0.0, -2.8, legend_text, ha='center', va='center',
                fontsize=9, color=text_color, linespacing=1.4)

        # Title
        title = self._tr("neo_ui.visual.screw.figure_title", "Регулировка винтов стола")
        if title:
            ax.text(0.0, 2.9, title, ha='center', va='center',
                    fontsize=12, fontweight='bold', color=text_color)

        # Список для хранения wedges для анимации
        animation_data: List[Dict] = []

        for corner, (x, y) in self._corner_positions.items():
            base_color = self._corner_colors.get(corner, '#94A3B8')
            
            # Рисуем серый фоновый круг (полный)
            background_circle = patches.Circle(
                (x, y), radius=0.7,
                facecolor=gray_color,
                edgecolor='#1E1E1E' if self.is_dark_theme else '#111827',
                linewidth=1.2,
                alpha=0.3,
                zorder=1,
            )
            ax.add_patch(background_circle)

            # Подпись угла
            label = self._tr(
                f"neo_ui.visual.corners.{corner}",
                corner.replace("_", " ").title()
            )
            ax.text(x, y - 1.1, label, ha='center', va='center',
                    fontsize=10, fontweight='bold', color=text_color,
                    bbox=dict(facecolor=panel_fill, edgecolor='#00000022',
                             boxstyle='round,pad=0.25'))

            # Проверяем нужна ли регулировка
            data = adjustments.get(corner)
            if not data:
                # Нет регулировки - показываем OK
                ax.text(x, y, "OK", ha='center', va='center',
                        fontsize=12, fontweight='bold', color='#22C55E',
                        zorder=5)
                continue

            minutes, direction = data
            if minutes is None or minutes <= 0:
                ax.text(x, y, "OK", ha='center', va='center',
                        fontsize=12, fontweight='bold', color='#22C55E',
                        zorder=5)
                continue

            # Определяем параметры заполнения
            clockwise = direction == RotationDirection.CLOCKWISE
            
            # Вычисляем угол заполнения (начинаем сверху - 90°)
            # Максимум 360° для полного оборота
            degrees = min((minutes / 60.0) * 360.0, 360)
            
            if clockwise:
                # По часовой: начинаем с 90° и идём против часовой стрелки (уменьшаем угол)
                start_angle = 90
                end_angle = 90 - degrees
            else:
                # Против часовой: начинаем с 90° и идём по часовой стрелке (увеличиваем угол)
                start_angle = 90
                end_angle = 90 + degrees

            print(f"DEBUG Viz: {corner} - {minutes:.1f}min = {degrees:.1f}° | start={start_angle}° end={end_angle}° | {'CW' if clockwise else 'CCW'}")

            # Создаём wedge для заполнения (изначально невидимый - theta2 = theta1)
            fill_wedge = patches.Wedge(
                (x, y), 0.7,
                start_angle, start_angle,  # Изначально нулевая дуга
                facecolor=base_color,
                edgecolor=base_color,
                linewidth=0,
                alpha=0.8,
                zorder=2,
            )
            ax.add_patch(fill_wedge)

            # Сохраняем данные для анимации
            animation_data.append({
                "wedge": fill_wedge,
                "start": start_angle,
                "end": end_angle,
                "color": base_color,
                "clockwise": clockwise,
            })

            # Информация о регулировке
            info_lines: List[str] = []
            
            # Стрелка направления (большая и заметная)
            arrow_symbol = "⟳" if not clockwise else "⟲"
            
            if self.show_minutes:
                info_lines.append(f"{arrow_symbol} {float(minutes):.1f} мин")
            elif self.show_degrees:
                info_lines.append(f"{arrow_symbol} {float(minutes * 6.0):.0f}°")
            else:
                info_lines.append(arrow_symbol)
            
            direction_text = self._tr(
                "neo_ui.visual.screw.counterclockwise" if not clockwise
                else "neo_ui.visual.screw.clockwise",
                "↑ Вверх" if not clockwise else "↓ Вниз",
            )
            info_lines.append(direction_text)

            bbox = dict(facecolor=panel_fill, edgecolor=base_color,
                       linewidth=1.5, boxstyle='round,pad=0.35')
            ax.text(x, y + 1.05, "\n".join(info_lines),
                    ha='center', va='center', fontsize=10,
                    fontweight='bold', color=text_color, bbox=bbox,
                    zorder=3)

        ax.set_xlim(-3.4, 3.4)
        ax.set_ylim(-3.6, 3.4)

        # Создаём анимацию если есть данные
        if animation_data:
            print(f"DEBUG Viz: Creating fill animation with {len(animation_data)} wedges")
            anim = self._build_fill_animation(fig, ax, animation_data)
            fig.animation = anim  # Сохраняем ссылку!
        else:
            print("DEBUG Viz: No animation data")

        return fig

    def _build_fill_animation(
        self,
        fig: Figure,
        ax,
        data: List[Dict],
    ) -> animation.FuncAnimation:
        """Создаёт анимацию заполнения кружков"""
        
        def update(frame: int):
            """Функция обновления кадра"""
            # frame идёт от 0 до 99
            progress = frame / 99.0  # 0.0 до 1.0
            
            artists = []
            for entry in data:
                wedge = entry["wedge"]
                start = entry["start"]
                end = entry["end"]
                
                # Вычисляем текущий угол заполнения
                current_theta2 = start + (end - start) * progress
                
                # Обновляем wedge
                wedge.set_theta1(start)
                wedge.set_theta2(current_theta2)
                artists.append(wedge)
            
            return artists

        # Создаём анимацию
        anim = animation.FuncAnimation(
            fig,
            update,
            frames=100,
            interval=30,  # 30ms между кадрами
            blit=False,   # КРИТИЧНО для Qt!
            repeat=True,
            repeat_delay=1500,  # Пауза перед повтором
        )
        
        print(f"DEBUG Viz: Fill animation created - frames=100, interval=30ms")
        
        return anim


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

        fig = Figure(figsize=(6.4, 4.8), dpi=110)
        fig.patch.set_alpha(0.0)
        ax = fig.add_subplot(111)
        ax.set_facecolor('none')
        ax.axis('off')
        ax.set_aspect('equal')

        text_color = '#F8FAFC' if self.is_dark_theme else '#1E293B'
        grid_color = '#475569' if self.is_dark_theme else '#CBD5F5'
        outline_color = '#94A3B8' if self.is_dark_theme else '#475569'

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
            1: '#FDE68A',
            2: '#FDBA74',
            3: '#F97316',
        }

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
                color='#111827',
            )

            coords = f"{cell.row + 1}{chr(65 + cell.col)}"
            info = (
                f"{coords} • "
                + self._tr("neo_ui.visual.tape.layers_short", "{value}×").format(value=cell.layers)
                + " • "
                + self._tr("neo_ui.visual.delta", "Δ {value:.3f} mm").format(value=float(cell.delta))
            )
            ax.text(
                cols + 0.6,
                rows - idx * 0.4,
                info,
                ha='left',
                va='center',
                fontsize=9,
                color=text_color,
            )

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

        if cells:
            legend_handles = [
                patches.Patch(facecolor=color_palette[1], edgecolor='#EA580C', linewidth=1.0, label='1×'),
                patches.Patch(facecolor=color_palette[2], edgecolor='#EA580C', linewidth=1.0, label='2×'),
                patches.Patch(facecolor=color_palette[3], edgecolor='#EA580C', linewidth=1.0, label='3×+'),
            ]
            legend_labels = [
                self._tr("neo_ui.visual.tape.layers_short", "{value}×").format(value=1),
                self._tr("neo_ui.visual.tape.layers_short", "{value}×").format(value=2),
                self._tr("neo_ui.visual.tape.layers_short", "{value}×").format(value=3) + "+",
            ]
            legend = ax.legend(
                legend_handles,
                legend_labels,
                loc='upper left',
                bbox_to_anchor=(0.0, -0.18),
                frameon=False,
                ncol=3,
                fontsize=8,
            )
            for text in legend.get_texts():
                text.set_color(text_color)

            instructions = [
                self._tr(
                    "neo_ui.visual.hints.tape.threshold",
                    "Tape corrections trigger above {threshold:.2f} mm.",
                ).format(threshold=float(threshold_mm or 0.0)),
                self._tr("neo_ui.visual.hints.tape.step_1", "Use aluminium tape ≈0.06 mm thick"),
                self._tr("neo_ui.visual.hints.tape.step_2", "Apply tape exactly at the highlighted cells"),
                self._tr(
                    "neo_ui.visual.hints.tape.step_3",
                    "Number shows how many layers to stack",
                ),
                self._tr("neo_ui.visual.hints.tape.step_4", "Re-measure the mesh after applying tape"),
            ]
            if tape_thickness is not None:
                instructions.insert(
                    1,
                    self._tr(
                        "neo_ui.visual.hints.tape.thickness",
                        "Tape thickness used: {thickness:.2f} mm.",
                    ).format(thickness=float(tape_thickness)),
                )
            box = patches.FancyBboxPatch(
                (cols + 0.4, -0.5),
                2.8,
                3.0,
                boxstyle='round,pad=0.35',
                linewidth=0,
                facecolor='#1F2933' if self.is_dark_theme else '#E2E8F0',
                alpha=0.9,
            )
            ax.add_patch(box)
            text_lines = "\n".join(instructions)
            ax.text(
                cols + 1.8,
                1.0,
                text_lines,
                ha='center',
                va='center',
                fontsize=8,
                color='#F8FAFC' if self.is_dark_theme else '#1E293B',
            )
            title = self._tr("neo_ui.visual.tape.figure_title", "").format(count=len(cells))
        else:
            ax.text(
                cols / 2,
                rows / 2,
                self._tr("neo_ui.visual.tape.no_adjustment", "No tape correction required"),
                ha='center',
                va='center',
                fontsize=12,
                fontweight='bold',
                color=text_color,
            )
            title = self._tr("neo_ui.visual.tape.scheme_title", "Tape layout")

        if not title:
            title = self._tr("neo_ui.visual.tape.scheme_title", "Tape layout")
        ax.set_title(title, color=text_color, fontsize=12, fontweight='bold')

        ax.set_xlim(-1.2, cols + 3.3)
        ax.set_ylim(-1.2, rows + 1.5)
        fig.tight_layout()
        return fig
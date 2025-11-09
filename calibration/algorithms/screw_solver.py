#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для расчета оптимальных регулировок винтов
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
from ..hardware.bed import Bed
from ..hardware.screw import Screw, RotationDirection, ScrewConfig

@dataclass
class ScrewAdjustment:
    """Информация о регулировке винта"""

    corner: str
    minutes: float
    degrees: float
    direction: RotationDirection
    current_height: float
    target_height: float
    priority: int
    turns: float

class ScrewSolver:
    def __init__(self, bed: Bed, screw_config: Optional[ScrewConfig] = None):
        self.bed = bed
        self.screw_config = screw_config or ScrewConfig()
        self._build_screws()
        self._compute_corner_weights()

    def _build_screws(self) -> None:
        """(Re)create screw instances with the current configuration."""
        self.screws = {
            corner: Screw(corner, self.screw_config)
            for corner in self.bed.corners.keys()
        }

    def set_screw_config(self, screw_config: ScrewConfig) -> None:
        """Update screw configuration and rebuild screw instances."""
        self.screw_config = screw_config
        self._build_screws()
        self._compute_corner_weights()

    def _compute_corner_weights(self) -> None:
        """Pre-compute bilinear weight maps for each corner."""
        rows = self.bed.config.mesh_points_x
        cols = self.bed.config.mesh_points_y
        if rows < 2 or cols < 2:
            self.corner_weights = {
                corner: np.ones((rows, cols)) for corner in self.bed.corners.keys()
            }
            return

        row_factors = np.linspace(0, 1, rows).reshape(rows, 1)
        col_factors = np.linspace(0, 1, cols).reshape(1, cols)

        self.corner_weights = {
            'front_left': (1 - row_factors) * (1 - col_factors),
            'front_right': (1 - row_factors) * col_factors,
            'back_left': row_factors * (1 - col_factors),
            'back_right': row_factors * col_factors,
        }

        # Небольшая нормализация на случай накопления ошибок
        total_weight = sum(self.corner_weights.values())
        with np.errstate(divide='ignore', invalid='ignore'):
            correction = np.where(total_weight != 0, 1.0 / total_weight, 0)
        for corner in self.corner_weights:
            self.corner_weights[corner] = self.corner_weights[corner] * correction
        
    def _calculate_priority(self, deviation: float) -> int:
        """Определение приоритета регулировки на основе отклонения"""
        if deviation > 0.4:
            return 1  # Высший приоритет
        elif deviation > 0.3:
            return 2
        elif deviation > 0.2:
            return 3
        return 4  # Низший приоритет

    def calculate_adjustments(self, ideal_plane: np.ndarray) -> List[ScrewAdjustment]:
        """
        Расчет необходимых регулировок винтов
        
        Args:
            ideal_plane: Идеальная плоскость для выравнивания
            
        Returns:
            List[ScrewAdjustment]: Список регулировок, отсортированный по приоритету
        """
        adjustments = []
        
        for corner, (x, y) in self.bed.corners.items():
            current_height = self.bed.get_corner_height(corner)
            target_height = ideal_plane[x, y]
            
            screw = self.screws[corner]
            minutes, direction = screw.calculate_adjustment(current_height, target_height)
            
            if minutes > 0:
                deviation = abs(current_height - target_height)
                priority = self._calculate_priority(deviation)
                
                adjustments.append(ScrewAdjustment(
                    corner=corner,
                    minutes=minutes,
                    degrees=screw.minutes_to_degrees(minutes),
                    direction=direction,
                    current_height=current_height,
                    target_height=target_height,
                    priority=priority,
                    turns=minutes / 60.0,
                ))
                
        # Сортируем по приоритету и величине отклонения
        return sorted(
            adjustments,
            key=lambda x: (x.priority, -abs(x.current_height - x.target_height))
        )

    def simulate_adjustment(
        self,
        adjustment: ScrewAdjustment,
        base_mesh: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Симуляция применения одной регулировки

        Returns:
            np.ndarray: Новое состояние сетки после регулировки
        """
        mesh_source = self.bed.mesh_data if base_mesh is None else base_mesh
        if mesh_source is None:
            raise ValueError("Mesh data is not available for simulation")

        simulated_mesh = mesh_source.copy()

        screw = self.screws[adjustment.corner]
        height_change = screw.height_change_from_minutes(
            adjustment.minutes, adjustment.direction
        )

        weight_map = self.corner_weights.get(adjustment.corner)
        if weight_map is None:
            raise ValueError(f"Weight map for corner {adjustment.corner} not initialised")

        simulated_mesh += height_change * weight_map

        return simulated_mesh

    def simulate_sequence(
        self,
        adjustments: List[ScrewAdjustment],
        base_mesh: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Последовательная симуляция списка регулировок."""
        mesh_source = self.bed.mesh_data if base_mesh is None else base_mesh
        if mesh_source is None:
            raise ValueError("Mesh data is not available for simulation")

        simulated_mesh = mesh_source.copy()
        for adjustment in adjustments:
            simulated_mesh = self.simulate_adjustment(adjustment, simulated_mesh)
        return simulated_mesh

    def get_adjustment_sequence(self, adjustments: List[ScrewAdjustment]) -> List[str]:
        """
        Генерация последовательности инструкций для регулировки
        
        Returns:
            List[str]: Список инструкций в порядке выполнения
        """
        instructions = []
        
        for adj in adjustments:
            # Формируем текст направления
            direction_text = "по часовой стрелке" if adj.direction == RotationDirection.CLOCKWISE else "против часовой стрелки"
            
            # Формируем основную инструкцию
            instruction = (
                f"{adj.corner}:\n"
                f"• Текущая высота: {adj.current_height:.3f}мм\n"
                f"• Целевая высота: {adj.target_height:.3f}мм\n"
                f"• Поверните винт {direction_text} "
                f"на {int(round(adj.minutes))} минут ({int(round(adj.degrees))}°)\n"
            )
            
            # Добавляем пометку о приоритете если высокий
            if adj.priority == 1:
                instruction += "❗ Высокий приоритет - выполнить в первую очередь\n"
                
            instructions.append(instruction)
            
        return instructions

    def estimate_total_improvement(self, adjustments: List[ScrewAdjustment]) -> float:
        """
        Оценка общего улучшения после всех регулировок
        
        Returns:
            float: Уменьшение максимального отклонения в мм
        """
        current_mesh = self.bed.mesh_data
        simulated_mesh = self.simulate_sequence(adjustments, current_mesh)
            
        # Считаем улучшение
        current_deviation = np.max(np.abs(current_mesh - np.mean(current_mesh)))
        simulated_deviation = np.max(np.abs(simulated_mesh - np.mean(simulated_mesh)))
        
        return current_deviation - simulated_deviation

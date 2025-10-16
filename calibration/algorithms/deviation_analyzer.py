#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для анализа отклонений уровня стола
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import numpy as np
from ..hardware.bed import Bed
from ..hardware.screw import Screw, ScrewConfig, RotationDirection

@dataclass
class DeviationStats:
    """Статистика отклонений стола"""
    mean_height: float                   # Средняя высота
    max_deviation: float                # Максимальное отклонение
    corner_deviations: Dict[str, float]  # Отклонения в углах
    has_critical_deviation: bool         # Есть ли критические отклонения

@dataclass
class LevelingStage:
    """Определение необходимого этапа выравнивания"""
    needs_screw_adjustment: bool        # Нужна ли регулировка винтами
    can_use_screws: bool               # Можно ли исправить винтами
    needs_tape: bool                    # Нужен ли скотч
    max_corner_diff: float             # Максимальная разница между углами
    problematic_corners: List[str]      # Проблемные углы

class DeviationAnalyzer:
    def __init__(self, 
                bed: Bed,
                corner_averaging_size: int = 1,
                screw_threshold: float = 0.4,   # Порог для регулировки винтами
                tape_threshold: float = 0.2,
                screw_config: Optional[ScrewConfig] = None):   # Конфигурация винтов

        self.bed = bed
        self.corner_averaging_size = corner_averaging_size
        self.screw_threshold = screw_threshold
        self.tape_threshold = tape_threshold
        self.screw_config = screw_config or ScrewConfig()

        # Создаем винты для каждого угла
        self._build_screws()

    def _build_screws(self) -> None:
        self.screws = {
            corner: Screw(corner, self.screw_config)
            for corner in self.bed.corners.keys()
        }

    def set_screw_config(self, screw_config: ScrewConfig) -> None:
        self.screw_config = screw_config
        self._build_screws()

    def get_stats(self) -> DeviationStats:
        """Получение статистики отклонений"""
        mean_height, _, _ = self.bed.get_mesh_stats()
        
        # Рассчитываем отклонения в углах
        corner_deviations = {}
        for corner in self.bed.corners.keys():
            height = self.bed.get_corner_height(corner, self.corner_averaging_size)
            deviation = abs(height - mean_height)
            corner_deviations[corner] = deviation
            
        max_deviation = max(corner_deviations.values())
        has_critical = max_deviation > self.screw_threshold
        
        return DeviationStats(
            mean_height=mean_height,
            max_deviation=max_deviation,
            corner_deviations=corner_deviations,
            has_critical_deviation=has_critical
        )

    def analyze_leveling_stage(self) -> LevelingStage:
        """Определение необходимого этапа выравнивания"""
        stats = self.get_stats()
        
        # Находим максимальную разницу между углами
        heights = [self.bed.get_corner_height(corner, self.corner_averaging_size) 
                  for corner in self.bed.corners.keys()]
        max_corner_diff = max(heights) - min(heights)
        
        # Определяем проблемные углы
        problematic = [
            corner for corner, dev in stats.corner_deviations.items()
            if dev > self.tape_threshold
        ]
        
        # Определяем можно ли исправить винтами
        # Если отклонение больше максимальной регулировки винта - нельзя
        can_use_screws = max_corner_diff <= self.screw_config.max_adjust
        
        # Определяем необходимые шаги
        needs_screw_adjustment = stats.max_deviation > self.screw_threshold
        
        # Всегда пробуем применить скотч после винтов, если отклонение выше порога
        needs_tape = stats.max_deviation > self.tape_threshold
        
        return LevelingStage(
            needs_screw_adjustment=needs_screw_adjustment,
            can_use_screws=can_use_screws,
            needs_tape=needs_tape,
            max_corner_diff=max_corner_diff,
            problematic_corners=problematic
        )

    def get_ideal_plane(self) -> np.ndarray:
        """Расчет идеальной плоскости для выравнивания"""
        return self.bed.generate_ideal_plane()

    def estimate_bed_after_screw_adjustment(self) -> np.ndarray:
        """Предсказание состояния стола после регулировки винтами"""
        if self.bed.mesh_data is None:
            raise ValueError("Данные сетки не установлены")
            
        ideal_plane = self.get_ideal_plane()
        
        # Копируем текущие данные
        simulated_mesh = self.bed.mesh_data.copy()
        
        # Получаем необходимые действия для выравнивания
        actions = {}
        for corner, (x, y) in self.bed.corners.items():
            current_height = self.bed.get_corner_height(corner)
            target_height = ideal_plane[x, y]
            
            screw = self.screws[corner]
            minutes, direction = screw.calculate_adjustment(current_height, target_height)
            
            actions[corner] = (minutes, direction)
        
        # Применяем действия к симулированному столу
        for corner, (minutes, direction) in actions.items():
            x, y = self.bed.corners[corner]
            screw = self.screws[corner]
            height_change = screw.height_change_from_minutes(minutes, direction)
            
            # Создаем матрицу влияния - влияние будет убывать с увеличением расстояния от угла
            influence = np.zeros_like(self.bed.mesh_data, dtype=float)
            
            for i in range(self.bed.config.mesh_points_x):
                for j in range(self.bed.config.mesh_points_y):
                    # Рассчитываем расстояние от точки сетки до угла
                    distance = np.sqrt((i - x)**2 + (j - y)**2)
                    
                    # Расчет коэффициента влияния: больше влияние на ближайшие точки
                    max_distance = np.sqrt(
                        (self.bed.config.mesh_points_x - 1)**2 + 
                        (self.bed.config.mesh_points_y - 1)**2
                    )
                    influence[i, j] = max(0, 1 - (distance / max_distance))
            
            # Применяем изменение высоты с учетом матрицы влияния
            simulated_mesh += height_change * influence
            
        return simulated_mesh
        
    def find_optimal_strategy(self) -> dict:
        """Находит оптимальную стратегию выравнивания стола"""
        if self.bed.mesh_data is None:
            raise ValueError("Данные сетки не установлены")
            
        original_deviation = np.max(np.abs(self.bed.mesh_data - np.mean(self.bed.mesh_data)))
        
        # Стратегия: Максимальное выравнивание винтами
        bed_after_screws = self.estimate_bed_after_screw_adjustment()
        deviation_after_screws = np.max(np.abs(bed_after_screws - np.mean(bed_after_screws)))
        
        # Определим, нужен ли скотч
        needs_tape = deviation_after_screws > self.tape_threshold
        
        return {
            'original_deviation': original_deviation,
            'deviation_after_screws': deviation_after_screws,
            'needs_screws': original_deviation > self.screw_threshold,
            'needs_tape': needs_tape,
            'expected_final_deviation': deviation_after_screws if not needs_tape else self.tape_threshold,
            'simulated_bed_after_screws': bed_after_screws
        }

    def get_corner_actions(self) -> Dict[str, Tuple[float, RotationDirection]]:
        """Получение необходимых действий для углов"""
        ideal_plane = self.get_ideal_plane()
        actions = {}
        
        for corner, (x, y) in self.bed.corners.items():
            current_height = self.bed.get_corner_height(corner, self.corner_averaging_size)
            target_height = ideal_plane[x, y]
            
            screw = self.screws[corner]
            minutes, direction = screw.calculate_adjustment(current_height, target_height)
            
            actions[corner] = (minutes, direction)
            
        return actions

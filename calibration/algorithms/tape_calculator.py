#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для определения мест наклейки скотча
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
import numpy as np
from ..hardware.bed import Bed


@dataclass
class TapeSpot:
    """Точка наклейки скотча"""
    x: int                  # Координата X на сетке
    y: int                  # Координата Y на сетке
    layers: int            # Количество слоев скотча
    height_diff: float     # Разница высот для компенсации
    priority: int          # Приоритет (1 - самый высокий)
    area_size: float       # Примерный размер области в мм²


class TapeCalculator:
    def __init__(self, 
                 bed: Bed,
                 tape_thickness: float = 0.06,     # Толщина одного слоя скотча в мм
                 min_height_diff: float = 0.1):    # Минимальная разница для наклейки
        self.bed = bed
        self.tape_thickness = tape_thickness
        self.min_height_diff = min_height_diff

    def _calculate_priority(self, height_diff: float) -> int:
        """Определение приоритета на основе разницы высот"""
        if height_diff > 0.3:
            return 1
        elif height_diff > 0.2:
            return 2
        return 3

    def _is_near_screw(self, x: int, y: int) -> bool:
        """Проверка попадания точки непосредственно в позицию винта."""
        for corner_x, corner_y in self.bed.corners.values():
            if x == corner_x and y == corner_y:
                return True
        return False

    def _calculate_area_size(self, x: int, y: int, height_diff: float) -> float:
        """Расчет примерного размера области для скотча"""
        # Получаем физические размеры между точками сетки
        x_step, y_step = self.bed.get_mm_per_point()
        
        # Базовый размер - одна ячейка сетки
        base_area = x_step * y_step
        
        # Увеличиваем область если отклонение большое
        if height_diff > 0.3:
            return base_area * 1.5
        return base_area

    def find_low_spots(self, simulated_mesh: np.ndarray) -> List[TapeSpot]:
        """
        Поиск точек, где нужен скотч
        
        Args:
            simulated_mesh: Сетка после регулировки винтами
            
        Returns:
            List[TapeSpot]: Список точек для наклейки скотча
        """
        mean_height = np.mean(simulated_mesh)
        spots = []
        
        for x in range(self.bed.config.mesh_points_x):
            for y in range(self.bed.config.mesh_points_y):
                # Пропускаем точки рядом с винтами
                if self._is_near_screw(x, y):
                    continue
                    
                height = simulated_mesh[x, y]
                diff = mean_height - height
                
                # Если точка ниже средней высоты больше чем на порог
                if diff > self.min_height_diff:
                    # Рассчитываем количество слоев
                    layers = max(1, int(np.ceil(diff / self.tape_thickness)))
                    
                    spots.append(TapeSpot(
                        x=x,
                        y=y,
                        layers=layers,
                        height_diff=diff,
                        priority=self._calculate_priority(diff),
                        area_size=self._calculate_area_size(x, y, diff)
                    ))
        
        # Сортируем по приоритету и величине отклонения
        return sorted(spots, key=lambda s: (s.priority, -s.height_diff))

    def optimize_tape_layout(self, spots: List[TapeSpot]) -> List[TapeSpot]:
        """
        Оптимизация расположения скотча
        
        Args:
            spots: Исходный список точек
            
        Returns:
            List[TapeSpot]: Оптимизированный список
        """
        # Объединяем близкие точки
        optimized = []
        used = set()
        
        for spot in spots:
            if (spot.x, spot.y) in used:
                continue
                
            # Ищем близкие точки
            nearby = [
                s for s in spots
                if abs(s.x - spot.x) <= 1 and abs(s.y - spot.y) <= 1
                and (s.x, s.y) not in used
            ]
            
            if nearby:
                # Объединяем точки
                avg_diff = np.mean([s.height_diff for s in nearby])
                avg_layers = max(1, int(np.ceil(avg_diff / self.tape_thickness)))
                total_area = sum(s.area_size for s in nearby)
                
                # Выбираем центральную точку
                center = spot
                if len(nearby) > 1:
                    center = min(nearby, key=lambda s: 
                               abs(s.x - np.mean([n.x for n in nearby])) +
                               abs(s.y - np.mean([n.y for n in nearby])))
                
                optimized.append(TapeSpot(
                    x=center.x,
                    y=center.y,
                    layers=avg_layers,
                    height_diff=avg_diff,
                    priority=min(s.priority for s in nearby),
                    area_size=total_area
                ))
                
                # Отмечаем использованные точки
                used.update((s.x, s.y) for s in nearby)
            else:
                optimized.append(spot)
                used.add((spot.x, spot.y))
        
        return optimized

    def get_tape_instructions(self, spots: List[TapeSpot]) -> List[str]:
        """
        Генерация инструкций по наклейке скотча
        
        Returns:
            List[str]: Список инструкций
        """
        if not spots:
            return ["Коррекция скотчем не требуется"]
            
        instructions = []
        total_area = sum(spot.area_size for spot in spots)
        total_layers = sum(spot.layers for spot in spots)
        
        instructions.append(
            f"Необходимо наклеить скотч в {len(spots)} местах\n"
            f"Общая площадь: {total_area:.1f}мм²\n"
            f"Всего слоев: {total_layers}\n"
        )
        
        for spot in spots:
            # Конвертируем координаты сетки в буквенно-цифровое обозначение
            position = f"{spot.x+1}{chr(65+spot.y)}"
            
            instruction = (
                f"Точка {position}:\n"
                f"• Отклонение: {spot.height_diff:.3f}мм\n"
                f"• Наклейте {spot.layers} слой(я/ев) скотча\n"
                f"• Площадь: {spot.area_size:.1f}мм²"
            )
            
            if spot.priority == 1:
                instruction += "\n❗ Высокий приоритет"
                
            instructions.append(instruction)
            
        return instructions

    def estimate_improvement(self, spots: List[TapeSpot]) -> float:
        """
        Оценка улучшения после наклейки скотча

        Returns:
            float: Уменьшение максимального отклонения в мм
        """
        simulated_mesh = self.apply_spots(self.bed.mesh_data, spots)

        current_deviation = np.max(np.abs(self.bed.mesh_data - np.mean(self.bed.mesh_data)))
        simulated_deviation = np.max(np.abs(simulated_mesh - np.mean(simulated_mesh)))

        return current_deviation - simulated_deviation

    def apply_spots(self, base_mesh: np.ndarray, spots: List[TapeSpot]) -> np.ndarray:
        """Применяет указанные точки скотча к копии переданной сетки."""
        simulated_mesh = base_mesh.copy()

        for spot in spots:
            height_increase = spot.layers * self.tape_thickness

            x_start = max(0, spot.x - 1)
            x_end = min(self.bed.config.mesh_points_x, spot.x + 2)
            y_start = max(0, spot.y - 1)
            y_end = min(self.bed.config.mesh_points_y, spot.y + 2)

            simulated_mesh[x_start:x_end, y_start:y_end] += height_increase

        return simulated_mesh

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с моделью стола 3D-принтера
"""

from dataclasses import dataclass
from typing import Tuple, Dict, Optional
import numpy as np

@dataclass
class BedConfig:
    """Конфигурация стола"""
    size_x: float = 220.0       # Размер стола по X в мм
    size_y: float = 220.0       # Размер стола по Y в мм
    mesh_points_x: int = 5      # Количество точек сетки по X
    mesh_points_y: int = 5      # Количество точек сетки по Y

class Bed:
    """Модель стола принтера"""
    def __init__(self, config: BedConfig):
        self.config = config
        self.mesh_data: Optional[np.ndarray] = None
        
        # Определяем позиции углов стола (индексы в массиве mesh_data)
        # Важно: в сетке 5x5 последний индекс = 4
        self.corners = {
            'front_left': (0, 0),
            'front_right': (0, config.mesh_points_y - 1),
            'back_left': (config.mesh_points_x - 1, 0),
            'back_right': (config.mesh_points_x - 1, config.mesh_points_y - 1)
        }
        
    def set_mesh_data(self, data: np.ndarray) -> None:
        """Установка данных сетки с проверкой размеров"""
        if data.shape != (self.config.mesh_points_x, self.config.mesh_points_y):
            raise ValueError(
                f"Неверный размер сетки: {data.shape}, "
                f"ожидается: ({self.config.mesh_points_x}, {self.config.mesh_points_y})"
            )
        self.mesh_data = data
        
    def get_corner_height(self, corner: str, area_size: int = 1) -> float:
        """
        Получение высоты в углу с усреднением по области
        
        Args:
            corner: Название угла ('front_left', 'front_right', 'back_left', 'back_right')
            area_size: Размер области усреднения (количество точек от центра)
        
        Returns:
            float: Средняя высота угла
        """
        if self.mesh_data is None:
            raise ValueError("Данные сетки не установлены")
            
        if corner not in self.corners:
            raise ValueError(f"Неизвестный угол: {corner}")
            
        x, y = self.corners[corner]
        
        # Определяем границы области для усреднения
        x_start = max(0, x - area_size)
        x_end = min(self.config.mesh_points_x, x + area_size + 1)
        y_start = max(0, y - area_size)
        y_end = min(self.config.mesh_points_y, y + area_size + 1)
        
        # Получаем область и считаем среднее значение
        corner_area = self.mesh_data[x_start:x_end, y_start:y_end]
        return float(np.mean(corner_area))
        
    def get_mesh_stats(self) -> Tuple[float, float, float]:
        """
        Получение общей статистики по сетке
        
        Returns:
            Tuple[float, float, float]: (среднее, минимум, максимум)
        """
        if self.mesh_data is None:
            raise ValueError("Данные сетки не установлены")
            
        mean_height = np.mean(self.mesh_data)
        min_height = np.min(self.mesh_data)
        max_height = np.max(self.mesh_data)
        
        return mean_height, min_height, max_height
        
    def get_point_height(self, x: int, y: int) -> float:
        """
        Получение высоты в конкретной точке сетки
        
        Args:
            x: Индекс по оси X
            y: Индекс по оси Y
            
        Returns:
            float: Высота точки
        """
        if self.mesh_data is None:
            raise ValueError("Данные сетки не установлены")
            
        if not (0 <= x < self.config.mesh_points_x and 0 <= y < self.config.mesh_points_y):
            raise ValueError(f"Координаты ({x}, {y}) вне диапазона сетки")
            
        return float(self.mesh_data[x, y])
        
    def get_mm_per_point(self) -> Tuple[float, float]:
        """
        Получение физического расстояния между точками сетки
        
        Returns:
            Tuple[float, float]: (мм на точку по X, мм на точку по Y)
        """
        x_step = self.config.size_x / (self.config.mesh_points_x - 1)
        y_step = self.config.size_y / (self.config.mesh_points_y - 1)
        return x_step, y_step
    
    def generate_ideal_plane(self) -> np.ndarray:
        """
        Возвращает горизонтальную плоскость на уровне средней высоты сетки.

        Раньше метод подбирал наклонённую плоскость по МНК. Однако для задач
        выравнивания нам нужна именно цель «горизонтальный стол», поэтому
        используем константную плоскость с высотой, равной среднему значению
        всей сетки. Это заставляет все дальнейшие расчёты стремиться к
        реальному выравниванию, а не к сохранению текущего наклона.
        """
        if self.mesh_data is None:
            raise ValueError("Данные сетки не установлены")

        mean_height = float(np.mean(self.mesh_data))
        return np.full_like(self.mesh_data, mean_height, dtype=float)
    
    def calculate_deviation_map(self) -> np.ndarray:
        """
        Расчет карты отклонений от идеальной плоскости
        
        Returns:
            np.ndarray: Карта отклонений (положительные - выше идеальной плоскости,
                        отрицательные - ниже)
        """
        if self.mesh_data is None:
            raise ValueError("Данные сетки не установлены")
            
        ideal_plane = self.generate_ideal_plane()
        deviation_map = self.mesh_data - ideal_plane
        
        return deviation_map
    
    def simulate_adjustment(self, corner_adjustments: Dict[str, float]) -> np.ndarray:
        """
        Симуляция результата регулировки углов
        
        Args:
            corner_adjustments: Словарь с регулировками углов {имя_угла: изменение_высоты}
            
        Returns:
            np.ndarray: Новая сетка после регулировки
        """
        if self.mesh_data is None:
            raise ValueError("Данные сетки не установлены")
            
        # Создаем копию текущей сетки
        adjusted_mesh = self.mesh_data.copy()
        
        # Для каждого угла применяем корректировку с учетом влияния на соседние точки
        for corner, adjustment in corner_adjustments.items():
            if corner not in self.corners:
                continue
                
            # Получаем координаты угла
            x, y = self.corners[corner]
            
            # Создаем матрицу влияния - влияние уменьшается с расстоянием от угла
            influence = np.zeros_like(self.mesh_data, dtype=float)
            
            for i in range(self.config.mesh_points_x):
                for j in range(self.config.mesh_points_y):
                    # Рассчитываем расстояние от точки сетки до угла
                    distance = np.sqrt((i - x)**2 + (j - y)**2)
                    
                    # Расчет коэффициента влияния: больше влияние на ближайшие точки
                    max_distance = np.sqrt(
                        (self.config.mesh_points_x - 1)**2 + 
                        (self.config.mesh_points_y - 1)**2
                    )
                    influence[i, j] = max(0, 1 - (distance / max_distance))
            
            # Применяем корректировку с учетом матрицы влияния
            adjusted_mesh += adjustment * influence
            
        return adjusted_mesh

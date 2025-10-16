#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для интерполяции сетки стола для визуализации
"""

import numpy as np
from scipy.interpolate import griddata, RectBivariateSpline


class MeshInterpolator:
    """Класс для интерполяции данных сетки стола"""
    
    def __init__(self, mesh_data: np.ndarray, x_count: int, y_count: int):
        """
        Инициализация интерполятора
        
        Args:
            mesh_data: Исходные данные сетки
            x_count: Количество точек сетки по X
            y_count: Количество точек сетки по Y
        """
        self.mesh_data = mesh_data
        self.x_count = x_count
        self.y_count = y_count
        
    def interpolate_cubic(self, 
                          target_points: int = 100, 
                          smooth: float = 0.1) -> tuple:
        """
        Интерполяция сетки методом кубического сплайна
        
        Args:
            target_points: Целевое количество точек для интерполяции
            smooth: Коэффициент сглаживания
            
        Returns:
            tuple: (X_grid, Y_grid, Z_values) - сетка X-Y и значения Z для 3D визуализации
        """
        # Создаем исходную сетку координат
        x = np.linspace(0, self.x_count - 1, self.x_count)
        y = np.linspace(0, self.y_count - 1, self.y_count)
        
        # Создаем интерполятор с помощью сплайнов
        interpolator = RectBivariateSpline(x, y, self.mesh_data, s=smooth)
        
        # Создаем точки для интерполированной сетки
        x_new = np.linspace(0, self.x_count - 1, target_points)
        y_new = np.linspace(0, self.y_count - 1, target_points)
        X_new, Y_new = np.meshgrid(x_new, y_new)
        
        # Получаем интерполированные значения
        Z_new = interpolator(x_new, y_new)
        
        return X_new, Y_new, Z_new
        
    def interpolate_grid(self, 
                        target_points: int = 100, 
                        method: str = 'cubic') -> tuple:
        """
        Интерполяция сетки через griddata
        
        Args:
            target_points: Целевое количество точек для интерполяции
            method: Метод интерполяции ('linear', 'cubic', 'nearest')
            
        Returns:
            tuple: (X_grid, Y_grid, Z_values) - сетка X-Y и значения Z для 3D визуализации
        """
        # Создаем список координат точек и значений
        points = []
        values = []
        
        for i in range(self.x_count):
            for j in range(self.y_count):
                points.append([i, j])
                values.append(self.mesh_data[i, j])
        
        # Преобразуем в numpy arrays
        points = np.array(points)
        values = np.array(values)
        
        # Создаем новую, более плотную сетку для интерполяции
        grid_x, grid_y = np.mgrid[0:self.x_count-0.01:complex(0, target_points), 
                                 0:self.y_count-0.01:complex(0, target_points)]
        
        # Интерполируем значения на новой сетке
        grid_z = griddata(points, values, (grid_x, grid_y), method=method)
        
        return grid_x, grid_y, grid_z
        
    def apply_smoothing(self, z_data: np.ndarray, alpha: float = 0.1) -> np.ndarray:
        """
        Применение сглаживания к интерполированным данным
        
        Args:
            z_data: Интерполированные значения Z
            alpha: Коэффициент сглаживания
            
        Returns:
            np.ndarray: Сглаженные данные Z
        """
        # Нормализуем данные для сглаживания
        z_min, z_max = np.nanmin(z_data), np.nanmax(z_data)
        normalized_data = (z_data - z_min) / (z_max - z_min)
        
        # Применяем экспоненциальное сглаживание
        smoothed_data = np.exp(alpha * normalized_data) / np.exp(alpha)
        
        # Возвращаем к исходному диапазону
        smoothed_data = smoothed_data * (z_max - z_min) + z_min
        
        return smoothed_data
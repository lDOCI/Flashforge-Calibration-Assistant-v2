#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для парсинга данных измерений стола
"""

from dataclasses import dataclass
from typing import List, Optional
import numpy as np
import re


@dataclass
class MeshData:
    """Структура данных для хранения информации о сетке измерений"""
    matrix: np.ndarray        # Матрица значений высот
    x_count: int             # Количество точек по X
    y_count: int             # Количество точек по Y
    min_x: float            # Минимальная координата X
    max_x: float            # Максимальная координата X
    min_y: float            # Минимальная координата Y
    max_y: float            # Максимальная координата Y


class KlipperMeshParser:
    """Парсер данных измерения стола из конфигурационного файла Klipper"""
    
    def __init__(self):
        # Регулярные выражения для извлечения данных
        self.point_pattern = re.compile(r'#\*#\s+(-?\d+\.\d+,\s*)*-?\d+\.\d+')
        self.param_pattern = re.compile(r'#\*#\s+(\w+)\s+=\s+(.+)')
    
    def parse_config_file(self, content: str) -> Optional[MeshData]:
        """
        Извлекает данные измерения стола из конфигурационного файла
        
        Args:
            content: Содержимое конфигурационного файла
            
        Returns:
            MeshData: Структура с данными измерений или None в случае ошибки
        """
        try:
            # Извлекаем все строки с точками измерений
            points_data = []
            for line in content.split('\n'):
                if match := self.point_pattern.search(line):
                    # Преобразуем строку с точками в список чисел
                    points = [float(p.strip()) for p in match.group(0).replace('#*#', '').split(',')]
                    points_data.append(points)
            
            # Извлекаем параметры сетки
            params = {}
            for line in content.split('\n'):
                if match := self.param_pattern.search(line):
                    key, value = match.groups()
                    params[key] = value
            
            # Проверяем наличие всех необходимых параметров
            required_params = ['x_count', 'y_count', 'min_x', 'max_x', 'min_y', 'max_y']
            if not all(param in params for param in required_params):
                raise ValueError("Missing required mesh parameters")
            
            # Преобразуем точки в numpy array
            height_matrix = np.array(points_data)
            
            # Создаем и возвращаем структуру данных
            return MeshData(
                matrix=height_matrix,
                x_count=int(params['x_count']),
                y_count=int(params['y_count']),
                min_x=float(params['min_x']),
                max_x=float(params['max_x']),
                min_y=float(params['min_y']),
                max_y=float(params['max_y'])
            )
            
        except Exception as e:
            print(f"Error parsing mesh data: {e}")
            return None
    
    def validate_mesh_data(self, mesh_data: MeshData) -> bool:
        """
        Проверяет корректность данных измерений
        
        Args:
            mesh_data: Структура с данными измерений
            
        Returns:
            bool: True если данные валидны
        """
        # Проверяем размерность матрицы
        if mesh_data.matrix.shape != (mesh_data.x_count, mesh_data.y_count):
            return False
        
        # Проверяем диапазон значений (типичные отклонения для стола)
        if np.any(np.abs(mesh_data.matrix) > 10):
            return False
            
        # Проверяем на наличие некорректных значений
        if np.any(np.isnan(mesh_data.matrix)) or np.any(np.isinf(mesh_data.matrix)):
            return False
            
        return True
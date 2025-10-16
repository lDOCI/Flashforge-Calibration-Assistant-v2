#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для работы с регулировочными винтами
"""

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

class RotationDirection(Enum):
    """Направление вращения винта"""
    CLOCKWISE = "по часовой стрелке"
    COUNTERCLOCKWISE = "против часовой стрелки"

@dataclass
class ScrewConfig:
    """Конфигурация регулировочного винта"""
    type: str = "M4"           # Тип винта
    pitch: float = 0.7         # Шаг резьбы в мм
    min_adjust: float = 0.1    # Минимальное изменение в мм
    max_adjust: float = 2.0    # Максимальное изменение в мм

class Screw:
    """Модель регулировочного винта"""
    def __init__(self, 
                 position: str,
                 config: ScrewConfig = ScrewConfig()):
        self.position = position    # front_left, front_right, back_left, back_right
        self.config = config
        self.MM_PER_MINUTE = config.pitch / 60  # мм на минуту поворота
        self.MM_PER_DEGREE = config.pitch / 360  # мм на градус поворота
        
    def calculate_adjustment(self, current_height: float, target_height: float) -> Tuple[float, RotationDirection]:
        """
        Расчет необходимого поворота винта
        
        Args:
            current_height: Текущая высота
            target_height: Целевая высота
            
        Returns:
            Tuple[float, RotationDirection]: (количество минут, направление)
        """
        diff = current_height - target_height
        
        # Если разница меньше минимальной регулировки, регулировка не требуется
        if abs(diff) < self.config.min_adjust:
            return 0, RotationDirection.CLOCKWISE
            
        # Определяем направление и количество минут
        direction = (RotationDirection.CLOCKWISE if diff > 0 
                    else RotationDirection.COUNTERCLOCKWISE)
                    
        # Рассчитываем минуты с ограничением максимальной регулировки
        minutes = min(
            abs(diff) / self.MM_PER_MINUTE,
            self.config.max_adjust / self.MM_PER_MINUTE
        )
        
        return minutes, direction
        
    def minutes_to_degrees(self, minutes: float) -> float:
        """Перевод минут в градусы"""
        return minutes * 6  # 1 минута = 6 градусов
        
    def height_change_from_minutes(self, minutes: float, direction: RotationDirection) -> float:
        """Расчет изменения высоты от поворота в минутах"""
        height_change = minutes * self.MM_PER_MINUTE
        return -height_change if direction == RotationDirection.CLOCKWISE else height_change
        
    def height_change_from_degrees(self, degrees: float, direction: RotationDirection) -> float:
        """Расчет изменения высоты от поворота в градусах"""
        height_change = degrees * self.MM_PER_DEGREE
        return -height_change if direction == RotationDirection.CLOCKWISE else height_change
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль для 3D визуализации поверхности стола принтера.
"""

from typing import Callable, Optional

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import patheffects
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from mpl_toolkits.mplot3d import Axes3D
import tkinter as tk

from data_processing.mesh_interpolator import MeshInterpolator
from visualization.widgets.custom_toolbars import MinimalNavigationToolbar
from app.ui.language import _

Translator = Callable[[str, Optional[str]], str]


class BedMesh3D:
    """Класс для отображения 3D визуализации стола."""

    def __init__(self, is_dark_theme: bool = False, translator: Optional[Translator] = None):
        """
        Инициализация визуализатора
        
        Args:
            is_dark_theme: Использовать ли темную тему
        """
        self.mesh_data = None
        self.max_delta = None
        self.is_dark_theme = is_dark_theme
        self.interpolation_factor = 100  # Количество точек сетки после интерполяции
        self.figsize = (7.0, 5.5)
        self._translator: Translator = translator or _

    # ------------------------------------------------------------------ service helpers
    def set_translator(self, translator: Optional[Translator]) -> None:
        """Устанавливает функцию перевода, совместимую с LocalizationService."""
        if translator is None:
            self._translator = _
        else:
            self._translator = translator

    def _tr(self, key: str, default: Optional[str] = None) -> str:
        return self._translator(key, default)
        
    def set_mesh_data(self, mesh_data: np.ndarray) -> None:
        """
        Установка данных сетки и расчет максимального отклонения
        
        Args:
            mesh_data: Данные сетки стола
        """
        self.mesh_data = mesh_data
        self.max_delta = float(np.max(self.mesh_data) - np.min(self.mesh_data))


    def display_in_frame(self, frame):
        """
        Отображение 3D карты в заданном фрейме
        
        Args:
            frame: Фрейм tkinter для отображения
        """
        if self.mesh_data is None:
            return
            
        # Удаляем предыдущие виджеты
        for widget in frame.winfo_children():
            widget.destroy()
            
        fig = self.create_3d_figure()
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        
        # Создаем минимальную панель инструментов (без кнопок)
        toolbar = MinimalNavigationToolbar(canvas, frame)
        toolbar.update()
        
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


    def set_theme(self, is_dark_theme: bool) -> None:
        """
        Установка темы
        
        Args:
            is_dark_theme: Использовать ли темную тему
        """
        self.is_dark_theme = is_dark_theme
        
    def set_interpolation_factor(self, factor: int) -> None:
        """
        Установка фактора интерполяции

        Args:
            factor: Фактор интерполяции (количество точек сетки после интерполяции)
        """
        if factor > 0:
            self.interpolation_factor = factor

    def set_figsize(self, width: float, height: float) -> None:
        if width > 0 and height > 0:
            self.figsize = (width, height)

    def create_3d_figure(self) -> Figure:
        """
        Создание фигуры с 3D визуализацией стола
        
        Returns:
            Figure: Объект фигуры matplotlib с 3D визуализацией
        """
        if self.mesh_data is None:
            return None
        
        fig = Figure(figsize=self.figsize, dpi=100)
        fig.patch.set_alpha(0.0)
        fig.subplots_adjust(left=0.06, right=0.82, bottom=0.05, top=0.86)
        ax = fig.add_subplot(111, projection='3d')

        if self.is_dark_theme:
            text_color = 'white'
        else:
            text_color = 'black'
        ax.set_facecolor('none')
        
        # Получаем размеры сетки
        rows, cols = self.mesh_data.shape
        
        # Создаем интерполятор
        interpolator = MeshInterpolator(self.mesh_data, rows, cols)
        
        # Выполняем интерполяцию
        X_smooth, Y_smooth, Z_smooth = interpolator.interpolate_cubic(
            target_points=self.interpolation_factor
        )
        
        # Применяем сглаживание для более естественного отображения
        Z_smooth = interpolator.apply_smoothing(Z_smooth, alpha=0.1)
        
        # Выбираем цветовую карту с учетом темы
        cmap = 'viridis' if self.is_dark_theme else 'coolwarm_r'
        
        # Создаем 3D поверхность
        surf = ax.plot_surface(X_smooth, Y_smooth, Z_smooth, cmap=cmap,
                               linewidth=0, antialiased=True, alpha=0.8)
        
        # Добавляем цветовую шкалу
        cbar = fig.colorbar(surf, ax=ax, fraction=0.04, pad=0.03)
        cbar.set_label(self._tr("visualization.height_mm"), color=text_color)
        cbar.ax.yaxis.set_tick_params(color=text_color)
        plt.setp(cbar.ax.get_yticklabels(), color=text_color)
        
        # Настраиваем цвета для темной темы
        if self.is_dark_theme:
            ax.xaxis.set_tick_params(colors=text_color)
            ax.yaxis.set_tick_params(colors=text_color)
            ax.zaxis.set_tick_params(colors=text_color)
        
        z_max = np.max(Z_smooth)
        z_min = np.min(Z_smooth)
        z_range = z_max - z_min
        z_offset = z_range * 0.3

        outline = [patheffects.withStroke(linewidth=2, foreground=('black' if text_color == 'white' else 'white'))]
        ax.text(
            0,
            0,
            z_min - z_offset,
            self._tr("visual_rec.front_left"),
            size=9,
            color=text_color,
            path_effects=outline,
        )
        ax.text(
            cols - 1,
            0,
            z_min - z_offset,
            self._tr("visual_rec.front_right"),
            size=9,
            color=text_color,
            path_effects=outline,
        )
        ax.text(
            0,
            rows - 1,
            z_min - z_offset,
            self._tr("visual_rec.back_left"),
            size=9,
            color=text_color,
            path_effects=outline,
        )
        ax.text(
            cols - 1,
            rows - 1,
            z_min - z_offset,
            self._tr("visual_rec.back_right"),
            size=9,
            color=text_color,
            path_effects=outline,
        )

        ax.set_zlim(z_min - z_offset * 2, z_max + z_offset * 0.5)

        max_deviation = float(np.max(self.mesh_data) - np.min(self.mesh_data))
        ax.text2D(
            0.5,
            1.12,
            self._tr("visualization.3d_map_title").format(max_deviation),
            color=text_color,
            fontsize=11,
            fontweight='semibold',
            ha='center',
            va='bottom',
            transform=ax.transAxes,
        )
        
        # Настраиваем ракурс для лучшего просмотра
        ax.view_init(elev=30, azim=45)
        
        # Подписи осей
        ax.set_xlabel('X', color=text_color)
        ax.set_ylabel('Y', color=text_color)
        ax.set_zlabel(_("visualization.height_mm"), color=text_color)
        
        return fig
        
    def display_in_window(self, parent_widget):
        """
        Отображение 3D карты в отдельном окне tkinter
        
        Args:
            parent_widget: Родительский виджет tkinter
        """
        if self.mesh_data is None:
            return
            
        top = tk.Toplevel(parent_widget)
        top.title(_("visualization.3d_map_window_title"))
        top.geometry("800x700")
        
        fig = self.create_3d_figure()
        
        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        
        class CustomNavigationToolbar(NavigationToolbar2Tk):
            def __init__(self, canvas, window):
                self.toolitems = []  # Пустой список - нет кнопок
                NavigationToolbar2Tk.__init__(self, canvas, window)

        custom_toolbar = CustomNavigationToolbar(canvas, frame)
        
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def display_in_frame(self, frame):
        """
        Отображение 3D карты в заданном фрейме
        
        Args:
            frame: Фрейм tkinter для отображения
        """
        if self.mesh_data is None:
            return
            
        # Удаляем предыдущие виджеты
        for widget in frame.winfo_children():
            widget.destroy()
            
        fig = self.create_3d_figure()
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        
        toolbar = NavigationToolbar2Tk(canvas, frame)
        toolbar.update()
        
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
    def create_comparison_figure(self, before_mesh: np.ndarray, after_mesh: np.ndarray) -> Figure:
        """
        Создание фигуры с сравнением двух поверхностей (до и после регулировки)
        
        Args:
            before_mesh: Сетка до регулировки
            after_mesh: Сетка после регулировки
            
        Returns:
            Figure: Объект фигуры matplotlib с 3D визуализацией сравнения
        """
        if before_mesh is None or after_mesh is None:
            return None
            
        fig = Figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        
        # Настройка цветов для темной темы
        if self.is_dark_theme:
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            text_color = 'white'
        else:
            text_color = 'black'
        
        # Получаем размеры сетки
        rows, cols = before_mesh.shape
        
        # Создаем интерполятор для обеих сеток
        interp_before = MeshInterpolator(before_mesh, rows, cols)
        interp_after = MeshInterpolator(after_mesh, rows, cols)
        
        # Интерполируем данные
        X_before, Y_before, Z_before = interp_before.interpolate_cubic(
            target_points=self.interpolation_factor
        )
        X_after, Y_after, Z_after = interp_after.interpolate_cubic(
            target_points=self.interpolation_factor
        )
        
        # Применяем сглаживание
        Z_before = interp_before.apply_smoothing(Z_before, alpha=0.1)
        Z_after = interp_after.apply_smoothing(Z_after, alpha=0.1)
        
        # Отображаем поверхности
        # Используем разные цветовые карты для лучшего отличия
        surf_before = ax.plot_surface(X_before, Y_before, Z_before, 
                                     cmap='coolwarm_r', alpha=0.5,
                                     linewidth=0, antialiased=True)
        
        surf_after = ax.plot_surface(X_after, Y_after, Z_after, 
                                    cmap='viridis', alpha=0.8,
                                    linewidth=0, antialiased=True)
        
        # Добавляем цветовые шкалы
        cbar1 = fig.colorbar(surf_before, ax=ax, shrink=0.4, pad=0.05, aspect=10)
        cbar2 = fig.colorbar(surf_after, ax=ax, shrink=0.4, pad=0.15, aspect=10)
        cbar1.set_label(_("visualization.before_mm"), color=text_color)
        cbar2.set_label(_("visualization.after_mm"), color=text_color)
        
        # Настраиваем цвета для темной темы
        if self.is_dark_theme:
            for cbar in [cbar1, cbar2]:
                cbar.ax.yaxis.set_tick_params(color=text_color)
                plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color=text_color)
            
            ax.xaxis.set_tick_params(colors=text_color)
            ax.yaxis.set_tick_params(colors=text_color)
            ax.zaxis.set_tick_params(colors=text_color)
        
        # Добавляем заголовок
        before_deviation = float(np.max(before_mesh) - np.min(before_mesh))
        after_deviation = float(np.max(after_mesh) - np.min(after_mesh))
        improvement = before_deviation - after_deviation
        percent_improvement = (improvement / before_deviation) * 100 if before_deviation > 0 else 0
        
        title = _("visual_rec.improvement_prediction").format(
            improvement=improvement,
            percent=percent_improvement,
            before=before_deviation,
            after=after_deviation
        )
        
        ax.set_title(title, color=text_color)
        
        # Настраиваем ракурс для лучшего просмотра
        ax.view_init(elev=30, azim=45)
        
        # Подписи осей
        ax.set_xlabel('X', color=text_color)
        ax.set_ylabel('Y', color=text_color)
        ax.set_zlabel(_("visualization.height_mm"), color=text_color)
        
        # Добавляем легенду (создаем proxy для поверхностей)
        import matplotlib.patches as mpatches
        before_patch = mpatches.Patch(color='blue', label=_("visual_rec.before_adjustment"))
        after_patch = mpatches.Patch(color='green', label=_("visual_rec.after_adjustment"))
        ax.legend(handles=[before_patch, after_patch], loc='upper right')
        
        fig.tight_layout()
        return fig

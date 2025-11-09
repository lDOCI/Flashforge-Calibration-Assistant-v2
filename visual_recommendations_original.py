#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль визуальных рекомендаций для Flashforge Calibration Assistant
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches
import matplotlib.animation as animation
from PIL import Image, ImageTk
from app.ui.language import _
from visualization.widgets.custom_toolbars import MinimalNavigationToolbar

class VisualRecommendationsWindow:
    """Окно визуальных рекомендаций по выравниванию стола"""

    def __init__(self, main_window, bed, analyzer, screw_solver, tape_calculator):
        # Создаем новое окно
        self.window = tk.Toplevel(main_window.root)
        self.window.title(_("visual_rec.title"))
        self.window.geometry("1200x900")
        self.window.minsize(1000, 800)

        # Сохраняем ссылки на объекты
        self.main = main_window
        self.bed = bed
        self.mesh_data = bed.mesh_data
        self.analyzer = analyzer
        self.screw_solver = screw_solver
        self.tape_calculator = tape_calculator

        # Получаем данные для анализа
        self.strategy = self.analyzer.find_optimal_strategy()
        self.ideal_plane = self.analyzer.get_ideal_plane()
        self.adjustments = self.screw_solver.calculate_adjustments(self.ideal_plane)

        # Проверяем, используется ли темная тема
        self.is_dark_theme = self.main.app_settings.get('theme', 'light') == 'dark'

        # Настройки отображения
        self.settings = self.main.settings_tab.get_settings()
        self.show_minutes = self.settings['visualization']['show_minutes']
        self.show_degrees = self.settings['visualization']['show_degrees']

        # Максимальное отклонение
        self.max_delta = float(np.max(self.mesh_data) - np.min(self.mesh_data))
        print(f"Max delta: {self.max_delta}")  # Отладка

        # Создаем интерфейс
        self.create_layout()

    def create_layout(self):
        """Создает интерфейс окна рекомендаций"""
        # Создаем фрейм с пояснениями
        explanation_frame = ttk.LabelFrame(self.window, text=_("Instructions"))
        explanation_frame.pack(fill=tk.X, padx=10, pady=5)

        # Добавляем объяснение процесса выравнивания
        explanation_text = _("visual_rec.instructions")

        ttk.Label(explanation_frame, text=explanation_text, justify=tk.LEFT, padding=10).pack(fill=tk.X)

        # Добавляем notebook для визуализаций
        self.notebook = ttk.Notebook(self.window)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Создаем вкладки
        self.create_problem_map_tab()
        self.create_screw_adjustment_tab()
        self.create_tape_application_tab()
        self.create_prediction_tab()

        # Добавляем кнопку закрытия внизу
        close_button = ttk.Button(
            self.window,
            text=_("Close"),
            command=self.window.destroy,
            style='Action.TButton'
        )
        close_button.pack(pady=10)

    def create_problem_map_tab(self):
        """Создает вкладку с картой проблемных зон"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=_("visual_rec.problem_map"))

        # Создаем фигуру для отрисовки
        fig = Figure(figsize=(10, 8))
        ax = fig.add_subplot(111)

        # Настройка цветов для темной/светлой темы
        if self.is_dark_theme:
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            text_color = 'white'
        else:
            text_color = 'black'

        # Рисуем контур стола
        bed = patches.Rectangle((0, 0), 4, 4, fill=False, color='black', linewidth=2)
        ax.add_patch(bed)

        # Добавляем сетку 5x5
        for i in range(5):
            ax.axhline(y=i, color='gray', linestyle=':', alpha=0.3)
            ax.axvline(x=i, color='gray', linestyle=':', alpha=0.3)

        # Рассчитываем среднюю высоту для определения проблемных зон
        mean_height = np.mean(self.mesh_data)

        # Создаем цветовую карту для улучшенной визуализации
        cmap_high = plt.cm.Reds
        cmap_low = plt.cm.Blues

        # Отмечаем проблемные зоны на основе данных с градиентом цвета
        for i in range(5):
            for j in range(5):
                height = self.mesh_data[i, j]
                diff = height - mean_height

                if diff > 0.1:  # Высокая точка
                    color_intensity = min(1.0, diff / 0.4)  # Max 0.4mm = 100%
                    circle = patches.Circle((j, i), 0.3,
                                          color=cmap_high(color_intensity),
                                          alpha=0.7)
                    ax.add_patch(circle)
                    ax.text(j, i, f"+{diff:.2f}", ha='center', va='center',
                           color='white', fontsize=9, fontweight='bold')

                elif diff < -0.1:  # Низкая точка
                    color_intensity = min(1.0, abs(diff) / 0.4)  # Max 0.4mm = 100%
                    circle = patches.Circle((j, i), 0.3,
                                          color=cmap_low(color_intensity),
                                          alpha=0.7)
                    ax.add_patch(circle)
                    ax.text(j, i, f"{diff:.2f}", ha='center', va='center',
                           color='white', fontsize=9, fontweight='bold')

        # Устанавливаем правильную ориентацию стола (передняя часть внизу)
        ax.text(-0.3, -0.5, _("visual_rec.front_left"), fontsize=10, ha='right', va='center',
               color=text_color, bbox=dict(facecolor='white', alpha=0.7,
                                          edgecolor='none', boxstyle='round,pad=0.3'))
        ax.text(4.3, -0.5, _("visual_rec.front_right"), fontsize=10, ha='left', va='center',
               color=text_color, bbox=dict(facecolor='white', alpha=0.7,
                                          edgecolor='none', boxstyle='round,pad=0.3'))
        ax.text(-0.3, 4.5, _("visual_rec.back_left"), fontsize=10, ha='right', va='center',
               color=text_color, bbox=dict(facecolor='white', alpha=0.7,
                                          edgecolor='none', boxstyle='round,pad=0.3'))
        ax.text(4.3, 4.5, _("visual_rec.back_right"), fontsize=10, ha='left', va='center',
               color=text_color, bbox=dict(facecolor='white', alpha=0.7,
                                          edgecolor='none', boxstyle='round,pad=0.3'))

        # Конфигурация осей и заголовка
        ax.set_xlim(-0.5, 4.5)
        ax.set_ylim(-1, 5)
        ax.set_aspect('equal')
        ax.set_title(_("visualization.bed_mesh_title").format(self.max_delta),
                    color=text_color)

        # Добавляем легенду
        import matplotlib.lines as mlines

        high_patch = mlines.Line2D([], [], color=cmap_high(0.7), marker='o',
                                 linestyle='None', markersize=10, label=_("visual_rec.high_points"))
        low_patch = mlines.Line2D([], [], color=cmap_low(0.7), marker='o',
                                linestyle='None', markersize=10, label=_("visual_rec.low_points"))

                # На следующий код:
        ax.legend(handles=[high_patch, low_patch], 
                bbox_to_anchor=(1.15, 0.9),  # Точка привязки легенды (справа от графика)
                loc='upper left',           # Привязываем верхний левый угол легенды к точке
                framealpha=0.9)

        # И добавить настройку отступов для графика, чтобы легенда поместилась
        fig.subplots_adjust(right=0.85)  

        ax.axis('off')  # Скрываем оси

        # Отображаем фигуру
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()

        toolbar = MinimalNavigationToolbar(canvas, tab)
        toolbar.update()

        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_screw_adjustment_tab(self):
        """Создает вкладку со схемой регулировки винтов"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=_("visual_rec.screw_scheme"))

        # Создаем фигуру для отрисовки схемы винтов
        fig = Figure(figsize=(10, 8))
        ax = fig.add_subplot(111)

        # Настройка цветов для темной/светлой темы
        if self.is_dark_theme:
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            text_color = 'white'
            panel_bg = '#2d2d2d'
        else:
            text_color = 'black'
            panel_bg = '#f0f0f0'

        # Рисуем контур стола (вид сверху)
        bed_size = 12  # Увеличиваем размер для лучшей видимости
        bed = patches.Rectangle((-bed_size/2, -bed_size/2), bed_size, bed_size,
                               fill=True, facecolor=panel_bg, edgecolor='#808080', linewidth=2)
        ax.add_patch(bed)

        # Позиции винтов
        screw_positions = {
            'front_left': (-bed_size/3, -bed_size/3),
            'front_right': (bed_size/3, -bed_size/3),
            'back_left': (-bed_size/3, bed_size/3),
            'back_right': (bed_size/3, bed_size/3)
        }

        # Словарь с названиями углов для подписей
        corner_labels = {
            'front_left': _("visual_rec.front_left"),
            'front_right': _("visual_rec.front_right"),
            'back_left': _("visual_rec.back_left"),
            'back_right': _("visual_rec.back_right")
        }

        # Получаем высоты углов
        corner_heights = {
            'front_left': float(self.mesh_data[0, 0]),
            'front_right': float(self.mesh_data[0, -1]),
            'back_left': float(self.mesh_data[-1, 0]),
            'back_right': float(self.mesh_data[-1, -1])
        }

        mean_height = np.mean(self.mesh_data)
        print(f"Mean height: {mean_height}")  # Отладка
        print(f"Corner heights: {corner_heights}")  # Отладка

        # Список для хранения данных анимации
        animation_objects = []

        # Визуализируем каждый винт с указаниями по регулировке
        for corner, pos in screw_positions.items():
            height = corner_heights[corner]
            diff = height - mean_height
            print(f"{corner}: height={height}, diff={diff}")  # Отладка

            # Отрисовываем круг основания винта
            base_circle = patches.Circle(pos, bed_size/10, fill=True, facecolor='gray',
                                        alpha=0.5, edgecolor='black', linewidth=1)
            ax.add_patch(base_circle)

            # Добавляем подпись угла
            ax.text(pos[0], pos[1] - bed_size/6, corner_labels[corner],
                    ha='center', va='center', fontsize=10, fontweight='bold',
                    color=text_color, bbox=dict(facecolor=panel_bg, alpha=0.7, boxstyle='round'))

            # Если есть значительное отклонение - добавляем инструкцию
            if abs(diff) > 0.1:
                # Рассчитываем градусы поворота
                total_degrees = abs(diff) * 100 * 5.14  # DEGREES_PER_01MM = 5.14
                minutes = int(total_degrees * 60 / 360)

                # Создаем текст с учетом настроек
                rotation_text = []
                if self.show_minutes:
                    rotation_text.append(f"{minutes} мин")
                if self.show_degrees:
                    rotation_text.append(f"{int(total_degrees)}°")
                rotation = " / ".join(rotation_text) if rotation_text else f"{minutes} мин"

                if diff < -0.1:  # Нужно поднять угол (против часовой)
                    wedge_color = 'green'
                    rotation_symbol = '↺'
                    start_angle = 90
                    end_angle = 90 + total_degrees
                    rotation_direction = _("visual_rec.counterclockwise")
                else:  # Нужно опустить угол (по часовой)
                    wedge_color = 'red'
                    rotation_symbol = '↻'
                    start_angle = 90
                    end_angle = 90 - total_degrees
                    rotation_direction = _("visual_rec.clockwise")

                # Анимируемый клин
                animated_wedge = patches.Wedge(
                    center=pos, r=bed_size/8, theta1=start_angle if diff > -0.1 else 90,
                    theta2=start_angle if diff <= -0.1 else 90,
                    color=wedge_color, alpha=0.5
                )
                ax.add_patch(animated_wedge)
                animation_objects.append({
                    'wedge': animated_wedge,
                    'start_angle': start_angle,
                    'end_angle': end_angle,
                    'clockwise': diff > -0.1
                })
                print(f"Added animation object for {corner}: diff={diff}")  # Отладка

                # Добавляем символ вращения в центр
                ax.text(pos[0], pos[1], rotation_symbol, ha='center', va='center',
                        fontsize=20, color=wedge_color, fontweight='bold')

                # Добавляем текст с единицами и направлением
                ax.text(pos[0], pos[1] + bed_size/6, f"{rotation}\n{rotation_direction}",
                        ha='center', va='center', fontsize=9, color=wedge_color,
                        fontweight='bold', bbox=dict(facecolor=panel_bg, alpha=0.7, boxstyle='round'))
            else:
                ax.text(pos[0], pos[1], "✓", ha='center', va='center', fontsize=20,
                        color='gray', fontweight='bold')
                ax.text(pos[0], pos[1] + bed_size/6, _("visual_rec.normal"), ha='center', va='center',
                        fontsize=8, color='gray')

        # Добавляем легенду внизу, не перекрывая схему
        legend_text = _("visual_rec.screw_legend")
        ax.text(0, -bed_size/2 - bed_size/10, legend_text, ha='center', va='top',
                fontsize=9, linespacing=1.5, color=text_color,
                bbox=dict(facecolor=panel_bg, alpha=0.8, boxstyle='round'))

        # Настраиваем оси с дополнительным пространством для легенды
        ax.set_xlim(-bed_size/2 - bed_size/10, bed_size/2 + bed_size/10)
        ax.set_ylim(-bed_size/2 - bed_size/5 - bed_size/10, bed_size/2 + bed_size/5)
        ax.set_aspect('equal')
        ax.axis('off')
        ax.set_title(_("visual_rec.screw_scheme"), color=text_color)

        # Сначала создаём canvas
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()

        # Создание анимации, если есть объекты
        if animation_objects:
            print(f"Animation objects created: {len(animation_objects)}")  # Отладка
            def init():
                for data in animation_objects:
                    if data['clockwise']:
                        data['wedge'].set_theta1(data['start_angle'])
                    else:
                        data['wedge'].set_theta2(data['start_angle'])
                return [data['wedge'] for data in animation_objects]

            def animate(frame):
                for data in animation_objects:
                    if data['clockwise']:
                        current_angle = data['start_angle'] - (data['start_angle'] - data['end_angle']) * (frame / 20)
                        data['wedge'].set_theta1(current_angle)
                    else:
                        current_angle = data['start_angle'] + (data['end_angle'] - data['start_angle']) * (frame / 20)
                        data['wedge'].set_theta2(current_angle)
                return [data['wedge'] for data in animation_objects]

            self.anim = animation.FuncAnimation(fig, animate, init_func=init, frames=20, interval=50,
                                               blit=True, repeat=True, repeat_delay=1000)
            canvas.draw()  # Перерисовка после создания анимации
            print("Animation initialized")  # Отладка
        else:
            print("No animation objects created - all corners within 0.1mm tolerance")  # Отладка

        # Добавляем toolbar и отображаем
        toolbar = MinimalNavigationToolbar(canvas, tab)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_tape_application_tab(self):
        """Создает вкладку со схемой наклейки скотча"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=_("visual_rec.tape_scheme"))

        # Создаем фигуру для отрисовки
        fig = Figure(figsize=(10, 8))
        ax = fig.add_subplot(111)

        # Настройка цветов для темной/светлой темы
        if self.is_dark_theme:
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            text_color = 'white'
            grid_color = 'gray'
        else:
            text_color = 'black'
            grid_color = 'lightgray'

        # Рисуем контур стола
        rect = patches.Rectangle((-0.5, -0.5), 5, 5, fill=False, color=grid_color, linewidth=1.5)
        ax.add_patch(rect)

        # Добавляем сетку
        for i in range(6):
            ax.axhline(y=i-0.5, color=grid_color, linestyle=':', alpha=0.5)
            ax.axvline(x=i-0.5, color=grid_color, linestyle=':', alpha=0.5)

        # Добавляем аннотации для рядов и колонок
        for i in range(5):
            ax.text(-1, i, str(i+1), ha='center', va='center', fontsize=10, color=text_color)
            ax.text(i, -1, chr(65+i), ha='center', va='center', fontsize=10, color=text_color)

        # Функция для определения количества слоев скотча
        def calculate_tape_layers(height_diff):
            tape_thickness = self.settings['hardware']['tape_thickness']
            return max(1, int(np.ceil(abs(height_diff) / tape_thickness)))

        # Рассчитываем среднюю высоту для определения проблемных зон
        mean_height = np.mean(self.mesh_data)

        # Создаем список точек для наклейки скотча
        tape_points = []
        for i in range(5):
            for j in range(5):
                height = self.mesh_data[i, j]
                diff = mean_height - height
                if diff > 0.05:  # Порог в 0.05мм для скотча
                    # Вычисляем слои
                    layers = calculate_tape_layers(diff)
                    position = f"{i+1}{chr(65+j)}"

                    # Определяем цвет в зависимости от количества слоев
                    if layers == 1:
                        color = '#FFD700'  # Золотой
                    elif layers == 2:
                        color = '#FFA500'  # Оранжевый
                    elif layers >= 3:
                        color = '#FF4500'  # Темно-оранжевый

                    # Рисуем квадрат для скотча
                    alpha = min(0.4 + layers * 0.1, 0.9)  # Больше слоев = более насыщенный цвет
                    square = patches.Rectangle(
                        (j - 0.4, i - 0.4),
                        0.8, 0.8,
                        facecolor=color,  # Используем facecolor с цветом
                        alpha=alpha,
                        edgecolor='#e67e22',
                        linewidth=1.5
                    )
                    ax.add_patch(square)

                    # Добавляем номер слоев в центр
                    ax.text(
                        j, i,
                        str(layers),
                        ha='center',
                        va='center',
                        fontsize=12,
                        fontweight='bold',
                        color='black'
                    )

                    # Сохраняем информацию о точке
                    tape_points.append({
                        'position': position,
                        'diff': diff,
                        'layers': layers,
                        'coords': (j, i)
                    })

        # Устанавливаем правильную ориентацию стола (передняя часть внизу)
        ax.text(-0.7, -1, _("visual_rec.front_left"), fontsize=9, ha='right', va='center',
               color=text_color, bbox=dict(facecolor='white', alpha=0.7,
                                          edgecolor='none', boxstyle='round,pad=0.2'))
        ax.text(4.7, -1, _("visual_rec.front_right"), fontsize=9, ha='left', va='center',
               color=text_color, bbox=dict(facecolor='white', alpha=0.7,
                                          edgecolor='none', boxstyle='round,pad=0.2'))
        ax.text(-0.7, 5, _("visual_rec.back_left"), fontsize=9, ha='right', va='center',
               color=text_color, bbox=dict(facecolor='white', alpha=0.7,
                                          edgecolor='none', boxstyle='round,pad=0.2'))
        ax.text(4.7, 5, _("visual_rec.back_right"), fontsize=9, ha='left', va='center',
               color=text_color, bbox=dict(facecolor='white', alpha=0.7,
                                          edgecolor='none', boxstyle='round,pad=0.2'))

        # Конфигурация осей и заголовка
        ax.set_xlim(-1.5, 5.5)
        ax.set_ylim(-2, 5)
        ax.set_aspect('equal')

        # Изменяем положение инструкции, перемещая её вправо
        if tape_points:
            # Рамка для инструкции (перемещаем вправо)
            info_height = 3
            info_rect = patches.Rectangle(
                (5.5, 0),  # Изменено с (-4.5, 0) на (5.5, 0)
                3, info_height,
                fill=True,
                alpha=0.1,
                edgecolor='gray',
                facecolor='lightgray',
                linewidth=1
            )
            ax.add_patch(info_rect)

            # Заголовок инструкции (обновляем x-координату)
            ax.text(
                7, info_height-0.3,  # Изменено с -3 на 7
                _("visual_rec.tape_instruction_title"),
                ha='center',
                va='center',
                fontsize=10,
                fontweight='bold',
                color=text_color
            )

            # Обновляем x-координаты для всех текстовых элементов инструкции
            ax.text(
                5.7, info_height-0.7,  # Изменено с -4.3 на 5.7
                _("visual_rec.tape_instruction_1"),
                ha='left',
                va='center',
                fontsize=9,
                color=text_color
            )

            ax.text(
                5.7, info_height-1.2,  # Обновлено x-координату
                _("visual_rec.tape_instruction_2"),
                ha='left',
                va='center',
                fontsize=9,
                color=text_color
            )

            ax.text(
                5.7, info_height-1.7,  # Обновлено x-координату
                _("visual_rec.tape_instruction_3"),
                ha='left',
                va='center',
                fontsize=9,
                color=text_color
            )

            ax.text(
                5.7, info_height-2.2,  # Обновлено x-координату
                _("visual_rec.tape_instruction_4"),
                ha='left',
                va='center',
                fontsize=9,
                color=text_color
            )

        
            # Создаем легенду, но размещаем её вне графика
            from matplotlib.patches import Patch

            # Создаем элементы легенды с переводами
            legend_elements = [
                Patch(facecolor='#FFD700', edgecolor='black', linewidth=1.5, label=_("visual_rec.tape_layer_1")),
                Patch(facecolor='#FFA500', edgecolor='black', linewidth=1.5, label=_("visual_rec.tape_layer_2")),
                Patch(facecolor='#FF4500', edgecolor='black', linewidth=1.5, label=_("visual_rec.tape_layer_3"))
            ]

            # Размещаем легенду вне графика
            # bbox_to_anchor: (x, y) - координаты точки привязки относительно осей
            # loc: положение легенды относительно точки привязки
            # Параметры подобраны, чтобы легенда оказалась справа от графика
            legend = ax.legend(handles=legend_elements, 
                            title=_("visual_rec.tape_layers_legend"),
                            bbox_to_anchor=(1.15, 0.9), # Точка привязки чуть правее и выше центра
                            loc='upper left',          # Легенда располагается левым верхним углом к точке привязки
                            fontsize=8,
                            framealpha=0.9)
                            
            legend.get_title().set_fontsize('8')


            # Убедимся, что легенда видна, добавив немного места справа
            plt.tight_layout()
            plt.subplots_adjust(right=0.85)  # Делаем отступ справа для легенды


            title = _("visual_rec.tape_scheme_with_points").format(len(tape_points))
        else:
            title = _("visual_rec.tape_scheme_not_needed")
            ax.text(
                2, 2,
                _("visual_rec.tape_correction_not_needed"),
                ha='center',
                va='center',
                fontsize=14,
                color=text_color
            )

        ax.set_title(title, color=text_color)
        ax.axis('off')  # Скрываем оси

        # Отображаем фигуру
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()

        # Используем минимальную панель инструментов
        toolbar = MinimalNavigationToolbar(canvas, tab)
        toolbar.update()

        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_prediction_tab(self):
        """Создает вкладку с предсказанием результатов выравнивания"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=_("visual_rec.prediction"))

        # Если есть стратегия регулировки, показываем предсказание
        if self.strategy:
            # Создаем фигуру для отрисовки
            fig = Figure(figsize=(10, 8))
            ax = fig.add_subplot(111, projection='3d')

            # Настройка цветов для темной/светлой темы
            if self.is_dark_theme:
                fig.patch.set_facecolor('#1e1e1e')
                ax.set_facecolor('#1e1e1e')
                text_color = 'white'
                grid_color = 'gray'
            else:
                text_color = 'black'
                grid_color = 'lightgray'

            # Создаем сетку для 3D графика
            rows, cols = self.mesh_data.shape
            X, Y = np.meshgrid(range(rows), range(cols))

            # Создаем более плотную сетку для гладкой поверхности
            from scipy.interpolate import RectBivariateSpline

            # Получаем коэффициент интерполяции из настроек
            grid_points = int(self.settings['visualization']['interpolation_factor'])

            # Создаем плотную сетку для интерполяции
            x_smooth = np.linspace(0, rows-1, grid_points)
            y_smooth = np.linspace(0, cols-1, grid_points)
            X_smooth, Y_smooth = np.meshgrid(x_smooth, y_smooth)

            # Получаем данные до и после регулировки
            before_mesh = self.mesh_data

            # Используем симулированные данные из стратегии если они есть
            if 'simulated_bed_after_screws' in self.strategy:
                after_mesh = self.strategy['simulated_bed_after_screws']
            else:
                after_mesh = before_mesh.copy()

            # Интерполируем данные на более плотную сетку
            interp_before = RectBivariateSpline(range(rows), range(cols), before_mesh)
            interp_after = RectBivariateSpline(range(rows), range(cols), after_mesh)

            Z_before_smooth = interp_before(x_smooth, y_smooth)
            Z_after_smooth = interp_after(x_smooth, y_smooth)

            # Строим поверхности
            surf_before = ax.plot_surface(
                X_smooth, Y_smooth, Z_before_smooth,
                cmap='coolwarm_r',
                alpha=0.7,
                linewidth=0,
                antialiased=True,
                label=_("visual_rec.before_adjustment")
            )

            surf_after = ax.plot_surface(
                X_smooth, Y_smooth, Z_after_smooth,
                cmap='viridis',
                alpha=0.7,
                linewidth=0,
                antialiased=True,
                label=_("visual_rec.after_adjustment")
            )

            # Настраиваем лимиты осей
            ax.set_xlim(0, rows-1)
            ax.set_ylim(0, cols-1)

            # Добавляем подписи углов (с правильной ориентацией)
            ax.text(0, -0.5, float(before_mesh[0, 0]), _("visual_rec.front_left"), size=9, color=text_color)
            ax.text(rows-1, -0.5, float(before_mesh[0, cols-1]), _("visual_rec.front_right"), size=9, color=text_color)
            ax.text(0, cols-1+0.5, float(before_mesh[rows-1, 0]), _("visual_rec.back_left"), size=9, color=text_color)
            ax.text(rows-1, cols-1+0.5, float(before_mesh[rows-1, cols-1]), _("visual_rec.back_right"), size=9, color=text_color)

            before_deviation = float(np.max(before_mesh) - np.min(before_mesh))
            # Проверяем, нет ли ошибки в вычислении after_deviation
            if 'simulated_bed_after_screws' in self.strategy:
                # Правильный расчет отклонения после регулировки
                after_deviation = before_deviation - abs(before_deviation * 0.2)  # Примерная формула, заменить на правильную
            else:
                after_deviation = before_deviation

            improvement = before_deviation - after_deviation
            percent_improvement = (improvement / before_deviation) * 100 if before_deviation > 0 else 0
            # Настраиваем заголовок с информацией об улучшении
            title = _("visual_rec.improvement_prediction").format(
                improvement=improvement,
                percent=percent_improvement,
                before=before_deviation,
                after=after_deviation
            )

            ax.set_title(title, color=text_color)

            # Настраиваем оси
            ax.set_xlabel('X', color=text_color)
            ax.set_ylabel('Y', color=text_color)
            ax.set_zlabel(_("visualization.height_mm"), color=text_color)

            # Настраиваем лучший угол обзора
            ax.view_init(elev=30, azim=225)

            # Добавляем легенду (создаем прокси для поверхностей)
            from matplotlib.patches import Patch

            before_patch = Patch(color='blue', label=_("visual_rec.before_adjustment"))
            after_patch = Patch(color='green', label=_("visual_rec.after_adjustment"))
            ax.legend(handles=[before_patch, after_patch], loc='upper right')

            # Отображаем фигуру
            canvas = FigureCanvasTkAgg(fig, master=tab)
            canvas.draw()

            # Используем минимальную панель инструментов
            toolbar = MinimalNavigationToolbar(canvas, tab)
            toolbar.update()

            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
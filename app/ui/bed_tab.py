#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import signal
import sys
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from scipy.interpolate import griddata

from app.ui.visual_recommendations import VisualRecommendationsWindow
from app.ui.language import _, get_language_manager
from visualization.bed_mesh.heatmap_2d import BedMeshHeatmap
from visualization.bed_mesh.surface_3d import BedMesh3D
from calibration.hardware.screw import RotationDirection

class MinimalNavigationToolbar(NavigationToolbar2Tk):
    def __init__(self, canvas, window):
        self.toolitems = []
        NavigationToolbar2Tk.__init__(self, canvas, window)

class BedLevelingTab(ttk.Frame):
    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main = main_window
        self.file_loaded = False
        self.heatmap_2d = BedMeshHeatmap(is_dark_theme=self.main.app_settings.get('theme') == 'dark')
        self.surface_3d = BedMesh3D(is_dark_theme=self.main.app_settings.get('theme') == 'dark')
        self.create_layout()
        self.setup_signal_handler()

    def setup_signal_handler(self):
        def signal_handler(sig, frame):
            print(_("app_title") + ": " + _("status.exit"))
            self.quit()
            sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)

    def create_layout(self):
        instruction_frame = ttk.LabelFrame(self, text=_("Instructions"))
        instruction_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(instruction_frame, text=_("bed_tab.instructions"), justify=tk.LEFT, padding=5).pack(fill=tk.X, padx=5, pady=5)
        
        control_frame = ttk.Frame(self)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Добавляем фрейм для переключателя языков в правом углу
        lang_frame = ttk.Frame(control_frame)
        lang_frame.pack(side=tk.RIGHT, padx=5)

        # Добавляем кнопки переключения языков
        self.en_button = ttk.Button(lang_frame, text="EN", width=3, command=lambda: self.change_language('en'))
        self.en_button.pack(side=tk.LEFT, padx=2)
        self.ru_button = ttk.Button(lang_frame, text="RU", width=3, command=lambda: self.change_language('ru'))
        self.ru_button.pack(side=tk.LEFT, padx=2)

        # Выделяем кнопку текущего языка
        current_lang = get_language_manager().current_language
        if current_lang == 'en':
            self.en_button.state(['pressed'])
        else:
            self.ru_button.state(['pressed'])
        
        ttk.Button(control_frame, text=_("bed_tab.load_config"), command=self.main.load_config, style='Action.TButton').pack(side=tk.LEFT, padx=5)
        self.visual_rec_button = ttk.Button(control_frame, text=_("bed_tab.visual_recommendations"), command=self.show_visual_recommendations, style='Action.TButton', state=tk.DISABLED)
        self.visual_rec_button.pack(side=tk.LEFT, padx=5)
        
        view_frame = ttk.LabelFrame(control_frame, text=_("View"))
        view_frame.pack(side=tk.LEFT, padx=15)
        self.view_var = tk.StringVar(value="2D")
        ttk.Radiobutton(view_frame, text=_("bed_tab.map_2d"), variable=self.view_var, value="2D", command=self.update_visualization).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(view_frame, text=_("bed_tab.map_3d"), variable=self.view_var, value="3D", command=self.update_visualization).pack(side=tk.LEFT, padx=5)
        
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        main_container.grid_columnconfigure(0, weight=7, minsize=500)
        main_container.grid_columnconfigure(1, weight=3, minsize=300)
        main_container.grid_rowconfigure(0, weight=1)
        
        viz_frame = ttk.LabelFrame(main_container, text=_("bed_tab.visualization"))
        viz_frame.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        
        rec_frame = ttk.LabelFrame(main_container, text=_("bed_tab.info_recommendations"))
        rec_frame.grid(row=0, column=1, sticky='nsew', padx=0, pady=0)
        
        self.create_visualization_panel_in_frame(viz_frame)
        self.create_recommendations_panel_in_frame(rec_frame)

    def change_language(self, language_code):
        """
        Меняет язык интерфейса
        
        Args:
            language_code: Код языка ('en' или 'ru')
        """
        # Проверяем, что язык изменился
        lang_manager = get_language_manager()
        if lang_manager.current_language == language_code:
            return
        
        # Устанавливаем новый язык
        if lang_manager.set_language(language_code):
            # Сохраняем выбранный язык в настройках
            self.main.app_settings['language'] = language_code
            self.main.save_app_settings()  # Изменено с save_settings на save_app_settings
            self.main.save_app_settings()  # Заменил второй save_settings на save_app_settings
            
            # Показываем сообщение о необходимости перезапуска
            messagebox.showinfo(
                _("Language Changed"), 
                _("The language has been changed. Please restart the application for the changes to take full effect.")
            )
            
            # Обновляем интерфейс текущей вкладки
            self.refresh_ui()
        else:
            messagebox.showerror(
                _("Error"), 
                _("Failed to change language.")
            )

    def refresh_ui(self):
        """Обновляет интерфейс при смене языка"""
        # Перестраиваем основные элементы интерфейса
        for widget in self.winfo_children():
            widget.destroy()
        
        # Пересоздаем интерфейс
        self.create_layout()
        
        # Если данные загружены, обновляем визуализацию и рекомендации
        if self.file_loaded:
            self.update_visualization()
            self.analyze_bed()
            
    def create_visualization_panel_in_frame(self, frame):
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        
        self.viz_container = ttk.Frame(frame)
        self.viz_container.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        
        empty_label = ttk.Label(self.viz_container, text=_("bed_tab.warning_load_first"), font=('Segoe UI', 12), anchor='center')
        empty_label.place(relx=0.5, rely=0.5, anchor='center')

    def create_recommendations_panel_in_frame(self, frame):
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        
        self.rec_text = tk.Text(frame, wrap=tk.WORD, width=40)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.rec_text.yview)
        self.rec_text.configure(yscrollcommand=scrollbar.set)
        
        self.rec_text.grid(row=0, column=0, sticky='nsew', padx=0, pady=0)
        scrollbar.grid(row=0, column=1, sticky='ns', padx=0, pady=0)
        
        self.rec_text.insert(tk.END, _("bed_tab.initial_recommendations"))
        self.rec_text.configure(state=tk.DISABLED)
        
        self.rec_text.tag_configure("heading", font=("Segoe UI", 10, "bold"))
        self.rec_text.tag_configure("important", foreground="red")
        self.rec_text.tag_configure("success", foreground="green")
        self.rec_text.tag_configure("warning", foreground="orange")

    def on_config_loaded(self, config_content):
        if not self.main.bed:
            return
        
        self.file_loaded = True
        self.visual_rec_button.configure(state=tk.NORMAL)
        self.analyze_bed()
        self.update_visualization()

    def update_visualization(self):
        if not self.file_loaded:
            return
        
        for widget in self.viz_container.winfo_children():
            widget.destroy()
        
        settings = self.main.settings_tab.get_settings()
        interpolation_factor = settings['visualization']['interpolation_factor']
        
        self.heatmap_2d.set_theme(self.main.app_settings.get('theme') == 'dark')
        self.surface_3d.set_theme(self.main.app_settings.get('theme') == 'dark')
        self.surface_3d.set_interpolation_factor(interpolation_factor)
        
        self.heatmap_2d.set_mesh_data(self.main.bed.mesh_data)
        self.surface_3d.set_mesh_data(self.main.bed.mesh_data)
        
        inner_frame = ttk.Frame(self.viz_container)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        container_width = self.viz_container.winfo_width()
        container_height = self.viz_container.winfo_height()
        
        if container_width < 100:
            container_width = int(self.winfo_width() * 0.6)
        if container_height < 100:
            container_height = int(self.winfo_height() * 0.8)
        
        dpi = 96
        fig_width = min(container_width / dpi * 0.9, 7.0)
        fig_height = min(container_height / dpi * 0.9, 5.5)
        
        print(f"Container size: {container_width}x{container_height}, Figure size: {fig_width}x{fig_height} inches")
        
        if self.view_var.get() == "2D":
            fig = self.heatmap_2d.create_2d_figure()
            if fig:
                fig.set_size_inches(fig_width, fig_height)
                canvas = FigureCanvasTkAgg(fig, master=inner_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            fig = self.surface_3d.create_3d_figure()
            if fig:
                fig.set_size_inches(fig_width, fig_height)
                canvas = FigureCanvasTkAgg(fig, master=inner_frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def analyze_bed(self):
        if not self.main.bed or not self.main.analyzer:
            return
        
        try:
            self.max_delta = float(np.max(self.main.bed.mesh_data) - np.min(self.main.bed.mesh_data))
            strategy = self.main.analyzer.find_optimal_strategy()
            
            self.rec_text.configure(state=tk.NORMAL)
            self.rec_text.delete(1.0, tk.END)
            self.show_recommendations(strategy)
            self.rec_text.configure(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror(_("Error"), _("bed_tab.error_during_analysis").format(str(e)))

    def show_recommendations(self, strategy):
        workflow_data = self.main.get_workflow_data(recompute=True)
        settings = self.main.settings_tab.get_settings()
        thresholds = settings['thresholds']
        workflow_flags = settings.get('workflow', {
            'enable_belt': True,
            'enable_screws': True,
            'enable_tape': True
        })

        belt_threshold = float(thresholds.get('belt_threshold', thresholds['screw_threshold']))
        screw_threshold = float(thresholds['screw_threshold'])
        tape_threshold = float(thresholds['tape_threshold'])

        belt_enabled = workflow_flags.get('enable_belt', True)
        screw_enabled = workflow_flags.get('enable_screws', True)
        tape_enabled = workflow_flags.get('enable_tape', True)

        need_belt = belt_enabled and self.max_delta >= belt_threshold
        need_screw = screw_enabled and self.max_delta >= screw_threshold
        need_tape = tape_enabled and self.max_delta >= tape_threshold

        if need_belt:
            status_key = "bed_tab.status_needs_belt"
        elif need_screw:
            status_key = "bed_tab.status_needs_adjustment"
        elif need_tape:
            status_key = "bed_tab.status_needs_tape"
        else:
            status_key = "bed_tab.status_level"

        status_text = f"{_('bed_tab.status_label')} {_(status_key)}\n\n"
        self.rec_text.insert(tk.END, status_text, "heading")

        mean_height = np.mean(self.main.bed.mesh_data)
        metrics_text = (
            _("bed_tab.current_max_deviation").format(self.max_delta)
            + "\n"
            + _("bed_tab.average_height").format(mean_height)
            + "\n\n"
        )
        self.rec_text.insert(tk.END, metrics_text)

        self.rec_text.insert(tk.END, _("bed_tab.action_plan") + "\n", "heading")
        if need_belt:
            self.rec_text.insert(
                tk.END,
                _("bed_tab.action_belts").format(belt_threshold) + "\n",
                "important",
            )
        if need_screw:
            self.rec_text.insert(
                tk.END,
                _("bed_tab.action_screws").format(strategy['deviation_after_screws']) + "\n",
                "important",
            )
        if need_tape:
            action_key = "bed_tab.action_tape" if (need_screw or need_belt) else "bed_tab.action_tape_only"
            self.rec_text.insert(
                tk.END,
                _(action_key).format(strategy['expected_final_deviation']) + "\n",
                "warning",
            )
        if not (need_belt or need_screw or need_tape):
            self.rec_text.insert(tk.END, _("bed_tab.action_none") + "\n", "success")
        self.rec_text.insert(tk.END, "\n")

        stats = self.main.analyzer.get_stats() if self.main.analyzer else None
        corner_pairs = []
        if stats:
            corner_pairs = sorted(
                (
                    (self.main.translate_corner(corner), deviation)
                    for corner, deviation in stats.corner_deviations.items()
                ),
                key=lambda item: item[1],
                reverse=True,
            )

        self.rec_text.insert(tk.END, _("bed_tab.corner_deviations") + "\n\n", "heading")
        for corner, dev in corner_pairs:
            status_icon = "❌" if dev > 0.4 else ("⚠️" if dev > 0.2 else "✅")
            tag_name = "important" if dev > 0.4 else "warning" if dev > 0.2 else "success"
            self.rec_text.insert(
                tk.END,
                f"{status_icon} {corner}: {dev:.3f}mm\n",
                tag_name,
            )

        self.rec_text.insert(
            tk.END,
            "\n" + _("bed_tab.visual_recommendations_details") + "\n",
        )

        if not corner_pairs:
            self.rec_text.insert(tk.END, "\n")

        if workflow_data is None:
            return

        stage_map = {stage.key: stage for stage in workflow_data.stages}

        if belt_enabled:
            self._render_belt_stage(stage_map.get('after_belts'))
        if screw_enabled:
            self._render_screw_stage(stage_map.get('after_screws'))
        if tape_enabled:
            self._render_tape_stage(stage_map.get('after_tape'), settings['hardware']['tape_thickness'])


    def _render_belt_stage(self, stage):
        self.rec_text.insert(tk.END, _('bed_tab.belt_header') + "\n", "heading")
        if stage is None or not stage.enabled:
            self.rec_text.insert(
                tk.END,
                _('bed_tab.belts_disabled') + "\n\n",
                "warning",
            )
            return
        if not stage.actions:
            self.rec_text.insert(
                tk.END,
                _('bed_tab.belt_no_adjustments') + "\n\n",
            )
            return
        for action in stage.actions:
            direction_text = _('bed_tab.belt_direction_up') if action.direction == 'up' else _('bed_tab.belt_direction_down')
            action_text = _('bed_tab.belt_action_tighten') if action.metadata.get('sign', 1.0) >= 0 else _('bed_tab.belt_action_loosen')
            teeth_label = self._teeth_label(action.teeth or 0)
            delta = action.magnitude_mm or 0.0
            self.rec_text.insert(
                tk.END,
                _('bed_tab.belt_instruction').format(
                    corner=_(action.label),
                    action=action_text,
                    teeth=action.teeth or 0,
                    teeth_label=teeth_label,
                    delta=delta,
                    direction=direction_text,
                ) + "\n",
                "important",
            )
        self.rec_text.insert(tk.END, "\n")

    def _render_screw_stage(self, stage):
        self.rec_text.insert(tk.END, _('bed_tab.screw_header') + "\n", "heading")
        if stage is None or not stage.enabled:
            self.rec_text.insert(tk.END, _('bed_tab.screws_disabled') + "\n\n", "warning")
            return
        if not stage.actions:
            self.rec_text.insert(tk.END, _('bed_tab.screw_no_adjustments') + "\n\n")
            return
        for action in stage.actions:
            direction = _('visual_rec.counterclockwise') if action.direction == 'counterclockwise' else _('visual_rec.clockwise')
            minutes = int(round(action.minutes or 0))
            degrees = action.degrees or 0.0
            action_text = _('bed_tab.screw_instruction').format(
                corner=_(action.label),
                direction=direction,
                minutes=minutes,
                degrees=degrees,
                action=_('bed_tab.screw_action_raise') if action.direction == 'counterclockwise' else _('bed_tab.screw_action_lower'),
            )
            self.rec_text.insert(tk.END, action_text + "\n")
        self.rec_text.insert(tk.END, "\n")

    def _render_tape_stage(self, stage, tape_thickness):
        self.rec_text.insert(tk.END, _('bed_tab.tape_header') + "\n", "heading")
        if stage is None or not stage.enabled:
            self.rec_text.insert(tk.END, _('bed_tab.tape_disabled') + "\n\n", "warning")
            return
        if not stage.actions:
            self.rec_text.insert(tk.END, _('bed_tab.tape_no_adjustments') + "\n\n")
            return
        for action in stage.actions:
            layers = action.metadata.get('layers', 0)
            thickness = action.metadata.get('thickness', layers * tape_thickness)
            self.rec_text.insert(
                tk.END,
                _('bed_tab.tape_instruction').format(
                    position=action.label,
                    layers=layers,
                    thickness=thickness,
                ) + "\n",
            )
        self.rec_text.insert(tk.END, "\n")


    def _teeth_label(self, teeth: int) -> str:
        lang = get_language_manager().current_language
        if lang == 'ru':
            if teeth % 10 == 1 and teeth % 100 != 11:
                return _("bed_tab.belt_teeth_one")
            if 2 <= teeth % 10 <= 4 and not 12 <= teeth % 100 <= 14:
                return _("bed_tab.belt_teeth_few")
            return _("bed_tab.belt_teeth_many")
        return _("bed_tab.belt_teeth_one") if teeth == 1 else _("bed_tab.belt_teeth_many")

    def show_visual_recommendations(self):
        if not self.file_loaded:
            messagebox.showwarning(_("Warning"), _("bed_tab.warning_load_first"))
            return
        VisualRecommendationsWindow(self.main, self.main.bed, self.main.analyzer, 
                                  self.main.screw_solver, self.main.tape_calculator)

    def _teeth_label(self, teeth: int) -> str:
        if teeth == 1:
            return _("bed_tab.belt_teeth_one")
        if 2 <= teeth % 10 <= 4 and not 12 <= teeth % 100 <= 14:
            return _("bed_tab.belt_teeth_few")
        return _("bed_tab.belt_teeth_many")

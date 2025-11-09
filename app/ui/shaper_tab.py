import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.gridspec as gridspec
import matplotlib.ticker
import os
import sys
from textwrap import wrap
from typing import Optional

# Добавляем импорт функции локализации
from app.ui.language import _

base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../input_shaper'))
sys.path.append(os.path.join(base_path, 'analysis'))
sys.path.append(os.path.join(base_path, 'analysis/extras'))

import calibrate_shaper
import shaper_calibrate

class ShaperTab(ttk.Frame):
    COLORS = {
        'purple': '#70088C',
        'red': '#FF0000',
        'green': '#00FF00',
        'blue': '#0000FF',
        'cyan': '#00FFFF',
        'darkorange': '#FF8C00',
        'deeppink': '#FF1493',
    }
    SHAPER_COLORS = ['#4682B4', '#32CD32', '#DA70D6', '#FFD700', '#FFA500', '#FF69B4']
    MAX_FREQ = 200.
    MIN_FREQ = 5.

    def __init__(self, parent, main_window):
        super().__init__(parent)
        self.main = main_window
        
        self.calibration_data_x = None
        self.calibration_data_y = None
        self.shapers_x = None
        self.shapers_y = None
        self.selected_shaper_x = None
        self.selected_shaper_y = None
        self.recommendations_text = None
        self.shaper_info_frame = None
        self.shaper_labels_x = []
        self.shaper_labels_y = []
        
        self.create_layout()

    def create_layout(self):
        self.side_frame = ttk.Frame(self, width=250)
        self.side_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        self.graph_frame = ttk.Frame(self)
        self.graph_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.create_side_section()
        self.create_graph_section()
        self.create_result_section()

    def create_side_section(self):
        button_frame = ttk.Frame(self.side_frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text=_("shaper_tab.load_x"), command=lambda: self.load_data('x')).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(button_frame, text=_("shaper_tab.load_y"), command=lambda: self.load_data('y')).pack(fill=tk.X, padx=5, pady=2)
        third_row_frame = ttk.Frame(button_frame)
        third_row_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(third_row_frame, text=_("shaper_tab.what_is_it"), command=self.show_help).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(third_row_frame, text=_("shaper_tab.copy_klipper"), command=self.copy_to_clipboard).pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.status_label = ttk.Label(self.side_frame, text=_("shaper_tab.no_data_loaded"))
        self.status_label.pack(pady=5)

        self.shaper_info_frame = ttk.LabelFrame(self.side_frame, text=_("shaper_tab.recommended_shapers"))
        self.shaper_info_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)

    def create_graph_section(self):
        self.fig = Figure(figsize=(12, 8))
        gs = gridspec.GridSpec(2, 1, height_ratios=[1, 1])
        self.ax_x = self.fig.add_subplot(gs[0])
        self.ax_x2 = self.ax_x.twinx()
        self.ax_y = self.fig.add_subplot(gs[1])
        self.ax_y2 = self.ax_y.twinx()
        self.fig.tight_layout(pad=3.0)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.init_empty_plots()

    def create_result_section(self):
        result_label_frame = ttk.LabelFrame(self.side_frame, text=_("shaper_tab.results_and_settings"))
        result_label_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)

        self.recommendations_text = tk.Text(result_label_frame, height=5, width=30)
        self.recommendations_text.pack(fill=tk.BOTH, padx=5, pady=5)

        self.x_result_frame = ttk.Frame(result_label_frame)
        self.x_result_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(self.x_result_frame, text=_("shaper_tab.axis_x")).pack(side=tk.LEFT)
        self.x_recommend_label = ttk.Label(self.x_result_frame, text=_("shaper_tab.not_analyzed"))
        self.x_recommend_label.pack(side=tk.LEFT, padx=5)

        self.x_shaper_buttons = ttk.Frame(result_label_frame)
        self.x_shaper_buttons.pack(fill=tk.X, pady=2)

        self.y_result_frame = ttk.Frame(result_label_frame)
        self.y_result_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Label(self.y_result_frame, text=_("shaper_tab.axis_y")).pack(side=tk.LEFT)
        self.y_recommend_label = ttk.Label(self.y_result_frame, text=_("shaper_tab.not_analyzed"))
        self.y_recommend_label.pack(side=tk.LEFT, padx=5)

        self.y_shaper_buttons = ttk.Frame(result_label_frame)
        self.y_shaper_buttons.pack(fill=tk.X, pady=2)

    def show_help(self):
        messagebox.showinfo(_("shaper_tab.input_shaper_title"), _("shaper_tab.help_text"))

    def init_empty_plots(self):
        for ax in [self.ax_x, self.ax_x2, self.ax_y, self.ax_y2]:
            ax.clear()
            ax.grid(True, which='major', linestyle='--', color='#666666', alpha=0.6)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        is_dark_theme = self.main.app_settings.get('theme', 'light') == 'dark'
        text_color = 'white' if is_dark_theme else 'black'
        bg_color = '#1e1e1e' if is_dark_theme else 'white'

        if is_dark_theme:
            self.fig.patch.set_facecolor(bg_color)
            for ax in [self.ax_x, self.ax_x2, self.ax_y, self.ax_y2]:
                ax.set_facecolor(bg_color)
                ax.tick_params(colors=text_color)
                ax.xaxis.label.set_color(text_color)
                ax.yaxis.label.set_color(text_color)
                for spine in ax.spines.values():
                    spine.set_edgecolor(text_color)

        self.ax_x.text(0.5, 0.5, _("shaper_tab.no_data_x"), ha='center', va='center', transform=self.ax_x.transAxes, color=text_color)
        self.ax_y.text(0.5, 0.5, _("shaper_tab.no_data_y"), ha='center', va='center', transform=self.ax_y.transAxes, color=text_color)

        self.ax_x.set_xlabel(_("shaper_tab.frequency_hz"), color=text_color)
        self.ax_x.set_ylabel(_("shaper_tab.power_spectral_density"), color=text_color)
        self.ax_y.set_xlabel(_("shaper_tab.frequency_hz"), color=text_color)
        self.ax_y.set_ylabel(_("shaper_tab.power_spectral_density"), color=text_color)
        
        for ax in [self.ax_x, self.ax_y]:
            ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(50))
            ax.yaxis.set_major_locator(matplotlib.ticker.AutoLocator())
            ax.tick_params(colors=text_color)

        self.canvas.draw()
        self.canvas.flush_events()

    def load_data(self, axis):
        file_path = filedialog.askopenfilename(
            title=_("shaper_tab.select_csv").format(axis=axis.upper()),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return
        self.load_data_from_file(file_path, axis_hint=axis)

    def load_data_from_file(self, file_path: str, axis_hint: Optional[str] = None) -> bool:
        try:
            data = calibrate_shaper.parse_log(file_path)
        except Exception as e:
            messagebox.showerror(_("Error"), _("shaper_tab.error_loading").format(str(e)))
            print(f"Error loading file: {e}")
            return False

        axis = axis_hint or self.infer_axis_from_filename(file_path)
        if axis not in {'x', 'y'}:
            # Автоматический выбор: сначала X, затем Y
            axis = 'x' if self.calibration_data_x is None else 'y'

        if axis == 'x':
            self.calibration_data_x = data
            self.status_label.config(text=_("shaper_tab.data_loaded_x").format(len(data.freq_bins)))
        else:
            self.calibration_data_y = data
            self.status_label.config(text=_("shaper_tab.data_loaded_y").format(len(data.freq_bins)))

        self.analyze_data()
        return True

    def infer_axis_from_filename(self, file_path: str) -> Optional[str]:
        name = os.path.basename(file_path).lower()
        if 'axis_x' in name or '_x' in name or '-x' in name:
            return 'x'
        if 'axis_y' in name or '_y' in name or '-y' in name:
            return 'y'
        return None

    def analyze_data(self):
        if not self.calibration_data_x and not self.calibration_data_y:
            return

        for widget in self.shaper_info_frame.winfo_children():
            widget.destroy()

        for label in self.shaper_labels_x + self.shaper_labels_y:
            label.destroy()
        self.shaper_labels_x = []
        self.shaper_labels_y = []

        is_dark_theme = self.main.app_settings.get('theme', 'light') == 'dark'
        text_color = 'white' if is_dark_theme else 'black'
        bg_color = '#1e1e1e' if is_dark_theme else 'white'
        print(f"Applying theme: {'dark' if is_dark_theme else 'light'}, text_color: {text_color}, bg_color: {bg_color}")

        try:
            recommendations = _("shaper_tab.setup_recommendations")
            
            if self.calibration_data_x:
                print(_("shaper_tab.analyzing_x"))
                if not isinstance(self.calibration_data_x, shaper_calibrate.CalibrationData):
                    self.calibration_data_x = shaper_calibrate.ShaperCalibrate(None).process_accelerometer_data(self.calibration_data_x)
                selected_shaper_x, shapers_x, calibration_data_x = calibrate_shaper.calibrate_shaper(
                    [self.calibration_data_x], csv_output=None, max_smoothing=None
                )
                print(_("shaper_tab.recommended_for_x").format(selected_shaper_x, next(s.freq for s in shapers_x if s.name == selected_shaper_x)))
                self.selected_shaper_x = selected_shaper_x
                self.shapers_x = shapers_x
                self.calibration_data_x = calibration_data_x
                recommendations += _("shaper_tab.axis_x") + ": " + _("shaper_tab.recommended_for_x").format(selected_shaper_x.upper(), next(s.freq for s in self.shapers_x if s.name == selected_shaper_x)) + "\n"
                self.create_shaper_buttons('x')
                fig_x = calibrate_shaper.plot_freq_response(
                    ["X"], self.calibration_data_x, self.shapers_x, self.selected_shaper_x, self.MAX_FREQ
                )

                self.ax_x.clear()
                self.ax_x2.clear()
                self.ax_x.grid(True, which='major', linestyle='--', color='#666666', alpha=0.6)
                self.ax_x2.grid(False)
                self.ax_x.spines['top'].set_visible(False)
                self.ax_x.spines['right'].set_visible(False)
                self.ax_x2.spines['top'].set_visible(False)
                self.ax_x2.spines['right'].set_visible(False)
                for ax in [self.ax_x, self.ax_x2]:
                    ax.set_facecolor(bg_color)
                    ax.tick_params(colors=text_color)
                    ax.xaxis.label.set_color(text_color)
                    ax.yaxis.label.set_color(text_color)
                    for spine in ax.spines.values():
                        spine.set_edgecolor(text_color)

                for ax in fig_x.axes:
                    if ax.get_ylabel() == 'Power spectral density':
                        self.ax_x.set_xlim(ax.get_xlim())
                        self.ax_x.set_ylim(ax.get_ylim())
                        self.ax_x.set_xlabel(_("shaper_graphs.frequency_hz"), color=text_color)
                        self.ax_x.set_ylabel(_("shaper_graphs.power_spectral_density"), color=text_color)
                        lines = ax.get_lines()
                        labels = [line.get_label() for line in lines]
                        print(f"All labels in Power spectral density: {labels}")
                        for i, line in enumerate(lines):
                            label = line.get_label()
                            print(f"Line {i} label: {label}, original color: {line.get_color()}")
                            cleaned_label = label.replace('\n', ' ').strip()
                            if cleaned_label == 'After shaper':
                                self.ax_x.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                               color=text_color, linewidth=2, alpha=0.8)
                                print(f"Fixed After shaper color to: {text_color}")
                            else:
                                self.ax_x.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                               color=self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)], 
                                               linewidth=2, alpha=0.8)
                        self.ax_x.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(50))
                        self.ax_x.yaxis.set_major_locator(matplotlib.ticker.AutoLocator())
                        self.ax_x.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
                        self.ax_x.tick_params(colors=text_color)
                        self.ax_x.legend(loc='upper right', fontsize=8, labelcolor=text_color, 
                                         frameon=False, framealpha=0, bbox_to_anchor=(0.99, 0.99))
                    elif ax.get_ylabel() == 'Shaper vibration reduction (ratio)':
                        self.ax_x2.set_ylim(ax.get_ylim())
                        
                        for i, line in enumerate(ax.get_lines()):
                            label = line.get_label()
                            print(f"Shaper vibration reduction line {i} label: {label}")
                            if not label or label.startswith('_'):
                                label = self.shapers_x[i].name.upper() if i < len(self.shapers_x) else f"Unknown {i}"
                            self.ax_x2.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                            linestyle=line.get_linestyle(), 
                                            color=self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)], 
                                            linewidth=2, alpha=0.8)
                        self.ax_x2.tick_params(colors=text_color)
                        self.ax_x2.legend().remove()
                self.canvas.draw()
                plt.close(fig_x)

                ttk.Label(self.shaper_info_frame, text=_("shaper_tab.axis_x"), font=("Arial", 10, "bold")).pack(anchor="w")
                ttk.Label(self.shaper_info_frame, text=_("shaper_tab.recommended").format(selected_shaper_x.upper()), 
                          font=("Arial", 10, "bold"), foreground="green").pack(anchor="w")
                
                for i, shaper in enumerate(self.shapers_x):
                    label = f"{shaper.name.upper()} ({shaper.freq:.1f} Hz, vibr={shaper.vibrs*100:.1f}%, sm~={shaper.smoothing:.2f}, accel<={round(shaper.max_accel/100.)*100:.0f})"
                    color = self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)]
                    shaper_frame = ttk.Frame(self.shaper_info_frame)
                    shaper_frame.pack(fill=tk.X, pady=2)
                    color_label = ttk.Label(shaper_frame, text="■", font=("Arial", 12), foreground=color)
                    color_label.pack(side=tk.LEFT)
                    text_label = ttk.Label(shaper_frame, text=label, font=("Arial", 10))
                    text_label.pack(side=tk.LEFT)
                    self.shaper_labels_x.append(shaper_frame)

            if self.calibration_data_y:
                print(_("shaper_tab.analyzing_y"))
                if not isinstance(self.calibration_data_y, shaper_calibrate.CalibrationData):
                    self.calibration_data_y = shaper_calibrate.ShaperCalibrate(None).process_accelerometer_data(self.calibration_data_y)
                selected_shaper_y, shapers_y, calibration_data_y = calibrate_shaper.calibrate_shaper(
                    [self.calibration_data_y], csv_output=None, max_smoothing=None
                )
                print(_("shaper_tab.recommended_for_y").format(selected_shaper_y, next(s.freq for s in shapers_y if s.name == selected_shaper_y)))
                self.selected_shaper_y = selected_shaper_y
                self.shapers_y = shapers_y
                self.calibration_data_y = calibration_data_y
                recommendations += _("shaper_tab.axis_y") + ": " + _("shaper_tab.recommended_for_y").format(selected_shaper_y.upper(), next(s.freq for s in self.shapers_y if s.name == selected_shaper_y)) + "\n"
                self.create_shaper_buttons('y')
                fig_y = calibrate_shaper.plot_freq_response(
                    ["Y"], self.calibration_data_y, self.shapers_y, self.selected_shaper_y, self.MAX_FREQ
                )

                self.ax_y.clear()
                self.ax_y2.clear()
                self.ax_y.grid(True, which='major', linestyle='--', color='#666666', alpha=0.6)
                self.ax_y2.grid(False)
                self.ax_y.spines['top'].set_visible(False)
                self.ax_y.spines['right'].set_visible(False)
                self.ax_y2.spines['top'].set_visible(False)
                self.ax_y2.spines['right'].set_visible(False)
                for ax in [self.ax_y, self.ax_y2]:
                    ax.set_facecolor(bg_color)
                    ax.tick_params(colors=text_color)
                    ax.xaxis.label.set_color(text_color)
                    ax.yaxis.label.set_color(text_color)
                    for spine in ax.spines.values():
                        spine.set_edgecolor(text_color)

                for ax in fig_y.axes:
                    if ax.get_ylabel() == 'Power spectral density':
                        self.ax_y.set_xlim(ax.get_xlim())
                        self.ax_y.set_ylim(ax.get_ylim())
                        self.ax_y.set_xlabel(_("shaper_graphs.frequency_hz"), color=text_color)
                        self.ax_y.set_ylabel(_("shaper_graphs.power_spectral_density"), color=text_color)
                        lines = ax.get_lines()
                        labels = [line.get_label() for line in lines]
                        print(f"All labels in Power spectral density: {labels}")
                        for i, line in enumerate(lines):
                            label = line.get_label()
                            print(f"Line {i} label: {label}, original color: {line.get_color()}")
                            cleaned_label = label.replace('\n', ' ').strip()
                            if cleaned_label == 'After shaper':
                                self.ax_y.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                               color=text_color, linewidth=2, alpha=0.8)
                                print(f"Fixed After shaper color to: {text_color}")
                            else:
                                self.ax_y.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                               color=self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)], 
                                               linewidth=2, alpha=0.8)
                        self.ax_y.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(50))
                        self.ax_y.yaxis.set_major_locator(matplotlib.ticker.AutoLocator())
                        self.ax_y.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
                        self.ax_y.tick_params(colors=text_color)
                        self.ax_y.legend(loc='upper right', fontsize=8, labelcolor=text_color, 
                                         frameon=False, framealpha=0, bbox_to_anchor=(0.99, 0.99))
                    elif ax.get_ylabel() == 'Shaper vibration reduction (ratio)':
                        self.ax_y2.set_ylim(ax.get_ylim())
                        
                        for i, line in enumerate(ax.get_lines()):
                            label = line.get_label()
                            print(f"Shaper vibration reduction line {i} label: {label}")
                            if not label or label.startswith('_'):
                                label = self.shapers_y[i].name.upper() if i < len(self.shapers_y) else f"Unknown {i}"
                            self.ax_y2.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                            linestyle=line.get_linestyle(), 
                                            color=self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)], 
                                            linewidth=2, alpha=0.8)
                        self.ax_y2.tick_params(colors=text_color)
                        self.ax_y2.legend().remove()
                self.canvas.draw()
                plt.close(fig_y)

                ttk.Label(self.shaper_info_frame, text=_("shaper_tab.axis_y"), font=("Arial", 10, "bold")).pack(anchor="w")
                ttk.Label(self.shaper_info_frame, text=_("shaper_tab.recommended").format(selected_shaper_y.upper()), 
                          font=("Arial", 10, "bold"), foreground="green").pack(anchor="w")
                
                for i, shaper in enumerate(self.shapers_y):
                    label = f"{shaper.name.upper()} ({shaper.freq:.1f} Hz, vibr={shaper.vibrs*100:.1f}%, sm~={shaper.smoothing:.2f}, accel<={round(shaper.max_accel/100.)*100:.0f})"
                    color = self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)]
                    shaper_frame = ttk.Frame(self.shaper_info_frame)
                    shaper_frame.pack(fill=tk.X, pady=2)
                    color_label = ttk.Label(shaper_frame, text="■", font=("Arial", 12), foreground=color)
                    color_label.pack(side=tk.LEFT)
                    text_label = ttk.Label(shaper_frame, text=label, font=("Arial", 10))
                    text_label.pack(side=tk.LEFT)
                    self.shaper_labels_y.append(shaper_frame)

            self.x_recommend_label.config(text=_("shaper_tab.recommended").format(self.selected_shaper_x.upper()) if self.shapers_x else _("shaper_tab.not_analyzed"))
            self.y_recommend_label.config(text=_("shaper_tab.recommended").format(self.selected_shaper_y.upper()) if self.shapers_y else _("shaper_tab.not_analyzed"))
            self.recommendations_text.delete(1.0, tk.END)
            self.recommendations_text.insert(tk.END, recommendations + _("shaper_tab.select_and_copy"))

        except Exception as e:
            print(f"Exception during analysis: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror(_("Error"), _("shaper_tab.analysis_complete").format(str(e)))

    def create_shaper_buttons(self, axis):
        shapers = self.shapers_x if axis == 'x' else self.shapers_y
        button_frame = self.x_shaper_buttons if axis == 'x' else self.y_shaper_buttons
        selected_shaper = self.selected_shaper_x if axis == 'x' else self.selected_shaper_y

        for widget in button_frame.winfo_children():
            widget.destroy()

        for shaper in shapers:
            button_text = shaper.name.upper()
            ttk.Button(
                button_frame,
                text=button_text,
                command=lambda name=shaper.name, a=axis: self.select_shaper(name, a),
                style='Shaper.TButton' if shaper.name == selected_shaper else 'TButton',
                width=6
            ).pack(side=tk.LEFT, padx=2)

        ttk.Style().configure('Shaper.TButton', background='lightgreen')

    def select_shaper(self, shaper_name, axis):
        is_dark_theme = self.main.app_settings.get('theme', 'light') == 'dark'
        text_color = 'white' if is_dark_theme else 'black'
        bg_color = '#1e1e1e' if is_dark_theme else 'white'
        print(f"Applying theme in select_shaper: {'dark' if is_dark_theme else 'light'}, text_color: {text_color}, bg_color: {bg_color}")

        if axis == 'x':
            self.selected_shaper_x = shaper_name
            if self.calibration_data_x:
                fig_x = calibrate_shaper.plot_freq_response(
                    ["X"], self.calibration_data_x, self.shapers_x, self.selected_shaper_x, self.MAX_FREQ
                )

                self.ax_x.clear()
                self.ax_x2.clear()
                self.ax_x.grid(True, which='major', linestyle='--', color='#666666', alpha=0.6)
                self.ax_x2.grid(False)
                self.ax_x.spines['top'].set_visible(False)
                self.ax_x.spines['right'].set_visible(False)
                self.ax_x2.spines['top'].set_visible(False)
                self.ax_x2.spines['right'].set_visible(False)
                for ax in [self.ax_x, self.ax_x2]:
                    ax.set_facecolor(bg_color)
                    ax.tick_params(colors=text_color)
                    ax.xaxis.label.set_color(text_color)
                    ax.yaxis.label.set_color(text_color)
                    for spine in ax.spines.values():
                        spine.set_edgecolor(text_color)

                for ax in fig_x.axes:
                    if ax.get_ylabel() == 'Power spectral density':
                        self.ax_x.set_xlim(ax.get_xlim())
                        self.ax_x.set_ylim(ax.get_ylim())
                        self.ax_x.set_xlabel(_("shaper_graphs.frequency_hz"), color=text_color)
                        self.ax_x.set_ylabel(_("shaper_graphs.power_spectral_density"), color=text_color)
                        lines = ax.get_lines()
                        labels = [line.get_label() for line in lines]
                        print(f"All labels in Power spectral density: {labels}")
                        for i, line in enumerate(lines):
                            label = line.get_label()
                            print(f"Line {i} label: {label}, original color: {line.get_color()}")
                            cleaned_label = label.replace('\n', ' ').strip()
                            if cleaned_label == 'After shaper':
                                self.ax_x.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                               color=text_color, linewidth=2, alpha=0.8)
                                print(f"Fixed After shaper color to: {text_color}")
                            else:
                                self.ax_x.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                               color=self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)], 
                                               linewidth=2, alpha=0.8)
                        self.ax_x.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(50))
                        self.ax_x.yaxis.set_major_locator(matplotlib.ticker.AutoLocator())
                        self.ax_x.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
                        self.ax_x.tick_params(colors=text_color)
                        self.ax_x.legend(loc='upper right', fontsize=8, labelcolor=text_color, 
                                         frameon=False, framealpha=0, bbox_to_anchor=(0.99, 0.99))
                    elif ax.get_ylabel() == 'Shaper vibration reduction (ratio)':
                        self.ax_x2.set_ylim(ax.get_ylim())
                        self.ax_x2.set_ylabel(_("shaper_graphs.vibration_reduction"), color=text_color)
                        for i, line in enumerate(ax.get_lines()):
                            label = line.get_label()
                            print(f"Shaper vibration reduction line {i} label: {label}")
                            if not label or label.startswith('_'):
                                label = self.shapers_x[i].name.upper() if i < len(self.shapers_x) else f"Unknown {i}"
                            self.ax_x2.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                            linestyle=line.get_linestyle(), 
                                            color=self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)], 
                                            linewidth=2, alpha=0.8)
                        self.ax_x2.tick_params(colors=text_color)
                        self.ax_x2.legend().remove()
                self.canvas.draw()
                plt.close(fig_x)
        else:
            self.selected_shaper_y = shaper_name
            if self.calibration_data_y:
                fig_y = calibrate_shaper.plot_freq_response(
                    ["Y"], self.calibration_data_y, self.shapers_y, self.selected_shaper_y, self.MAX_FREQ
                )

                self.ax_y.clear()
                self.ax_y2.clear()
                self.ax_y.grid(True, which='major', linestyle='--', color='#666666', alpha=0.6)
                self.ax_y2.grid(False)
                self.ax_y.spines['top'].set_visible(False)
                self.ax_y.spines['right'].set_visible(False)
                self.ax_y2.spines['top'].set_visible(False)
                self.ax_y2.spines['right'].set_visible(False)
                for ax in [self.ax_y, self.ax_y2]:
                    ax.set_facecolor(bg_color)
                    ax.tick_params(colors=text_color)
                    ax.xaxis.label.set_color(text_color)
                    ax.yaxis.label.set_color(text_color)
                    for spine in ax.spines.values():
                        spine.set_edgecolor(text_color)

                for ax in fig_y.axes:
                    if ax.get_ylabel() == 'Power spectral density':
                        self.ax_y.set_xlim(ax.get_xlim())
                        self.ax_y.set_ylim(ax.get_ylim())
                        self.ax_y.set_xlabel(_("shaper_graphs.frequency_hz"), color=text_color)
                        self.ax_y.set_ylabel(_("shaper_graphs.power_spectral_density"), color=text_color)
                        lines = ax.get_lines()
                        labels = [line.get_label() for line in lines]
                        print(f"All labels in Power spectral density: {labels}")
                        for i, line in enumerate(lines):
                            label = line.get_label()
                            print(f"Line {i} label: {label}, original color: {line.get_color()}")
                            cleaned_label = label.replace('\n', ' ').strip()
                            if cleaned_label == 'After shaper':
                                self.ax_y.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                               color=text_color, linewidth=2, alpha=0.8)
                                print(f"Fixed After shaper color to: {text_color}")
                            else:
                                self.ax_y.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                               color=self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)], 
                                               linewidth=2, alpha=0.8)
                        self.ax_y.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(50))
                        self.ax_y.yaxis.set_major_locator(matplotlib.ticker.AutoLocator())
                        self.ax_y.ticklabel_format(axis='y', style='scientific', scilimits=(0, 0))
                        self.ax_y.tick_params(colors=text_color)
                        self.ax_y.legend(loc='upper right', fontsize=8, labelcolor=text_color, 
                                         frameon=False, framealpha=0, bbox_to_anchor=(0.99, 0.99))
                    elif ax.get_ylabel() == 'Shaper vibration reduction (ratio)':
                        self.ax_y2.set_ylim(ax.get_ylim())
                        self.ax_y2.set_ylabel(_("shaper_graphs.vibration_reduction"), color=text_color)
                        for i, line in enumerate(ax.get_lines()):
                            label = line.get_label()
                            print(f"Shaper vibration reduction line {i} label: {label}")
                            if not label or label.startswith('_'):
                                label = self.shapers_y[i].name.upper() if i < len(self.shapers_y) else f"Unknown {i}"
                            self.ax_y2.plot(line.get_xdata(), line.get_ydata(), label=label, 
                                            linestyle=line.get_linestyle(), 
                                            color=self.SHAPER_COLORS[i % len(self.SHAPER_COLORS)], 
                                            linewidth=2, alpha=0.8)
                        self.ax_y2.tick_params(colors=text_color)
                        self.ax_y2.legend().remove()
                self.canvas.draw()
                plt.close(fig_y)
        self.create_shaper_buttons(axis)

    def copy_to_clipboard(self):
        if not self.shapers_x and not self.shapers_y:
            messagebox.showwarning(_("Warning"), _("shaper_tab.perform_analysis_first"))
            return

        x_shaper = self.selected_shaper_x if self.selected_shaper_x else 'mzv'
        x_freq = next((s.freq for s in self.shapers_x if s.name == self.selected_shaper_x), 45.0) if self.shapers_x else 45.0
        y_shaper = self.selected_shaper_y if self.selected_shaper_y else 'mzv'
        y_freq = next((s.freq for s in self.shapers_y if s.name == self.selected_shaper_y), 45.0) if self.shapers_y else 45.0

        config_text = (
            "[input_shaper]\n"
            f"shaper_type_x = {x_shaper}\n"
            f"shaper_freq_x = {x_freq:.1f}\n"
            f"shaper_type_y = {y_shaper}\n"
            f"shaper_freq_y = {y_freq:.1f}\n"
        )

        self.clipboard_clear()
        self.clipboard_append(config_text)
        messagebox.showinfo(_("Copied"), _("shaper_tab.copied"))

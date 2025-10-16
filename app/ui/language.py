#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Dict, List, Tuple, Any
import json
import os
import logging

def _(key, default=None):
    return get_language_manager().get_text(key, default)

_language_manager = None

def get_language_manager():
    global _language_manager
    if (_language_manager is None):
        _language_manager = LanguageManager()
    return _language_manager

class LanguageManager:
    def __init__(self, default_language='en'):
        self.languages = {}
        self.current_language = default_language
        self.default_language = default_language
        self.load_languages()
        
    def load_languages(self):
        languages_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'languages')
        if not os.path.exists(languages_dir):
            os.makedirs(languages_dir)
            self._create_default_language_files(languages_dir)
        
        for filename in os.listdir(languages_dir):
            if filename.endswith('.json'):
                language_code = filename.split('.')[0]
                with open(os.path.join(languages_dir, filename), 'r', encoding='utf-8') as f:
                    try:
                        self.languages[language_code] = json.load(f)
                    except json.JSONDecodeError:
                        logging.error(f"Error loading language file: {filename}")
                        
        if not self.languages or self.default_language not in self.languages:
            self._create_default_language_files(languages_dir)
            self.load_languages()
            
    def _create_default_language_files(self, languages_dir):
        en_strings = {

            "Language Changed": "Language Changed",
            "The language has been changed. Please restart the application for the changes to take full effect.": "The language has been changed. Please restart the application for the changes to take full effect.",
            "Failed to change language.": "Failed to change language.",
            "app_title": "Flashforge Calibration Assistant",
            "menu": {
                "file": "File",
                "open_config": "Open Config",
                "exit": "Exit",
                "view": "View",
                "light_theme": "Light Theme",
                "dark_theme": "Dark Theme",
                "tools": "Tools",
                "visual_recommendations": "Visual Recommendations",
                "ssh_settings": "SSH Settings",
                "help": "Help",
                "about": "About",
                "language": "Language"
            },
            "status": {
                "ready": "Ready",
                "loading": "Loading file: {}",
                "success": "File loaded successfully",
                "error": "Error loading file",
                "exit": "Interrupt Ctrl+C received. Closing application..."
            },
            "tabs": {
                "bed_leveling": "Bed Leveling",
                "input_shaper": "Input Shaper",
                "settings": "Settings"
            },
            "bed_tab": {
                "load_config": "Load Configuration",
                "map_2d": "2D Map",
                "map_3d": "3D Map",
                "visual_recommendations": "Visual Recommendations",
                "visualization": "Visualization",
                "info_recommendations": "Information and Recommendations",
                "warning_load_first": "Please load data first",
                "instructions": "IMPORTANT:\n• FRONT side of the bed - closer to you\n• BACK side - further from you\n\n1. Load the printer.cfg file\n2. TURN THE SCREWS HOLD THE NUTS!!! Use visualization to analyze the bed\n3. Follow the adjustment recommendations",
                "initial_recommendations": "Recommendations for bed leveling will be displayed here\nafter loading the configuration file.\n\nTo begin, press the\n'Load Configuration' button.",
                "status_label": "STATUS:",
                "status_level": "✅ Bed is level",
                "status_needs_adjustment": "❌ Screw adjustment needed",
                "status_needs_belt": "❗ Z lead screw sync required",
                "status_needs_tape": "⚠️ Tape correction needed",
                "current_max_deviation": "Current max deviation: {:.3f}mm",
                "average_height": "Average height: {:.3f}mm",
                "action_plan": "Recommended action plan:",
                "action_belts": "1. Synchronise Z lead screws (bring delta below {:.3f}mm)",
                "action_screws": "2. Adjust screws (target {:.3f}mm)",
                "action_tape": "3. Apply tape (target {:.3f}mm)",
                "action_tape_only": "1. Apply tape (target {:.3f}mm)",
                "action_none": "No adjustments needed",
                "corner_deviations": "Corner deviations:",
                "visual_recommendations_details": "Use visual recommendations for details",
                "belt_header": "Stage 1: Synchronise Z lead screws",
                "belt_instruction": "{corner}: {action} by {teeth} {teeth_label} (~{delta:.2f} mm). Turn {direction}.",
                "belt_direction_up": "counterclockwise (raises corner)",
                "belt_direction_down": "clockwise (lowers corner)",
                "belt_action_tighten": "tighten",
                "belt_action_loosen": "loosen",
                "belt_no_adjustments": "Z lead screws appear balanced.",
                "belts_disabled": "Z lead screw stage disabled in settings.",
                "screw_header": "Stage 2: Screw adjustments",
                "screw_instruction": "{corner}: turn {direction} by {minutes} min ({degrees:.0f}°). Action: {action}.",
                "screw_action_raise": "raise the corner",
                "screw_action_lower": "lower the corner",
                "screw_no_adjustments": "Screw adjustments not required.",
                "screws_disabled": "Screw stage disabled in settings.",
                "tape_header": "Stage 3: Tape compensation",
                "tape_instruction": "{position}: {layers} layer(s) (~{thickness:.2f} mm)",
                "tape_no_adjustments": "Area is within tolerance – no tape needed.",
                "tape_disabled": "Tape stage disabled in settings.",
                "belt_teeth_one": "tooth",
                "belt_teeth_many": "teeth",
                "error_during_analysis": "Error during analysis: {}"
            },
            "shaper_tab": {
                    "load_x": "Load X-axis Data",
                    "load_y": "Load Y-axis Data",
                    "what_is_it": "What is it?",
                    "copy_klipper": "Copy for settings",
                    "recommended_shapers": "Recommended Shaper Types",
                    "results_and_settings": "Results and Settings",
                    "axis_x": "X-axis:",
                    "axis_y": "Y-axis:",
                    "frequency": "Frequency:",
                    "no_data_loaded": "No data loaded",
                    "not_analyzed": "Not analyzed",
                    "data_loaded_x": "X-axis data loaded ({} points)",
                    "data_loaded_y": "Y-axis data loaded ({} points)",
                    "analysis_complete": "Analysis complete. Recommended shaper parameters updated.",
                    "copied": "Configuration copied to clipboard.\nPaste it into your printer.cfg file.",
                    "raw_signal_x": "X-axis - Raw Signal",
                    "raw_signal_y": "Y-axis - Raw Signal",
                    "spectrum_x": "Spectrum (X)",
                    "spectrum_y": "Spectrum (Y)",
                    "time": "Time (s)",
                    "acceleration": "Acceleration",
                    "frequency_hz": "Frequency (Hz)",
                    "power_spectral_density": "Power Spectral Density",
                    "vibration_reduction": "Vibration Reduction (ratio)",
                    "amplitude": "Amplitude",
                    "no_data_x": "No data for X-axis",
                    "no_data_y": "No data for Y-axis",
                    "help_text": "Input Shaper is a technology that helps reduce vibrations in a 3D printer during printing.\n\nVibrations can cause defects on the model, such as 'ghosting'. Input Shaper analyzes the printer's movements and adjusts them to minimize these vibrations.\n\nHow it works?\n1. Load accelerometer data.\n2. The program selects the best 'shaper'.\n3. Copy the settings.\n\nResult: smoother printing and fewer defects!",
                    "setup_recommendations": "Recommendations for setup:\n\n",
                    "analyzing_x": "Analyzing X axis...",
                    "analyzing_y": "Analyzing Y axis...",
                    "recommended_for_x": "Recommended shaper for X: {} @ {:.1f} Hz",
                    "recommended_for_y": "Recommended shaper for Y: {} @ {:.1f} Hz",
                    "select_and_copy": "Select a shaper and copy the settings!",
                    "recommended": "Recommended: {}",
                    "input_shaper_title": "What is Input Shaper?",
                    "perform_analysis_first": "Perform analysis first!",
                    "select_csv": "Select CSV file for axis {axis}",
                    "error_loading": "Error loading file:\n{}",
                },
            "settings_tab": {
                "hardware": "Hardware",
                "thresholds": "Thresholds",
                "ssh": "SSH",
                "visualization": "Visualization",
                "environment": "Environment",
                "workflow": "Workflow",
                "screw_pitch": "M4 screw pitch (mm):",
                "min_adjustment": "Min adjustment (mm):",
                "max_adjustment": "Max adjustment (mm):",
                "tape_thickness": "Tape thickness (mm):",
                "belt_tooth_mm": "Belt pitch per tooth (mm):",
                "belt_threshold": "Belt adjustment threshold (mm):",
                "screw_threshold": "Screw threshold (mm):",
                "tape_threshold": "Tape threshold (mm):",
                "host": "Host:",
                "username": "Username:",
                "password": "Password:",
                "test_connection": "Test Connection",
                "get_printer_cfg": "Get printer.cfg",
                "get_shapers": "Get shapers",
                "interpolation_factor": "Interpolation factor:",
                "show_minutes": "Show minutes",
                "show_degrees": "Show degrees",
                "measurement_temp": "Measurement temperature (°C):",
                "target_temp": "Target temperature (°C):",
                "thermal_coeff": "Thermal deformation coefficient (mm/°C):",
                "enable_belt": "Stage 1 – Adjust Z lead screws",
                "enable_screws": "Stage 2 – Adjust screws",
                "enable_tape": "Stage 3 – Apply tape",
                "save": "Save",
                "reset": "Reset",
                "settings_saved": "Settings saved",
                "numeric_error": "Check numeric values for correctness",
                "fill_ssh": "Fill in all SSH fields",
                "connection_success": "SSH connection successful",
                "connection_error": "Connection error: {}",
                "fill_printer_cfg": "Printer configuration downloaded: {}",
                "fill_shapers": "Shaper files downloaded:\n{}",
                "no_shapers_found": "No shaper files were found on the printer.",
                "ssh_connection_desc": "SSH connection allows automatic loading of configuration files and calibration data directly from your printer",
                "connection_requirements": "For connection, the following is required:",
                "ip_or_hostname": "IP address or printer hostname",
                "username_desc": "Username (usually 'root')",
                "password_desc": "Password for access",
                "interpolation_factor_desc": "Interpolation factor determines the smoothness of 3D visualization (higher value = prettier graph, but more load)",
                "hardware_info": "• Screw pitch determines how much height changes per full turn\n• Tape thickness affects the calculation of layers for compensation\n• Min/max adjustment limits the range of suggested changes",
                "thresholds_info": "1. If deviation > screw threshold, the program suggests screw adjustment\n2. If after screw adjustment deviation > tape threshold,\n   the program suggests additional tape correction\n3. If deviation < screw threshold but > tape threshold,\n   the program suggests only tape correction",
                "visualization_info": "• Interpolation factor determines the smoothness of 3D visualization\n  (higher value = prettier graph, but more load)\n\n• Display settings allow choosing units for screw adjustment instructions (minutes and/or degrees)",
                "display_options_error": "At least one display option (minutes or degrees) must be enabled.\nBoth options have been enabled by default.",
                "environment_info": "Temperature difference between measurement and printing can warp the bed.\nUse the coefficient to control the strength and direction of the simulated dome (negative values invert the curvature)."
            },
            "visual_rec": {
                "title": "Visual Recommendations",
                "problem_map": "Problem Areas Map",
                "screw_scheme": "Screw Adjustment Scheme",
                "tape_scheme": "Tape Application Scheme",
                "prediction": "Predicted Changes",
                "temperature_tab": "Thermal behaviour",
                "temperature_map_title": "Predicted thermal warp {measure:.0f}°C → {target:.0f}°C (coeff {coeff:.1e})",
                "temperature_delta_label": "Warp, mm",
                "temperature_map_hint": "Red areas rise after heating, blue areas drop. Compare with a hot mesh to confirm.",
                "temperature_hot_surface": "After heating",
                "high_points": "High Points",
                "low_points": "Low Points",
                "clockwise": "clockwise",
                "counterclockwise": "counterclockwise",
                "instructions": "IMPORTANT! Bed orientation:\n• FRONT side - closer to you (where the control panel is)\n• BACK side - further from you (rear of the printer)\n\n1. Locate the four corner screws on your bed (see screw adjustment scheme).\n2. Clockwise rotation LOWERS the corner, counterclockwise RAISES the corner.\n3. After adjusting screws, follow the tape application scheme for final correction.\n4. After all adjustments, re-measure the bed to verify results.",
                "hardware_settings_summary": "Hardware settings: screw pitch {pitch:.2f} mm • min adjustment {min_adjust:.2f} mm • max adjustment {max_adjust:.2f} mm • tape thickness {tape:.2f} mm",
                "drag_hint": "Tip: drag the tab headers to rearrange the recommendation cards.",
                "temperature_summary": "Temperature: measured at {measurement:.1f}°C → target {target:.1f}°C • thermal coefficient {coeff:.5f} mm/°C",
                "belt_scheme": "Z Lead Screw/Belt Adjustment",
                "belt_scheme_tab": "Z shaft schematic",
                "belt_stage_title": "Stage 1: Synchronise Z lead screws",
                "belt_stage_description": "Use the guidance below to balance the three Z lead screws before fine screw and tape adjustments.",
                "belt_action_tighten": "Tighten",
                "belt_action_loosen": "Loosen",
                "belt_action_ok": "In tolerance",
                "belt_rotation_ccw": "Turn the shaft counterclockwise (raises the gantry)",
                "belt_rotation_cw": "Turn the shaft clockwise (lowers the gantry)",
                "belt_instruction_overview": "Sequence:\n1. Power off the printer\n2. Lay printer on its back\n3. Loosen the tensioner lock bolts before turning the screws",
                "belt_instruction_finish": "After adjustment:\n• Re-tension the belts\n• Return the printer upright\n• Re-run the bed mesh",
                "belt_no_action": "Z lead screws appear balanced.",
                "belt_teeth_count": "Teeth to move: {count}",
                "front_left": "Front Left",
                "front_right": "Front Right",
                "back_left": "Back Left",
                "back_right": "Back Right",
                "back_center": "Back Center",
                "normal": "Normal",
                "minutes_label": "{value:.1f} min",
                "degrees_label": "{value:.1f}°",
                "height_delta": "Height change: {value:+.2f} mm",
                "corner_height": "Current {current:.3f} mm → Target {target:.3f} mm",
                "spot_height_diff": "{value:.2f} mm",
                "tape_instruction_title": "INSTRUCTION:",
                "tape_instruction_1": "1. Use aluminum tape with a thickness of ~0.06mm",
                "tape_instruction_2": "2. Apply tape at the indicated locations",
                "tape_instruction_3": "3. The number indicates the NUMBER OF LAYERS of tape",
                "tape_instruction_4": "4. After applying, perform a re-measurement",
                "tape_layers_legend": "NUMBER OF LAYERS",
                "tape_layer_1": "1 layer",
                "tape_layer_2": "2 layers",
                "tape_layer_3": "3 layers",
                "tape_scheme_with_points": "Tape Application Scheme ({} points)",
                "tape_scheme_not_needed": "Tape Application Scheme (not needed)",
                "tape_correction_not_needed": "Tape correction not needed",
                "tape_threshold_line": "Minimum deviation for tape: {threshold:.2f} mm",
                "tape_thickness_line": "Tape thickness used: {thickness:.2f} mm",
                "checklist": "Action checklist",
                "instructions_short": "Work through the stages in order. Each panel tells you exactly what to adjust.",
                "instructions_heatmap_hint": "Dark red means the bed is high, dark blue means low. Focus on the brightest zones first.",
                "belt_extra_tip": "Tip: release the synchronising belt clamp before turning the shaft, then tighten it again.",
                "screw_legend": "• Clockwise - LOWERS the corner\n• Counterclockwise - RAISES the corner\n• 1 turn = 60 min = 360°",
                "before_adjustment": "Before adjustment",
                "after_adjustment": "After adjustment",
                "after_adjustment_belts": "After Z lead screws",
                "after_adjustment_with_tape": "After adjustment (screws + tape)",
                "after_adjustment_with_environment": "After adjustment (screws + tape + temperature)",
                "deviation_before": "Deviation before: {value:.3f} mm",
                "deviation_after_screws": "After screws: {value:.3f} mm",
                "deviation_after_tape": "After tape: {value:.3f} mm",
                "deviation_after_belts": "After Z lead screws: {value:.3f} mm",
                "deviation_after_temperature": "After temperature: {value:.3f} mm",
                "screw_turns": "Turns: {value:.2f}",
                "tape_layers_card": "Layers: {value}",
                "temperature_no_adjustments": "No thermal deformation detected",
                "screw_animation_hint": "Watch the animation: it shows which way to turn each screw.",
                "temperature_instructions": "Heat the bed from {measurement:.1f}°C to {target:.1f}°C. PEI expands about {coeff:.1e} per °C, so wait a few minutes for the plate to stabilise.",
                "temperature_expected": "Expected dome change ≈ {delta:.3f} mm across the bed.",
                "temperature_tip": "After heating, run another mesh at printing temperature to confirm the result.",
                "improvement_prediction": "Improvement forecast: {improvement:.3f}mm ({percent:.1f}%)\nBefore: {before:.3f}mm → After: {after:.3f}mm",
                "help_dialog_title": "Stage Help",
                "help_dialog_close": "Close",
                "help": {
                    "initial": "This is the baseline mesh before any corrections.",
                    "belts": "Synchronise the front Z shafts first. Follow the highlighted arrows to raise or lower the corners.",
                    "screws": "Use the adjustment screws for fine tuning. Clockwise lowers the corner, counterclockwise raises it.",
                    "tape": "Apply aluminium tape to the highlighted grid cells. The number indicates how many layers to stack.",
                    "temperature": "Shows how the bed may warp when heating from measurement temperature to target temperature."
                }
            },
            "about": {
                "title": "About",
                "version": "Version 1.0",
                "description": "Application for analysis and calibration\nof 3D printer bed\n\n• Bed level analysis\n• Calibration recommendations\n• Input shaper analysis",
                "ok": "OK"
            },
            "corners": {
                "front_left": "front left",
                "front_right": "front right",
                "back_left": "back left",
                "back_right": "back right"
            },
            "visualization": {
                "bed_mesh_title": "Bed Level Map (Max deviation: {:.3f}mm)",
                "3d_map_title": "3D Bed Map (Max deviation: {:.3f}mm)",
                "height_mm": "Height (mm)",
                "2d_map_title": "2D Bed Level Map",
                "3d_map_window_title": "3D Bed Level Map",
                "before_mm": "Before (mm)",
                "after_mm": "After (mm)"
            },
            "Close": "Close",
            "Drag and drop is not available on this platform. Use 'Load Configuration'.": "Drag and drop is not available on this platform. Use 'Load Configuration'.",
            "Drop format not supported": "Dropped file format is not supported.",
            "Instructions": "Instructions",
            "View": "View",
            "Error": "Error",
            "Warning": "Warning",
            "No shaper files downloaded": "No shaper files were downloaded.",
            "shaper_graphs": {
                "frequency_hz": "Frequency (Hz)",
                "power_spectral_density": "Power Spectral Density",
                "vibration_reduction": "Vibration Reduction (ratio)"
            }
        }
        
        ru_strings = {


            "Language Changed": "Язык изменен",
            "The language has been changed. Please restart the application for the changes to take full effect.": "Язык был изменен. Пожалуйста, перезапустите приложение для полного применения изменений.",
            "Failed to change language.": "Не удалось изменить язык.",
            "app_title": "Flashforge Calibration Assistant",
            "menu": {
                "file": "Файл",
                "open_config": "Открыть конфиг",
                "exit": "Выход",
                "view": "Вид",
                "light_theme": "Светлая тема",
                "dark_theme": "Тёмная тема",
                "tools": "Инструменты",
                "visual_recommendations": "Визуальные рекомендации",
                "ssh_settings": "Настройки SSH",
                "help": "Справка",
                "about": "О программе",
                "language": "Язык"
            },
            "status": {
                "ready": "Готов к работе",
                "loading": "Загрузка файла: {}",
                "success": "Файл успешно загружен",
                "error": "Ошибка при загрузке файла",
                "exit": "Получено прерывание Ctrl+C. Закрываю приложение..."
            },
            "tabs": {
                "bed_leveling": "Выравнивание стола",
                "input_shaper": "Input Shaper",
                "settings": "Настройки"
            },
            "bed_tab": {
                "load_config": "Загрузить конфигурацию",
                "map_2d": "2D карта",
                "map_3d": "3D карта",
                "visual_recommendations": "Визуальные рекомендации",
                "visualization": "Визуализация",
                "info_recommendations": "Информация и рекомендации",
                "warning_load_first": "Сначала загрузите данные",
                "instructions": "ВАЖНО:\n• ПЕРЕДНЯЯ сторона стола - ближе к вам\n• ЗАДНЯЯ сторона - дальше от вас\n\n1. Загрузите файл printer.cfg\n2. Используйте визуализацию для анализа стола\n3. Следуйте рекомендациям по регулировке",
                "initial_recommendations": "Здесь будут отображены рекомендации\nпо выравниванию стола после загрузки\nфайла конфигурации.\n\nДля начала нажмите кнопку\n'Загрузить конфигурацию'.",
                "status_label": "СТАТУС:",
                "status_level": "✅ Стол выровнен",
                "status_needs_adjustment": "❌ Требуется регулировка винтами",
                "status_needs_belt": "❗ Требуется синхронизация Z-валов",
                "status_needs_tape": "⚠️ Требуется коррекция скотчем",
                "current_max_deviation": "Текущее макс. отклонение: {:.3f}мм",
                "average_height": "Средняя высота: {:.3f}мм",
                "action_plan": "Рекомендуемый план действий:",
                "action_belts": "1. Синхронизируйте Z-валы (снизьте дельту ниже {:.3f}мм)",
                "action_screws": "2. Регулировка винтами (цель {:.3f}мм)",
                "action_tape": "3. Наклейка скотча (цель {:.3f}мм)",
                "action_tape_only": "1. Наклейка скотча (цель {:.3f}мм)",
                "action_none": "Корректировка не требуется",
                "corner_deviations": "Отклонения по углам:",
                "visual_recommendations_details": "Используйте визуальные рекомендации для подробностей",
                "belt_header": "Этап 1: Синхронизация Z-валов",
                "belt_instruction": "{corner}: {action} на {teeth} {teeth_label} (~{delta:.2f} мм). Крутить {direction}.",
                "belt_direction_up": "против часовой стрелки (поднимает угол)",
                "belt_direction_down": "по часовой стрелке (опускает угол)",
                "belt_action_tighten": "натянуть",
                "belt_action_loosen": "ослабить",
                "belt_no_adjustments": "Регулировка Z-валов не требуется.",
                "belts_disabled": "Этап Z-валов отключён в настройках.",
                "screw_header": "Этап 2: Регулировка винтов",
                "screw_instruction": "{corner}: поверните {direction} на {minutes} мин ({degrees:.0f}°). Действие: {action}.",
                "screw_action_raise": "поднять угол",
                "screw_action_lower": "опустить угол",
                "screw_no_adjustments": "Регулировка винтов не требуется.",
                "screws_disabled": "Этап винтов отключён в настройках.",
                "tape_header": "Этап 3: Наклейка скотча",
                "tape_instruction": "{position}: {layers} слой(я/ев) (~{thickness:.2f} мм)",
                "tape_no_adjustments": "Отклонения в норме — скотч не нужен.",
                "tape_disabled": "Этап скотча отключён в настройках.",
                "belt_teeth_one": "зуб",
                "belt_teeth_few": "зуба",
                "belt_teeth_many": "зубьев",
                "error_during_analysis": "Ошибка при анализе: {}"
            },
            "shaper_tab": {
                    "load_x": "Загрузить данные X",
                    "load_y": "Загрузить данные Y",
                    "what_is_it": "Что это?",
                    "copy_klipper": "Копировать для настроек",
                    "recommended_shapers": "Рекомендуемые типы шейперов",
                    "results_and_settings": "Результаты и настройки",
                    "axis_x": "Ось X:",
                    "axis_y": "Ось Y:",
                    "frequency": "Частота:",
                    "no_data_loaded": "Данные не загружены",
                    "not_analyzed": "Не проанализировано",
                    "data_loaded_x": "Загружены данные для оси X ({} точек)",
                    "data_loaded_y": "Загружены данные для оси Y ({} точек)",
                    "analysis_complete": "Анализ завершен. Рекомендуемые параметры шейперов обновлены.",
                    "copied": "Конфигурация скопирована в буфер обмена.\nВставьте в файл printer.cfg вашего принтера.",
                    "raw_signal_x": "Ось X - Исходный сигнал",
                    "raw_signal_y": "Ось Y - Исходный сигнал",
                    "spectrum_x": "Спектр (X)",
                    "spectrum_y": "Спектр (Y)",
                    "time": "Время (с)",
                    "acceleration": "Ускорение",
                    "frequency_hz": "Частота (Гц)",
                    "power_spectral_density": "Плотность спектра мощности",
                    "vibration_reduction": "Уменьшение вибраций (отношение)",
                    "amplitude": "Амплитуда",
                    "no_data_x": "Данные для оси X не загружены",
                    "no_data_y": "Данные для оси Y не загружены",
                    "help_text": "Input Shaper — это технология, которая помогает уменьшить вибрации 3D-принтера во время печати.\n\nВибрации могут вызывать дефекты на модели, такие как 'звон' (ghosting). Input Shaper анализирует движения принтера и настраивает его так, чтобы эти вибрации были минимальными.\n\nКак это работает?\n1. Вы загружаете данные с акселерометра.\n2. Программа выбирает лучший 'шейпер'.\n3. Вы копируете настройки.\n\nРезультат: более плавная печать и меньше дефектов!",
                    "setup_recommendations": "Рекомендации по настройке:\n\n",
                    "analyzing_x": "Анализ оси X...",
                    "analyzing_y": "Анализ оси Y...",
                    "recommended_for_x": "Рекомендуемый шейпер для X: {} @ {:.1f} Гц",
                    "recommended_for_y": "Рекомендуемый шейпер для Y: {} @ {:.1f} Гц",
                    "select_and_copy": "Выберите шейпер и скопируйте настройки!",
                    "recommended": "Рекомендуется: {}",
                    "input_shaper_title": "Что такое Input Shaper?",
                    "perform_analysis_first": "Сначала выполните анализ!",
                    "select_csv": "Выберите CSV-файл для оси {axis}",
                    "error_loading": "Ошибка загрузки файла:\n{}"
                },
            "settings_tab": {
                "hardware": "Оборудование",
                "thresholds": "Пороги",
                "ssh": "SSH",
                "visualization": "Визуализация",
                "environment": "Температура",
                "workflow": "Этапы калибровки",
                "screw_pitch": "Шаг винта M4 (мм):",
                "min_adjustment": "Мин. регулировка (мм):",
                "max_adjustment": "Макс. регулировка (мм):",
                "tape_thickness": "Толщина скотча (мм):",
                "belt_tooth_mm": "Шаг ремня на зуб (мм):",
                "belt_threshold": "Порог регулировки валов (мм):",
                "screw_threshold": "Порог винтов (мм):",
                "tape_threshold": "Порог скотча (мм):",
                "host": "Хост:",
                "username": "Пользователь:",
                "password": "Пароль:",
                "test_connection": "Проверить подключение",
                "get_printer_cfg": "Получить printer.cfg",
                "get_shapers": "Получить шейперы",
                "interpolation_factor": "Фактор интерполяции:",
                "show_minutes": "Показывать минуты",
                "show_degrees": "Показывать градусы",
                "measurement_temp": "Температура измерения (°C):",
                "target_temp": "Температура печати (°C):",
                "thermal_coeff": "Коэффициент термодеформации (мм/°C):",
                "enable_belt": "Этап 1 — регулировка Z-валов",
                "enable_screws": "Этап 2 — регулировка винтов",
                "enable_tape": "Этап 3 — наклейка скотча",
                "save": "Сохранить",
                "reset": "Сбросить",
                "settings_saved": "Настройки сохранены",
                "numeric_error": "Проверьте правильность ввода числовых значений",
                "fill_ssh": "Заполните все поля SSH",
                "connection_success": "SSH подключение успешно",
                "connection_error": "Ошибка подключения: {}",
                "fill_printer_cfg": "Конфигурация принтера загружена: {}",
                "fill_shapers": "Файлы шейперов загружены:\n{}",
                "no_shapers_found": "На принтере не найдено файлов шейперов.",
                "ssh_connection_desc": "SSH подключение позволяет автоматически загружать файлы конфигурации и данные калибровки прямо с вашего принтера",
                "connection_requirements": "Для подключения требуется:",
                "ip_or_hostname": "IP адрес или имя хоста принтера",
                "username_desc": "Имя пользователя (обычно 'root')",
                "password_desc": "Пароль для доступа",
                "interpolation_factor_desc": "Фактор интерполяции определяет плавность 3D визуализации (выше значение = красивее график, но больше нагрузка)",
                "hardware_info": "• Шаг винта определяет насколько изменится высота при полном обороте\n• Толщина скотча влияет на расчет количества слоев для компенсации\n• Мин./макс. регулировка ограничивает диапазон предлагаемых изменений",
                "thresholds_info": "1. Если отклонение > порога винтов, программа предложит регулировку винтами\n2. Если после регулировки винтами отклонение > порога скотча,\n   программа предложит дополнительную коррекцию скотчем\n3. Если отклонение < порога винтов, но > порога скотча,\n   программа предложит только коррекцию скотчем",
                "visualization_info": "• Фактор интерполяции определяет плавность 3D визуализации\n  (выше значение = красивее график, но больше нагрузка)\n\n• Настройки отображения позволяют выбрать единицы измерения\n  для инструкций по регулировке винтов (минуты и/или градусы)",
                "display_options_error": "Должна быть включена хотя бы одна опция отображения (минуты или градусы).\nОбе опции были включены по умолчанию.",
                "environment_info": "Разница между температурой измерения и печати может выгибать стол.\nИспользуйте коэффициент, чтобы управлять силой и направлением симулированного купола (отрицательное значение инвертирует кривизну)."
            },
            "visual_rec": {
                "title": "Визуальные рекомендации",
                "problem_map": "Карта проблемных зон",
                "screw_scheme": "Схема регулировки винтов",
                "tape_scheme": "Схема наклейки скотча",
                "prediction": "Предсказание изменений",
                "temperature_tab": "Термоэффект",
                "temperature_map_title": "Прогрев {measure:.0f}°C → {target:.0f}°C (коэф. {coeff:.1e})",
                "temperature_delta_label": "Прогиб, мм",
                "temperature_map_hint": "Красные области поднимутся при нагреве, синие просядут. Сравните с замером на горячем столе.",
                "temperature_hot_surface": "После прогрева",
                "high_points": "Высокие точки",
                "low_points": "Низкие точки",
                "clockwise": "по часовой стрелке",
                "counterclockwise": "против часовой стрелки",
                "instructions": "ВАЖНО! Ориентация стола:\n• ПЕРЕДНЯЯ сторона - ближе к вам (где находится панель управления)\n• ЗАДНЯЯ сторона - дальше от вас (задняя часть принтера)\n\n1. Найдите четыре угловых винта на вашем столе (см. схему регулировки винтов).\n2. КРУТИТЬ ВИНТЫ, ДЕРЖАТЬ ГАЙКИ!!! Вращение ПО часовой стрелке ОПУСКАЕТ угол, ПРОТИВ часовой стрелки ПОДНИМАЕТ угол.\n3. После регулировки винтов следуйте схеме наклейки скотча для окончательной коррекции.\n4. После всех корректировок повторите измерение стола для проверки результатов.",
                "hardware_settings_summary": "Параметры оборудования: шаг винта {pitch:.2f} мм • мин. регулировка {min_adjust:.2f} мм • макс. регулировка {max_adjust:.2f} мм • толщина скотча {tape:.2f} мм",
                "drag_hint": "Подсказка: перетаскивайте заголовки вкладок, чтобы менять порядок карточек рекомендаций.",
                "temperature_summary": "Температура: измерение при {measurement:.1f}°C → печать {target:.1f}°C • коэффициент {coeff:.5f} мм/°C",
                "belt_scheme": "Схема регулировки Z-валов",
                "belt_scheme_tab": "Схема валов",
                "belt_stage_title": "Этап 1: Синхронизация Z-валов",
                "belt_stage_description": "Используйте подсказки ниже, чтобы выровнять три винта/ремня перед точной регулировкой винтов и скотча.",
                "belt_action_tighten": "Натянуть",
                "belt_action_loosen": "Ослабить",
                "belt_action_ok": "В норме",
                "belt_rotation_ccw": "Поверните вал против часовой стрелки (поднимет портал)",
                "belt_rotation_cw": "Поверните вал по часовой стрелке (опустит портал)",
                "belt_instruction_overview": "Последовательность:\n1. Отключите принтер\n2. Положите принтер на спину\n3. Ослабьте фиксаторы натяжителя перед поворотом валов",
                "belt_instruction_finish": "После регулировки:\n• Затяните натяжитель\n• Верните принтер в рабочее положение\n• Повторите измерение стола",
                "belt_no_action": "Регулировка Z-валов не требуется.",
                "belt_teeth_count": "Количество зубьев: {count}",
                "front_left": "Передний левый",
                "front_right": "Передний правый",
                "back_left": "Задний левый",
                "back_right": "Задний правый",
                "back_center": "Задний",
                "normal": "Норма",
                "minutes_label": "{value:.1f} мин",
                "degrees_label": "{value:.1f}°",
                "height_delta": "Изменение высоты: {value:+.2f} мм",
                "corner_height": "Текущая {current:.3f} мм → Целевая {target:.3f} мм",
                "spot_height_diff": "Δ {value:.2f} мм",
                "tape_instruction_title": "ИНСТРУКЦИЯ:",
                "tape_instruction_1": "1. Используйте алюминиевый скотч толщиной ~0.06мм",
                "tape_instruction_2": "2. Наклеивайте скотч в указанных местах",
                "tape_instruction_3": "3. Цифра показывает КОЛИЧЕСТВО СЛОЕВ скотча",
                "tape_instruction_4": "4. После наклейки выполните повторное измерение",
                "tape_layers_legend": "КОЛИЧЕСТВО СЛОЕВ",
                "tape_layer_1": "1 слой",
                "tape_layer_2": "2 слоя",
                "tape_layer_3": "3 слоя",
                "tape_scheme_with_points": "Схема наклейки скотча ({} точек)",
                "tape_scheme_not_needed": "Схема наклейки скотча (не требуется)",
                "tape_correction_not_needed": "Коррекция скотчем не требуется",
                "tape_threshold_line": "Минимальное отклонение для скотча: {threshold:.2f} мм",
                "tape_thickness_line": "Используемая толщина скотча: {thickness:.2f} мм",
                "checklist": "Что сделать",
                "instructions_short": "Выполняйте шаги сверху вниз. Каждый этап подсказывает, что именно нужно сделать.",
                "instructions_heatmap_hint": "Ярко-красное — высокая точка, тёмно-синее — низкая. Начните с самых контрастных зон.",
                "belt_extra_tip": "Подсказка: перед поворотом валов ослабьте фиксатор синхронизирующего ремня и затяните его после регулировки.",
                "screw_legend": "• ПО часовой стрелке - ОПУСКАЕТ угол\n• ПРОТИВ часовой - ПОДНИМАЕТ угол\n• 1 оборот = 60 мин = 360°",
                "before_adjustment": "До регулировки",
                "after_adjustment": "После регулировки",
                "after_adjustment_belts": "После регулировки Z-валов",
                "after_adjustment_with_tape": "После регулировки (винты + скотч)",
                "after_adjustment_with_environment": "После регулировки (винты + скотч + температура)",
                "deviation_before": "Отклонение до: {value:.3f} мм",
                "deviation_after_screws": "После винтов: {value:.3f} мм",
                "deviation_after_tape": "После скотча: {value:.3f} мм",
                "deviation_after_belts": "После Z-валов: {value:.3f} мм",
                "deviation_after_temperature": "После нагрева: {value:.3f} мм",
                "screw_turns": "Обороты: {value:.2f}",
                "tape_layers_card": "Слоёв: {value}",
                "temperature_no_adjustments": "Температурная деформация не выявлена",
                "screw_animation_hint": "Анимация показывает направление вращения каждого винта.",
                "temperature_instructions": "Прогрейте стол с {measurement:.1f}°C до {target:.1f}°C. PEI расширяется примерно на {coeff:.1e} за градус — дайте пластине стабилизироваться перед замером.",
                "temperature_expected": "Ожидаемая выпуклость ≈ {delta:.3f} мм по диагонали стола.",
                "temperature_tip": "После прогрева ещё раз снимите сетку при рабочей температуре и сравните изменения.",
                "improvement_prediction": "Прогноз улучшения: {improvement:.3f}мм ({percent:.1f}%)\nДо: {before:.3f}мм → После: {after:.3f}мм",
                "help_dialog_title": "Справка по этапу",
                "help_dialog_close": "Закрыть",
                "help": {
                    "initial": "Это исходные измерения стола до любых коррекций.",
                    "belts": "Сначала синхронизируйте передние Z-валы. Следуйте стрелкам, чтобы понять куда поднимать или опускать угол.",
                    "screws": "Выполняйте точную регулировку винтами. По часовой стрелке — опускаем, против — поднимаем.",
                    "tape": "Наклейте алюминиевый скотч в подсвеченных ячейках. Число показывает количество слоев.",
                    "temperature": "Показывает, как стол изгибается при переходе от температуры измерения к рабочей температуре."
                }
            },
            "about": {
                "title": "О программе",
                "version": "Версия 1.0",
                "description": "Программа для анализа и калибровки\nстола 3D принтера\n\n• Анализ уровня стола\n• Рекомендации по калибровке\n• Анализ input shaper",
                "ok": "OK"
            },
            "corners": {
                "front_left": "передний левый",
                "front_right": "передний правый",
                "back_left": "задний левый",
                "back_right": "задний правый"
            },
            "visualization": {
                "bed_mesh_title": "Карта уровня стола (Макс. отклонение: {:.3f}мм)",
                "3d_map_title": "3D карта стола (Макс. отклонение: {:.3f}мм)",
                "height_mm": "Высота (мм)",
                "2d_map_title": "2D карта уровня стола",
                "3d_map_window_title": "3D карта уровня стола",
                "before_mm": "До (мм)",
                "after_mm": "После (мм)"
            },
            "Close": "Закрыть",
            "Drag and drop is not available on this platform. Use 'Load Configuration'.": "Перетаскивание файлов недоступно на этой платформе. Используйте кнопку 'Загрузить конфигурацию'.",
            "Drop format not supported": "Формат перетаскиваемого файла не поддерживается.",
            "Instructions": "Инструкции",
            "View": "Вид",
            "Error": "Ошибка",
            "Warning": "Предупреждение",
            "No shaper files downloaded": "Файлы шейперов не были загружены.",
            "shaper_graphs": {
                "frequency_hz": "Частота (Гц)",
                "power_spectral_density": "Плотность спектра мощности",
                "vibration_reduction": "Уменьшение вибраций (отношение)"
            }
        }
        
        with open(os.path.join(languages_dir, 'en.json'), 'w', encoding='utf-8') as f:
            json.dump(en_strings, f, ensure_ascii=False, indent=4)
            
        with open(os.path.join(languages_dir, 'ru.json'), 'w', encoding='utf-8') as f:
            json.dump(ru_strings, f, ensure_ascii=False, indent=4)
    
    def set_language(self, language_code):
        if language_code in self.languages:
            self.current_language = language_code
            return True
        return False
    
    def get_text(self, key, default=None):
        keys = key.split('.')
        value = self.languages.get(self.current_language, {})
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                if self.current_language != self.default_language:
                    value = self.languages.get(self.default_language, {})
                    for k_default in keys:
                        if isinstance(value, dict) and k_default in value:
                            value = value[k_default]
                        else:
                            return default or key
                else:
                    return default or key
        
        return value
    
    def get_available_languages(self):
        language_names = {
            'ru': 'Русский',
            'en': 'English'
        }
        
        result = []
        for code in self.languages.keys():
            if code in language_names:
                result.append((code, language_names[code]))
            else:
                result.append((code, code.upper()))
        
        return result

if __name__ == "__main__":
    manager = LanguageManager()
    print(manager.get_text("app_title"))
    print(manager.get_text("menu.file"))
    print(manager.get_available_languages())

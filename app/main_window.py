#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное окно приложения Flashforge Calibration Assistant
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sv_ttk
import numpy as np
import json
import os
import sys
from urllib.parse import urlparse, unquote
from functools import partial
from typing import Optional

from calibration.hardware.bed import Bed, BedConfig
from calibration.hardware.screw import ScrewConfig
from calibration.algorithms.deviation_analyzer import DeviationAnalyzer
from calibration.algorithms.screw_solver import ScrewSolver
from calibration.algorithms.tape_calculator import TapeCalculator
from data_processing.measurement_parser import KlipperMeshParser

from app.ui.bed_tab import BedLevelingTab
from app.ui.shaper_tab import ShaperTab
from app.ui.settings_tab import SettingsTab
from app.ui.visual_recommendations import VisualRecommendationsWindow
from app.ui.language import get_language_manager, _
from calibration.workflow import compute_workflow, WorkflowData

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES as TKDND_FILES  # type: ignore
    _DnDBase = TkinterDnD.Tk  # type: ignore[attr-defined]
    _DND_FILES_CONST = TKDND_FILES
    _HAS_TKINTERDND2 = True
except Exception:  # noqa: BLE001
    _DnDBase = tk.Tk
    _DND_FILES_CONST = 'DND_Files'
    _HAS_TKINTERDND2 = False

class MainWindow:
    def __init__(self):
        # Инициализация главного окна
        self.root = _DnDBase()
        self.root.title("Flashforge Calibration Assistant")
        self.root.geometry("1200x800")
        self.root.minsize(1024, 768)
        self.dnd_support = None
        
        # Загрузка настроек приложения
        self.app_settings = self.load_app_settings()
        
        # Применение темы
        self.apply_theme(self.app_settings.get('theme', 'light'))
        
        # Установка языка
        language_manager = get_language_manager()
        language_manager.set_language(self.app_settings.get('language', 'en'))
        
        # Настройка стилей UI
        self.setup_styles()
        
        # Инициализация объектов для работы с данными
        self.parser = KlipperMeshParser()
        self.bed = None
        self.analyzer = None
        self.screw_solver = None
        self.tape_calculator = None
        self._workflow_cache: Optional[WorkflowData] = None
        
        # Создание UI компонентов
        self.create_status_bar()
        self.create_menu()
        self.create_main_frame()
        self.setup_drag_and_drop()

        # Восстановление последнего открытого файла
        last_file = self.app_settings.get('last_file')
        if last_file and os.path.exists(last_file):
            self.load_config(filepath=last_file)
    
    def setup_styles(self):
        """Настройка стилей для UI элементов"""
        style = ttk.Style()
        
        # Настраиваем стили кнопок и меток
        style.configure('Action.TButton', font=('Segoe UI', 10, 'bold'), padding=10)
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'), padding=5)
        style.configure('Info.TLabel', font=('Segoe UI', 10), padding=5)
        style.configure('Status.TLabel', font=('Segoe UI', 9), padding=2)
        
        # Для темного и светлого фона настраиваем различные цвета текста
        is_dark = self.app_settings.get('theme', 'light') == 'dark'
        
        # Настраиваем цвета для текстовых компонентов
        text_bg = '#1e1e1e' if is_dark else '#ffffff'
        text_fg = '#ffffff' if is_dark else '#000000'
        
        # Настраиваем цвета для Text widget
        self.root.option_add('*Text.background', text_bg)
        self.root.option_add('*Text.foreground', text_fg)
    
    def create_menu(self):
        """Создание главного меню приложения"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu.file"), menu=file_menu)
        file_menu.add_command(label=_("menu.open_config"), command=self.load_config, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label=_("menu.exit"), command=self.root.quit, accelerator="Alt+F4")
        
        # Меню Вид
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu.view"), menu=view_menu)
        view_menu.add_command(label=_("menu.light_theme"), command=lambda: self.set_theme("light"))
        view_menu.add_command(label=_("menu.dark_theme"), command=lambda: self.set_theme("dark"))
        
        # Меню Инструменты
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu.tools"), menu=tools_menu)
        tools_menu.add_command(label=_("menu.visual_recommendations"), 
                              command=self.show_visual_recommendations)
        tools_menu.add_command(label=_("menu.ssh_settings"), 
                              command=lambda: self.notebook.select(self.settings_tab))
        
        # Меню Язык
        language_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu.language"), menu=language_menu)
        
        language_manager = get_language_manager()
        for code, name in language_manager.get_available_languages():
            language_menu.add_command(label=name, 
                                     command=lambda c=code: self.set_language(c))
        
        # Меню Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=_("menu.help"), menu=help_menu)
        help_menu.add_command(label=_("menu.about"), command=self.show_about)
        
        # Привязка горячих клавиш
        self.root.bind('<Control-o>', lambda e: self.load_config())
    
    def create_status_bar(self):
        """Создание строки состояния"""
        self.status_bar = ttk.Frame(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(
            self.status_bar,
            text=_("status.ready"),
            relief=tk.SUNKEN,
            padding=(5, 2),
            style='Status.TLabel'
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Добавляем индикатор темы
        theme_indicator = ttk.Label(
            self.status_bar,
            text=_("Dark") if self.app_settings.get('theme') == 'dark' else _("Light"),
            padding=(5, 2),
            style='Status.TLabel'
        )
        theme_indicator.pack(side=tk.RIGHT)
    
    def create_main_frame(self):
        """Создание основного контейнера с вкладками"""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Инициализация вкладок
        self.bed_tab = BedLevelingTab(self.notebook, self)
        self.shaper_tab = ShaperTab(self.notebook, self)
        self.settings_tab = SettingsTab(self.notebook, self)
        
        # Добавление вкладок в ноутбук
        self.notebook.add(self.bed_tab, text=_("tabs.bed_leveling"))
        self.notebook.add(self.shaper_tab, text=_("tabs.input_shaper"))
        self.notebook.add(self.settings_tab, text=_("tabs.settings"))

    def setup_drag_and_drop(self):
        """Регистрация drag-and-drop для загрузки файлов."""
        self.dnd_support = self._detect_drag_and_drop_backend()
        self._register_mac_open_document()

        if self.dnd_support in {'tkinterdnd2', 'tkdnd'}:
            self._register_drop_targets()
        elif self.dnd_support == 'mac':
            # macOS will deliver documents through the OpenDocument hook
            self.status_label.config(text=_("status.ready"))
        else:
            # Если система не поддерживает dnd, выводим подсказку пользователю
            self.status_label.config(
                text=_("Drag and drop is not available on this platform. Use 'Load Configuration'.")
            )

    def _register_drop_targets(self) -> None:
        targets = [self.root, self.main_frame, self.notebook, self.bed_tab, self.shaper_tab]
        on_enter = partial(self._set_cursor, cursor='hand2')
        on_leave = partial(self._set_cursor, cursor='')
        drop_types = [_DND_FILES_CONST, 'CF_HDROP', 'DND_Text', 'text/uri-list']

        for widget in targets:
            if not hasattr(widget, 'drop_target_register') or not hasattr(widget, 'dnd_bind'):
                continue
            for drop_type in drop_types:
                try:
                    widget.drop_target_register(drop_type)
                except tk.TclError:
                    continue
            try:
                widget.dnd_bind('<<Drop>>', self._handle_file_drop)
                widget.dnd_bind('<<DragEnter>>', on_enter)
                widget.dnd_bind('<<DragLeave>>', on_leave)
            except Exception:  # noqa: BLE001
                continue

    def _detect_drag_and_drop_backend(self) -> str | None:
        if _HAS_TKINTERDND2:
            return 'tkinterdnd2'

        try:
            self.root.tk.call('package', 'require', 'tkdnd')
            return 'tkdnd'
        except tk.TclError:
            pass

        if sys.platform == 'darwin':
            return 'mac'
        return None

    def _register_mac_open_document(self) -> None:
        if sys.platform != 'darwin':
            return
        for command in ('::tk::mac::OpenDocument', 'tk::mac::OpenDocument'):
            try:
                self.root.createcommand(command, self._mac_open_document)
                break
            except tk.TclError:
                continue

    @staticmethod
    def _set_cursor(event, cursor=''):
        try:
            event.widget.configure(cursor=cursor)
        except tk.TclError:
            pass

    def _handle_file_drop(self, event):
        file_paths = self._parse_dropped_files(event.data)
        self._process_dropped_paths(file_paths)

    def _mac_open_document(self, *file_paths):
        self._process_dropped_paths(list(file_paths))

    def _parse_dropped_files(self, data: str) -> list[str]:
        if not data:
            return []
        try:
            paths = self.root.tk.splitlist(data)
        except tk.TclError:
            paths = data.split()

        cleaned = []
        for item in paths:
            path = item.strip()
            if path.startswith('{') and path.endswith('}'):
                path = path[1:-1]
            if path.startswith('file://'):
                parsed = urlparse(path)
                # text/uri-list may include host portion; combine with path if present
                combined = parsed.path or ''
                if parsed.netloc and not combined.startswith('/'):
                    combined = f"/{parsed.netloc}{combined or ''}"
                path = unquote(combined)
                if sys.platform.startswith('win'):
                    path = path.lstrip('/')
            path = path.strip()
            cleaned.append(path)
        return cleaned

    def _process_dropped_paths(self, file_paths: list[str]) -> bool:
        handled = False
        for path in file_paths:
            if not path or not os.path.exists(path):
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext in {'.cfg', '.conf'}:
                self.load_config(filepath=path)
                handled = True
            elif ext == '.csv':
                axis = self.shaper_tab.infer_axis_from_filename(path)
                self.shaper_tab.load_data_from_file(path, axis_hint=axis)
                handled = True

        if not handled and file_paths:
            messagebox.showwarning(_("Warning"), _("Drop format not supported"))
        return handled
    
    def load_config(self, filepath=None, event=None):
        """Загрузка файла конфигурации Klipper"""
        if not filepath:
            filepath = filedialog.askopenfilename(
                title=_("Open Configuration"),
                filetypes=[
                    (_("Klipper configs"), "*.cfg"),
                    (_("All files"), "*.*")
                ]
            )
        
        if not filepath:
            return

        try:
            self.status_label.config(text=_("status.loading").format(filepath))
            self.root.update()

            with open(filepath, 'r') as f:
                config_content = f.read()

            settings = self.settings_tab.get_settings()
            mesh_data = self.parser.parse_config_file(config_content)

            if mesh_data:
                # Создаем экземпляр стола
                self.bed = Bed(BedConfig(
                    size_x=220.0,
                    size_y=220.0,
                    mesh_points_x=mesh_data.x_count,
                    mesh_points_y=mesh_data.y_count
                ))
                
                # Устанавливаем данные сетки
                self.bed.set_mesh_data(mesh_data.matrix)
                
                # Создаем модули анализа
                screw_config = ScrewConfig(
                    pitch=settings['hardware']['screw_pitch'],
                    min_adjust=settings['hardware']['min_adjustment'],
                    max_adjust=settings['hardware']['max_adjustment']
                )

                self.analyzer = DeviationAnalyzer(
                    self.bed,
                    screw_threshold=settings['thresholds']['screw_threshold'],
                    tape_threshold=settings['thresholds']['tape_threshold'],
                    screw_config=screw_config
                )
                
                self.screw_solver = ScrewSolver(self.bed, screw_config)
                self.tape_calculator = TapeCalculator(
                    self.bed,
                    tape_thickness=settings['hardware']['tape_thickness'],
                    min_height_diff=settings['thresholds']['tape_threshold']
                )

                # Уведомляем вкладку о загрузке данных
                self.bed_tab.on_config_loaded(config_content)

                # Обновляем строку состояния
                self.status_label.config(text=_("status.success"))

                # Сохраняем путь к последнему открытому файлу
                self.app_settings['last_file'] = filepath
                self.save_app_settings()

                self.invalidate_workflow()

            else:
                raise ValueError(_("Failed to get mesh data"))

        except Exception as e:
            messagebox.showerror(_("Error"), f"{_('status.error')}: {str(e)}")
            self.status_label.config(text=_("status.error"))
    
    def show_visual_recommendations(self):
        """Показать окно визуальных рекомендаций"""
        if not self.bed or not self.analyzer:
            messagebox.showwarning(_("Warning"), _("bed_tab.warning_load_first"))
            return

        settings = self.settings_tab.get_settings()
        screw_config = ScrewConfig(
            pitch=settings['hardware']['screw_pitch'],
            min_adjust=settings['hardware']['min_adjustment'],
            max_adjust=settings['hardware']['max_adjustment']
        )

        self.analyzer.set_screw_config(screw_config)
        self.screw_solver.set_screw_config(screw_config)
        self.tape_calculator.tape_thickness = settings['hardware']['tape_thickness']
        self.tape_calculator.min_height_diff = settings['thresholds']['tape_threshold']

        VisualRecommendationsWindow(
            self,
            self.bed,
            self.analyzer,
            self.screw_solver,
            self.tape_calculator
        )

    def get_workflow_data(self, recompute: bool = False) -> Optional[WorkflowData]:
        if not self.bed or not self.analyzer or not self.screw_solver or not self.tape_calculator:
            return None
        if recompute or self._workflow_cache is None:
            settings = self.settings_tab.get_settings()
            self._workflow_cache = compute_workflow(
                self.bed,
                self.analyzer,
                self.screw_solver,
                self.tape_calculator,
                settings
            )
        return self._workflow_cache

    def invalidate_workflow(self):
        self._workflow_cache = None
    
    def show_about(self):
        """Показать окно 'О программе'"""
        about_window = tk.Toplevel(self.root)
        about_window.title(_("about.title"))
        about_window.geometry("400x300")
        about_window.transient(self.root)
        about_window.grab_set()
        
        # Центрируем окно относительно главного
        about_window.geometry(f"+{self.root.winfo_x() + 50}+{self.root.winfo_y() + 50}")
        
        # Проверяем тему
        is_dark_theme = self.app_settings.get('theme', 'light') == 'dark'
        
        frame = ttk.Frame(about_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(
            frame,
            text="Flashforge Calibration Assistant",
            style='Header.TLabel'
        ).pack(pady=(0, 10))
        
        ttk.Label(
            frame,
            text=_("about.version"),
            style='Info.TLabel'
        ).pack()
        
        description = _("about.description")
        ttk.Label(
            frame,
            text=description,
            style='Info.TLabel',
            justify=tk.CENTER
        ).pack(pady=20)
        
        ttk.Button(
            frame,
            text=_("about.ok"),
            command=about_window.destroy,
            style='Action.TButton'
        ).pack(pady=(20, 0))
    
    def translate_corner(self, corner_name):
        """Перевести название угла"""
        return _("corners." + corner_name)
    
    def set_theme(self, theme_name):
        """Изменить тему оформления приложения"""
        if theme_name in ['light', 'dark']:
            sv_ttk.set_theme(theme_name)
            self.app_settings['theme'] = theme_name
            self.save_app_settings()
            
            # Обновляем стили для текстовых компонентов
            self.setup_styles()
            
            # Обновляем визуализацию
            if self.bed and hasattr(self.bed_tab, 'update_visualization'):
                self.bed_tab.update_visualization()
                
            # Если вкладка шейперов уже инициализирована и у нее есть метод обновления
            if hasattr(self.shaper_tab, 'init_empty_plots'):
                self.shaper_tab.init_empty_plots()
                
            messagebox.showinfo(_("Information"), 
                                _("Theme has been changed. Some elements may update only after restart."))
    
    def apply_theme(self, theme_name):
        """Применить тему оформления"""
        if theme_name in ['light', 'dark']:
            sv_ttk.set_theme(theme_name)
        else:
            sv_ttk.set_theme("light")  # По умолчанию светлая тема
    
    def set_language(self, language_code):
        """Изменить язык интерфейса"""
        language_manager = get_language_manager()
        if language_manager.set_language(language_code):
            self.app_settings['language'] = language_code
            self.save_app_settings()
            messagebox.showinfo(_("Information"), 
                               _("Language changes will be applied after restart."))
    
    def load_app_settings(self):
        """Загрузка общих настроек приложения"""
        settings_path = os.path.join('config', 'app_settings.json')
        
        # Настройки по умолчанию
        default_settings = {
            'theme': 'light',
            'language': 'en',
            'last_file': None
        }
        
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    # Обновляем значения по умолчанию теми, что загружены из файла
                    default_settings.update(settings)
            except:
                pass
                
        return default_settings
        
    def save_app_settings(self):
        """Сохранение общих настроек приложения"""
        settings_path = os.path.join('config', 'app_settings.json')
        
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        
        with open(settings_path, 'w') as f:
            json.dump(self.app_settings, f, indent=4)
    
    def run(self):
        """Запуск главного цикла приложения"""
        self.root.mainloop()

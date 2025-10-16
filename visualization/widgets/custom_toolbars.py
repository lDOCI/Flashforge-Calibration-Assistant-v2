#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Настраиваемые панели инструментов для Matplotlib
"""

from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

class MinimalNavigationToolbar(NavigationToolbar2Tk):
    """Минимальная панель навигации без кнопок"""
    def __init__(self, canvas, window):
        self.toolitems = []  # Пустой список - нет кнопок
        NavigationToolbar2Tk.__init__(self, canvas, window)
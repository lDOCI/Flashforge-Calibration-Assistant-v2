"""
Flashforge Calibration Assistant - PySide6 application package.

This package hosts the redesigned application architecture with clear
separation between core logic, services, and UI layers.
"""

__all__ = [
    "create_app",
]

from .app import create_app  # noqa: E402


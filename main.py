#!/usr/bin/env python3
"""
Flashforge Calibration Assistant (PySide6 edition).

This module boots the redesigned application with improved modularity and UI.
"""

from __future__ import annotations

import logging
import platform
import sys
from importlib.util import find_spec
from pathlib import Path

from flashforge_app import create_app


REQUIRED_PACKAGES = {
    "numpy": "numpy",
    "matplotlib": "matplotlib",
    "scipy": "scipy",
    "paramiko": "paramiko",
    "PySide6": "PySide6",
}

REQUIRED_DIRECTORIES = ("config", "languages")


def check_dependencies() -> bool:
    missing = [pkg for module, pkg in REQUIRED_PACKAGES.items() if find_spec(module) is None]
    if missing:
        print("Не установлены необходимые пакеты:")
        print("  " + " ".join(sorted(missing)))
        print("Установите их командой:")
        print(f"  pip install {' '.join(sorted(missing))}")
        return False
    return True


def prepare_directories() -> None:
    for directory in REQUIRED_DIRECTORIES:
        Path(directory).mkdir(parents=True, exist_ok=True)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(message)s",
    )


def main() -> int:
    print("Запуск Flashforge Calibration Assistant (PySide6)")
    print(f"Python: {sys.version.split()[0]} | OS: {platform.system()} {platform.release()}")

    if not check_dependencies():
        return 1

    configure_logging()
    prepare_directories()

    application = create_app()
    try:
        return application.run()
    except Exception:
        logging.exception("Критическая ошибка приложения")
        return 1


if __name__ == "__main__":
    sys.exit(main())
    

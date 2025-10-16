from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    """
    Centralised theme colors; tweak here to adjust the entire app appearance.
    """

    background: str = "#0F111A"
    surface: str = "#161925"
    surface_alt: str = "#1D2132"
    surface_hover: str = "#22283D"
    border: str = "#2B324A"
    accent_primary: str = "#5C6BF5"
    accent_secondary: str = "#FF6EA1"
    accent_success: str = "#42C29E"
    accent_warning: str = "#F5A45C"
    accent_error: str = "#F55C6B"
    text_primary: str = "#F7F9FF"
    text_secondary: str = "#B5BAD6"
    text_muted: str = "#707897"
    shadow: str = "#000000"
    outline_glow: str = "#5C6BF533"


from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List


SETTINGS_PATH = Path("config") / "app_settings.json"


@dataclass
class VisualizationSettings:
    interpolation_factor: int = 100
    show_minutes: bool = True
    show_degrees: bool = True


@dataclass
class HardwareSettings:
    screw_pitch: float = 0.7
    min_adjustment: float = 0.1
    max_adjustment: float = 2.0
    tape_thickness: float = 0.06
    belt_tooth_mm: float = 0.4
    screw_mode: str = "hold_nut"


@dataclass
class ThresholdSettings:
    belt_threshold: float = 0.6
    screw_threshold: float = 0.4
    tape_threshold: float = 0.2


@dataclass
class EnvironmentSettings:
    measurement_temp: float = 25.0
    target_temp: float = 25.0
    thermal_expansion_coeff: float = 0.0


@dataclass
class ThermalPreset:
    name: str = "ABS 100°C"
    measurement_temp: float = 60.0
    target_temp: float = 100.0
    chamber_factor: float = 0.35  # доля прогрева воздуха от стола
    pei_thickness: float = 0.55
    steel_thickness: float = 1.50
    alpha_pei: float = 5.0e-5
    alpha_steel: float = 1.2e-5
    beta_uniform: float = 0.2  # вклад равномерного расширения


@dataclass
class WorkflowSettings:
    enable_belt: bool = True
    enable_screws: bool = True
    enable_tape: bool = True


@dataclass
class SSHSettings:
    host: str = ""
    username: str = ""
    password: str = ""


@dataclass
class ApplicationSettings:
    theme: str = "light"
    language: str = "en"
    last_file: str | None = None
    hardware: HardwareSettings = field(default_factory=HardwareSettings)
    thresholds: ThresholdSettings = field(default_factory=ThresholdSettings)
    visualization: VisualizationSettings = field(default_factory=VisualizationSettings)
    environment: EnvironmentSettings = field(default_factory=EnvironmentSettings)
    workflow: WorkflowSettings = field(default_factory=WorkflowSettings)
    ssh: SSHSettings = field(default_factory=SSHSettings)
    thermal_presets: List[ThermalPreset] = field(default_factory=lambda: [
        ThermalPreset(name="PLA 50°C", measurement_temp=60.0, target_temp=50.0, chamber_factor=0.25),
        ThermalPreset(name="PETG 70°C", measurement_temp=60.0, target_temp=70.0, chamber_factor=0.3),
        ThermalPreset(name="ABS 100°C", measurement_temp=60.0, target_temp=100.0, chamber_factor=0.4),
    ])
    active_thermal_preset: str | None = "ABS 100°C"

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ApplicationSettings":

        def merge_dataclass(dataclass_type, values):
            base = dataclass_type()
            for key, value in values.items():
                if hasattr(base, key):
                    setattr(base, key, value)
            return base

        instance = cls()
        for key, value in payload.items():
            if key in {"hardware", "thresholds", "visualization", "environment", "workflow", "ssh"}:
                target_type = getattr(instance, key).__class__
                setattr(instance, key, merge_dataclass(target_type, value))
            elif key == "thermal_presets" and isinstance(value, list):
                instance.thermal_presets = [merge_dataclass(ThermalPreset, item) for item in value if isinstance(item, dict)]
            elif hasattr(instance, key):
                setattr(instance, key, value)
        if instance.active_thermal_preset is None and instance.thermal_presets:
            instance.active_thermal_preset = instance.thermal_presets[0].name
        return instance


class SettingsService:
    """
    Provides read/write access to persistent application settings.
    """

    def __init__(self, storage_path: Path = SETTINGS_PATH) -> None:
        self.storage_path = storage_path
        self.settings = ApplicationSettings()

    def load(self) -> ApplicationSettings:
        if self.storage_path.exists():
            try:
                payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
                self.settings = ApplicationSettings.from_dict(payload)
            except json.JSONDecodeError:
                # Corrupted file, keep defaults but do not overwrite immediately.
                pass
        else:
            self.save()
        return self.settings

    def save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(self.settings.to_dict(), indent=2),
            encoding="utf-8",
        )

    def update(self, **kwargs: Any) -> ApplicationSettings:
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        self.save()
        return self.settings

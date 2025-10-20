"""
Application state container that bridges backend logic with UI views.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from calibration.algorithms.deviation_analyzer import DeviationAnalyzer
from calibration.algorithms.screw_solver import ScrewConfig, ScrewSolver
from calibration.algorithms.tape_calculator import TapeCalculator
from calibration.hardware.bed import Bed, BedConfig
from calibration.workflow import WorkflowData, compute_workflow
from data_processing.measurement_parser import KlipperMeshParser, MeshData

from flashforge_app.services.settings import ApplicationSettings, SettingsService


@dataclass
class BedWorkspace:
    mesh: MeshData
    bed: Bed
    analyzer: DeviationAnalyzer
    screw_solver: ScrewSolver
    tape_calculator: TapeCalculator
    workflow: Optional[WorkflowData] = None

    @property
    def mesh_matrix(self) -> np.ndarray:
        return self.bed.mesh_data if self.bed.mesh_data is not None else self.mesh.matrix


class AppState:
    """
    Coordinates persistent services and runtime data used across views.
    """

    def __init__(self, settings_service: SettingsService) -> None:
        self.settings_service = settings_service
        self.parser = KlipperMeshParser()
        self.current_settings: ApplicationSettings = self.settings_service.settings
        self.workspace: Optional[BedWorkspace] = None
        self.last_printer_cfg: Optional[Path] = None

    # ------------------------------------------------------------------ Settings helpers
    def reload_settings(self) -> ApplicationSettings:
        self.current_settings = self.settings_service.load()
        return self.current_settings

    def save_settings(self) -> None:
        self.settings_service.save()
        self.current_settings = self.settings_service.settings

    def update_settings(self, settings: ApplicationSettings) -> None:
        self.settings_service.settings = settings
        self.current_settings = settings
        self.save_settings()
        if self.workspace:
            hw = settings.hardware
            thresholds = settings.thresholds
            screw_config = ScrewConfig(
                pitch=hw.screw_pitch,
                min_adjust=hw.min_adjustment,
                max_adjust=hw.max_adjustment,
            )

            self.workspace.screw_solver.set_screw_config(screw_config)
            self.workspace.analyzer.set_screw_config(screw_config)
            self.workspace.analyzer.screw_threshold = thresholds.screw_threshold
            self.workspace.analyzer.tape_threshold = thresholds.tape_threshold
            self.workspace.tape_calculator.tape_thickness = hw.tape_thickness
            self.workspace.tape_calculator.min_height_diff = thresholds.tape_threshold
            self._compute_workflow()

    # ------------------------------------------------------------------ Bed handling
    def load_printer_config(self, file_path: Path) -> BedWorkspace:
        content = Path(file_path).read_text(encoding="utf-8")
        mesh = self.parser.parse_config_file(content)
        if not mesh:
            raise ValueError("failed_to_parse_mesh")

        bed = Bed(BedConfig(
            size_x=220.0,
            size_y=220.0,
            mesh_points_x=mesh.x_count,
            mesh_points_y=mesh.y_count,
        ))
        bed.set_mesh_data(mesh.matrix)

        hw = self.current_settings.hardware
        thresholds = self.current_settings.thresholds

        screw_config = ScrewConfig(
            pitch=hw.screw_pitch,
            min_adjust=hw.min_adjustment,
            max_adjust=hw.max_adjustment,
        )

        analyzer = DeviationAnalyzer(
            bed,
            screw_threshold=thresholds.screw_threshold,
            tape_threshold=thresholds.tape_threshold,
            screw_config=screw_config,
        )
        screw_solver = ScrewSolver(bed, screw_config)
        tape_calculator = TapeCalculator(
            bed,
            tape_thickness=hw.tape_thickness,
            min_height_diff=thresholds.tape_threshold,
        )

        self.workspace = BedWorkspace(
            mesh=mesh,
            bed=bed,
            analyzer=analyzer,
            screw_solver=screw_solver,
            tape_calculator=tape_calculator,
        )
        self.last_printer_cfg = file_path
        self.current_settings.last_file = str(file_path)
        self.settings_service.save()

        self._compute_workflow()
        return self.workspace

    def _compute_workflow(self) -> Optional[WorkflowData]:
        if not self.workspace:
            return None
        settings_payload = {
            "hardware": {
                "tape_thickness": self.current_settings.hardware.tape_thickness,
                "belt_tooth_mm": self.current_settings.hardware.belt_tooth_mm,
                "screw_pitch": self.current_settings.hardware.screw_pitch,
                "min_adjustment": self.current_settings.hardware.min_adjustment,
                "max_adjustment": self.current_settings.hardware.max_adjustment,
            },
            "thresholds": {
                "belt_threshold": self.current_settings.thresholds.belt_threshold,
                "screw_threshold": self.current_settings.thresholds.screw_threshold,
                "tape_threshold": self.current_settings.thresholds.tape_threshold,
            },
            "visualization": {
                "interpolation_factor": self.current_settings.visualization.interpolation_factor,
            },
            "workflow": {
                "enable_belt": self.current_settings.workflow.enable_belt,
                "enable_screws": self.current_settings.workflow.enable_screws,
                "enable_tape": self.current_settings.workflow.enable_tape,
            },
            "environment": {
                "measurement_temp": self.current_settings.environment.measurement_temp,
                "target_temp": self.current_settings.environment.target_temp,
                "thermal_expansion_coeff": self.current_settings.environment.thermal_expansion_coeff,
            },
        }
        presets = self.current_settings.thermal_presets
        active_preset = None
        if presets:
            active_preset = next(
                (preset for preset in presets if preset.name == self.current_settings.active_thermal_preset),
                presets[0],
            )
            settings_payload["thermal_model"] = {
                "name": active_preset.name,
                "measurement_temp": active_preset.measurement_temp,
                "target_temp": active_preset.target_temp,
                "chamber_factor": active_preset.chamber_factor,
                "pei_thickness": active_preset.pei_thickness,
                "steel_thickness": active_preset.steel_thickness,
                "alpha_pei": active_preset.alpha_pei,
                "alpha_steel": active_preset.alpha_steel,
                "beta_uniform": active_preset.beta_uniform,
            }
        self.workspace.workflow = compute_workflow(
            self.workspace.bed,
            self.workspace.analyzer,
            self.workspace.screw_solver,
            self.workspace.tape_calculator,
            settings_payload,
        )
        # Attach active thermal preset for UI consumers
        if self.workspace.workflow:
            setattr(self.workspace.workflow, "active_thermal_model", settings_payload.get("thermal_model"))
        return self.workspace.workflow

    def recompute_workflow(self) -> Optional[WorkflowData]:
        return self._compute_workflow()

"""High level orchestration for calibration workflow computations."""

from __future__ import annotations

from typing import Dict

from calibration.algorithms.deviation_analyzer import DeviationAnalyzer
from calibration.algorithms.screw_solver import ScrewSolver
from calibration.algorithms.tape_calculator import TapeCalculator
from calibration.hardware.bed import Bed

from .calculators import (
    build_belt_stage,
    build_screw_stage,
    build_tape_stage,
    build_temperature_stage,
    compute_initial_stage,
)
from .models import StageResult, WorkflowData

DEFAULT_WORKFLOW_FLAGS: Dict[str, bool] = {
    'enable_belt': True,
    'enable_screws': True,
    'enable_tape': True,
}


def compute_workflow(
    bed: Bed,
    analyzer: DeviationAnalyzer,
    screw_solver: ScrewSolver,
    tape_calculator: TapeCalculator,
    settings: Dict,
) -> WorkflowData:
    """Compose stage-by-stage calibration results for UI consumption."""
    workflow_flags = {
        **DEFAULT_WORKFLOW_FLAGS,
        **settings.get('workflow', {}),
    }
    env_settings = settings.get('environment', {})

    stages: list[StageResult] = []
    mesh_state = bed.mesh_data.copy()

    initial_stage = compute_initial_stage(mesh_state)
    stages.append(initial_stage)

    belt_stage, mesh_state = build_belt_stage(
        bed,
        screw_solver,
        settings,
        mesh_state,
        workflow_flags.get('enable_belt', True),
    )
    stages.append(belt_stage)

    screw_stage, mesh_state = build_screw_stage(
        analyzer,
        screw_solver,
        mesh_state,
        workflow_flags.get('enable_screws', True),
    )
    stages.append(screw_stage)

    tape_stage, mesh_state = build_tape_stage(
        tape_calculator,
        mesh_state,
        settings,
        workflow_flags.get('enable_tape', True),
    )
    stages.append(tape_stage)

    temperature_stage, mesh_state = build_temperature_stage(
        bed,
        mesh_state,
        env_settings,
        enabled_flag=True,
        thermal_model=settings.get('thermal_model'),
    )
    stages.append(temperature_stage)

    enabled_stages = [stage for stage in stages if stage.enabled]
    best_stage = (
        min(enabled_stages, key=lambda stage: stage.deviation)
        if enabled_stages else stages[0]
    )

    return WorkflowData(
        stages=stages,
        best_stage=best_stage,
        active_thermal_model=settings.get('thermal_model'),
    )

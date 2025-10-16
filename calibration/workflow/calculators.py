"""Stage calculators that encapsulate calibration logic."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from calibration.algorithms.deviation_analyzer import DeviationAnalyzer
from calibration.algorithms.screw_solver import ScrewAdjustment, ScrewSolver
from calibration.algorithms.tape_calculator import TapeCalculator, TapeSpot
from calibration.hardware.bed import Bed

from .models import StageAction, StageResult

# Tunable gains for front vs rear Z-shafts. Front shafts receive stronger response
# while the rear shaft behaves as a supporting reference.
FRONT_SHAFT_GAIN = 1.6
BACK_SHAFT_GAIN = 0.4


def compute_stage_deviation(mesh: np.ndarray) -> float:
    """Return the maximum absolute deviation from the mean height."""
    mean = float(np.mean(mesh))
    return float(np.max(np.abs(mesh - mean)))


def compute_initial_stage(mesh: np.ndarray) -> StageResult:
    """Assemble the initial stage before any corrections."""
    deviation = compute_stage_deviation(mesh)
    return StageResult(
        key='initial',
        label='visual_rec.stage_initial',
        description='visual_rec.stage_initial_details',
        enabled=True,
        deviation=deviation,
        baseline=None,
        mesh=mesh.copy(),
        actions=[],
        warnings=[],
        help_key='visual_rec.help.initial',
    )


def _format_corner_name(side: str) -> str:
    mapping = {
        'front_left': 'visual_rec.front_left',
        'front_right': 'visual_rec.front_right',
        'back_left': 'visual_rec.back_left',
        'back_right': 'visual_rec.back_right',
        'back_center': 'visual_rec.back_center',
    }
    return mapping.get(side, side)


def _build_corner_weights(solver: ScrewSolver) -> Dict[str, np.ndarray]:
    """Reuse solver-provided weights or create smooth falloff maps."""
    if getattr(solver, 'corner_weights', None):
        return solver.corner_weights

    rows = solver.bed.config.mesh_points_x
    cols = solver.bed.config.mesh_points_y
    coords = {
        'front_left': (0, 0),
        'front_right': (0, cols - 1),
        'back_left': (rows - 1, 0),
        'back_right': (rows - 1, cols - 1),
    }
    weights = {}
    vertical_bias = np.linspace(1.0, 0.4, rows).reshape(rows, 1)
    horizontal_left = np.linspace(1.0, 0.6, cols)
    horizontal_right = horizontal_left[::-1]
    for key, (x0, y0) in coords.items():
        weight = np.zeros((rows, cols), dtype=float)
        for x in range(rows):
            for y in range(cols):
                dist = np.hypot(x - x0, y - y0)
                falloff = 1.0 / (1.0 + dist)
                if key in ('front_left', 'front_right'):
                    horiz_bias = horizontal_left[y] if key == 'front_left' else horizontal_right[y]
                    weight[x, y] = falloff * vertical_bias[x, 0] * horiz_bias
                else:
                    weight[x, y] = falloff * 0.7  # rear remains more neutral
        max_val = float(weight.max())
        if max_val:
            weight /= max_val
        weights[key] = weight
    solver.corner_weights = weights
    return weights


def _normalise_mesh_load(base_mesh: np.ndarray, adjusted_mesh: np.ndarray) -> np.ndarray:
    offset = float(np.mean(adjusted_mesh - base_mesh))
    if abs(offset) < 1e-9:
        return adjusted_mesh
    return adjusted_mesh - offset


def _calculate_belt_adjustments(
    bed: Bed,
    solver: ScrewSolver,
    threshold: float,
    tooth_mm: float,
) -> Dict[str, StageAction]:
    mesh = bed.mesh_data
    rows, cols = mesh.shape

    left_front = float(mesh[0, 0])
    right_front = float(mesh[0, cols - 1])
    back_center = float(mesh[rows - 1, cols // 2])
    front_avg = (left_front + right_front) / 2.0

    adjustments: Dict[str, StageAction] = {}

    lr_diff = right_front - left_front
    if abs(lr_diff) > threshold:
        teeth = max(1, int(np.ceil(abs(lr_diff) / tooth_mm)))
        delta_mm = teeth * tooth_mm
        target_corner = 'front_left' if lr_diff > 0 else 'front_right'
        direction = 'up'
        sign = 1.0
        adjustments[target_corner] = StageAction(
            kind='belt',
            identifier=target_corner,
            label=_format_corner_name(target_corner),
            direction=direction,
            magnitude_mm=delta_mm,
            teeth=teeth,
            metadata={
                'sign': sign,
                'gain': FRONT_SHAFT_GAIN,
                'raw_difference': lr_diff,
                'load_bias': 'front',
            },
        )

    back_diff = back_center - front_avg
    if abs(back_diff) > threshold:
        teeth = max(1, int(np.ceil(abs(back_diff) / tooth_mm)))
        delta_mm = teeth * tooth_mm
        direction = 'up' if back_diff < 0 else 'down'
        sign = 1.0 if direction == 'up' else -1.0
        adjustments['back'] = StageAction(
            kind='belt',
            identifier='back',
            label=_format_corner_name('back_center'),
            direction=direction,
            magnitude_mm=delta_mm,
            teeth=teeth,
            metadata={
                'sign': sign,
                'gain': BACK_SHAFT_GAIN,
                'raw_difference': back_diff,
                'load_bias': 'support',
            },
        )

    return adjustments


def _apply_belt_adjustments(
    base_mesh: np.ndarray,
    solver: ScrewSolver,
    actions: Dict[str, StageAction],
) -> np.ndarray:
    if not actions:
        return base_mesh.copy()

    weights = _build_corner_weights(solver)
    result = base_mesh.copy()

    def apply_to_corner(delta_mm: float, influence: np.ndarray) -> None:
        nonlocal result
        scaled = influence / influence.max() if influence.max() else influence
        result = result + delta_mm * scaled

    for identifier, action in actions.items():
        if identifier == 'front_left':
            influence = weights.get('front_left')
        elif identifier == 'front_right':
            influence = weights.get('front_right')
        elif identifier == 'back':
            influence = (weights.get('back_left') + weights.get('back_right')) / 2.0
        else:
            continue
        if influence is None:
            continue

        delta = (action.magnitude_mm or 0.0) * action.metadata.get('sign', 1.0)
        delta *= float(action.metadata.get('gain', 1.0))
        apply_to_corner(delta, influence)

    offset_removed = float(np.mean(result - base_mesh))
    balanced = _normalise_mesh_load(base_mesh, result)
    balanced_delta = balanced - base_mesh
    load_range = float(np.max(balanced_delta) - np.min(balanced_delta))
    for action in actions.values():
        action.metadata['removed_offset'] = offset_removed
        action.metadata['load_range'] = load_range
    return balanced


def build_belt_stage(
    bed: Bed,
    solver: ScrewSolver,
    settings: dict,
    mesh_before: np.ndarray,
    enabled_flag: bool,
) -> Tuple[StageResult, np.ndarray]:
    """Compute the belt stage, returning the result and updated mesh."""
    baseline = compute_stage_deviation(mesh_before)

    if not enabled_flag:
        stage = StageResult(
            key='after_belts',
            label='visual_rec.belt_stage_title',
            description='visual_rec.belt_stage_description',
            enabled=False,
            deviation=baseline,
            baseline=baseline,
            mesh=mesh_before.copy(),
            actions=[],
            warnings=['visual_rec.stage_disabled'],
            help_key='visual_rec.help.belts',
        )
        return stage, mesh_before

    belt_threshold = float(
        settings['thresholds'].get('belt_threshold', settings['thresholds']['screw_threshold'])
    )
    tooth_mm = float(settings['hardware'].get('belt_tooth_mm', 0.4))

    actions_dict = _calculate_belt_adjustments(bed, solver, belt_threshold, tooth_mm)
    mesh_after = _apply_belt_adjustments(mesh_before, solver, actions_dict)
    deviation_after = compute_stage_deviation(mesh_after)

    actions = [actions_dict[key] for key in ('front_left', 'front_right', 'back') if key in actions_dict]
    warnings = ['visual_rec.belt_no_adjustments'] if not actions else []

    stage = StageResult(
        key='after_belts',
        label='visual_rec.belt_stage_title',
        description='visual_rec.belt_stage_description',
        enabled=True,
        deviation=deviation_after,
        baseline=baseline,
        mesh=mesh_after.copy(),
        actions=actions,
        warnings=warnings,
        help_key='visual_rec.help.belts',
    )
    return stage, mesh_after


def _build_screw_actions(adjustments: List[ScrewAdjustment]) -> List[StageAction]:
    actions: List[StageAction] = []
    for adj in adjustments:
        actions.append(StageAction(
            kind='screw',
            identifier=adj.corner,
            label=_format_corner_name(adj.corner),
            direction='counterclockwise' if adj.direction.name == 'COUNTERCLOCKWISE' else 'clockwise',
            minutes=adj.minutes,
            degrees=adj.degrees,
            magnitude_mm=abs(adj.current_height - adj.target_height),
            metadata={'turns': adj.turns},
        ))
    return actions


def build_screw_stage(
    analyzer: DeviationAnalyzer,
    solver: ScrewSolver,
    base_mesh: np.ndarray,
    enabled_flag: bool,
) -> Tuple[StageResult, np.ndarray]:
    baseline = compute_stage_deviation(base_mesh)

    if not enabled_flag:
        stage = StageResult(
            key='after_screws',
            label='visual_rec.screw_header',
            description='visual_rec.stage_screw_details',
            enabled=False,
            deviation=baseline,
            baseline=baseline,
            mesh=base_mesh.copy(),
            actions=[],
            warnings=['visual_rec.stage_disabled'],
            help_key='visual_rec.help.screws',
        )
        return stage, base_mesh

    adjustments = solver.calculate_adjustments(analyzer.get_ideal_plane())
    if adjustments:
        mesh_after = solver.simulate_sequence(adjustments, base_mesh=base_mesh)
    else:
        mesh_after = base_mesh.copy()

    deviation_after = compute_stage_deviation(mesh_after)
    actions = _build_screw_actions(adjustments)
    warnings = ['visual_rec.screw_no_adjustments'] if not actions else []

    stage = StageResult(
        key='after_screws',
        label='visual_rec.screw_header',
        description='visual_rec.stage_screw_details',
        enabled=True,
        deviation=deviation_after,
        baseline=baseline,
        mesh=mesh_after.copy(),
        actions=actions,
        warnings=warnings,
        help_key='visual_rec.help.screws',
    )
    return stage, mesh_after


def _build_tape_actions(spots: List[TapeSpot], tape_thickness: float) -> List[StageAction]:
    actions: List[StageAction] = []
    for spot in spots:
        position = f"{spot.x + 1}{chr(65 + spot.y)}"
        actions.append(StageAction(
            kind='tape',
            identifier=position,
            label=position,
            magnitude_mm=spot.height_diff,
            metadata={'layers': spot.layers, 'thickness': spot.layers * tape_thickness},
        ))
    return actions


def build_tape_stage(
    tape_calculator: TapeCalculator,
    base_mesh: np.ndarray,
    settings: dict,
    enabled_flag: bool,
) -> Tuple[StageResult, np.ndarray]:
    baseline = compute_stage_deviation(base_mesh)

    if not enabled_flag:
        stage = StageResult(
            key='after_tape',
            label='visual_rec.tape_header',
            description='visual_rec.stage_tape_details',
            enabled=False,
            deviation=baseline,
            baseline=baseline,
            mesh=base_mesh.copy(),
            actions=[],
            warnings=['visual_rec.stage_disabled'],
            help_key='visual_rec.help.tape',
        )
        return stage, base_mesh

    spots = tape_calculator.optimize_tape_layout(
        tape_calculator.find_low_spots(base_mesh)
    )
    mesh_after = tape_calculator.apply_spots(base_mesh, spots) if spots else base_mesh.copy()

    deviation_after = compute_stage_deviation(mesh_after)
    actions = _build_tape_actions(spots, settings['hardware']['tape_thickness'])
    warnings = ['visual_rec.tape_no_adjustments'] if not actions else []

    stage = StageResult(
        key='after_tape',
        label='visual_rec.tape_header',
        description='visual_rec.stage_tape_details',
        enabled=True,
        deviation=deviation_after,
        baseline=baseline,
        mesh=mesh_after.copy(),
        actions=actions,
        warnings=warnings,
        help_key='visual_rec.help.tape',
    )
    return stage, mesh_after


def _apply_temperature_effect(
    bed: Bed,
    mesh: np.ndarray,
    env_settings: Optional[Dict],
    thermal_model: Optional[Dict],
) -> Tuple[np.ndarray, Dict[str, float]]:
    env_settings = env_settings or {}
    thermal_model = thermal_model or {}

    measurement_temp = float(thermal_model.get('measurement_temp', env_settings.get('measurement_temp', 25.0)))
    target_temp = float(thermal_model.get('target_temp', env_settings.get('target_temp', measurement_temp)))

    info: Dict[str, float] = {
        'measurement_temp': measurement_temp,
        'target_temp': target_temp,
    }

    if abs(target_temp - measurement_temp) < 1e-3 and not thermal_model:
        return mesh.copy(), info

    chamber_factor = float(thermal_model.get('chamber_factor', 0.0))
    pei_thickness = float(thermal_model.get('pei_thickness', 0.55))
    steel_thickness = float(thermal_model.get('steel_thickness', 1.50))
    alpha_pei = float(thermal_model.get('alpha_pei', env_settings.get('thermal_expansion_coeff', 0.0)))
    alpha_steel = float(thermal_model.get('alpha_steel', env_settings.get('thermal_expansion_coeff', 0.0)))
    beta_uniform = float(thermal_model.get('beta_uniform', 0.2))

    total_top_delta = target_temp - measurement_temp
    chamber_temp = measurement_temp + chamber_factor * total_top_delta

    delta_through = target_temp - chamber_temp
    delta_uniform = chamber_temp - measurement_temp

    info.update({
        'chamber_factor': chamber_factor,
        'pei_thickness': pei_thickness,
        'steel_thickness': steel_thickness,
        'alpha_pei': alpha_pei,
        'alpha_steel': alpha_steel,
        'beta_uniform': beta_uniform,
        'delta_through': delta_through,
        'delta_uniform': delta_uniform,
        'chamber_temp': chamber_temp,
    })

    if 'name' in thermal_model:
        info['name'] = thermal_model['name']

    if abs(delta_through) < 1e-6 and abs(delta_uniform) < 1e-6 and not thermal_model:
        info['kappa_bimetal'] = 0.0
        info['kappa_uniform'] = 0.0
        info['kappa_total'] = 0.0
        info['warp_max'] = 0.0
        info['warp_min'] = 0.0
        info['warp_range'] = 0.0
        return mesh.copy(), info

    x_step, y_step = bed.get_mm_per_point()
    rows, cols = mesh.shape
    x_coords = (np.arange(rows) * x_step).reshape(rows, 1)
    y_coords = (np.arange(cols) * y_step).reshape(1, cols)

    center_x = bed.config.size_x / 2
    center_y = bed.config.size_y / 2

    X = x_coords - center_x
    Y = y_coords - center_y
    radius_sq = X ** 2 + Y ** 2

    info.update({
        'x_step': x_step,
        'y_step': y_step,
        'bed_size_x': bed.config.size_x,
        'bed_size_y': bed.config.size_y,
    })
    warp = np.zeros_like(mesh, dtype=float)
    kappa_bimetal = 0.0
    kappa_uniform = 0.0
    kappa_fallback = 0.0

    total_thickness = max(pei_thickness + steel_thickness, 1e-6)

    if abs(delta_through) > 1e-6 and pei_thickness > 0 and steel_thickness > 0 and abs(alpha_pei - alpha_steel) > 1e-12:
        rho = pei_thickness / steel_thickness
        n = 3.3e9 / 200e9  # E_pei / E_steel (approx)
        stiffness = 1 + 4 * rho + 6 * rho ** 2 + 4 * rho ** 3 + rho ** 4
        coupling = 1 + (n * rho ** 2 * (1 + rho) ** 2) / max(stiffness, 1e-6)
        numerator = 6 * (alpha_pei - alpha_steel) * delta_through
        denom = steel_thickness * (1 + rho) ** 2 * max(stiffness, 1e-6)
        kappa_bimetal = (numerator / denom) / coupling
        warp += 0.5 * kappa_bimetal * radius_sq

    if abs(delta_uniform) > 1e-6 and abs(alpha_steel) > 1e-12:
        kappa_uniform = beta_uniform * alpha_steel * delta_uniform / total_thickness
        warp += 0.5 * kappa_uniform * radius_sq

    if not np.any(warp):
        expansion_coeff = float(env_settings.get('thermal_expansion_coeff', 0.0))
        delta_temp = target_temp - measurement_temp
        if abs(delta_temp) < 1e-3 or abs(expansion_coeff) < 1e-9:
            info['kappa_bimetal'] = 0.0
            info['kappa_uniform'] = 0.0
            info['kappa_total'] = 0.0
            info['warp_max'] = 0.0
            info['warp_min'] = 0.0
            info['warp_range'] = 0.0
            return mesh.copy(), info
        max_radius_sq = float(center_x ** 2 + center_y ** 2)
        if max_radius_sq <= 0:
            info['kappa_bimetal'] = 0.0
            info['kappa_uniform'] = 0.0
            info['kappa_total'] = 0.0
            info['warp_max'] = 0.0
            info['warp_min'] = 0.0
            info['warp_range'] = 0.0
            return mesh.copy(), info
        warp = expansion_coeff * delta_temp * (radius_sq / max_radius_sq)
        kappa_fallback = 2 * expansion_coeff * delta_temp / max_radius_sq

    warp -= np.mean(warp)
    info['kappa_bimetal'] = kappa_bimetal
    info['kappa_uniform'] = kappa_uniform
    info['kappa_total'] = kappa_bimetal + kappa_uniform + kappa_fallback
    info['warp_max'] = float(np.max(warp))
    info['warp_min'] = float(np.min(warp))
    info['warp_range'] = info['warp_max'] - info['warp_min']
    return mesh + warp, info


def build_temperature_stage(
    bed: Bed,
    base_mesh: np.ndarray,
    env_settings: dict,
    enabled_flag: bool,
    thermal_model: Optional[Dict] = None,
) -> Tuple[StageResult, np.ndarray]:
    baseline = compute_stage_deviation(base_mesh)
    mesh_after, info = _apply_temperature_effect(bed, base_mesh, env_settings, thermal_model)
    deviation_after = compute_stage_deviation(mesh_after)

    enabled = bool(enabled_flag and abs(deviation_after - baseline) > 1e-6)
    warnings = ['visual_rec.temperature_no_adjustments'] if not enabled else []

    stage = StageResult(
        key='after_temperature',
        label='visual_rec.stage_temperature',
        description='visual_rec.stage_temperature_details',
        enabled=enabled,
        deviation=deviation_after,
        baseline=baseline,
        mesh=mesh_after.copy(),
        actions=[],
        warnings=warnings,
        help_key='visual_rec.help.temperature',
        metadata=info,
    )
    return stage, mesh_after

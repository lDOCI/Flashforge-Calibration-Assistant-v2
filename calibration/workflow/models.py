"""Data models used by the calibration workflow engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

import numpy as np


@dataclass
class StageAction:
    """Single actionable step for a calibration stage."""

    kind: str  # e.g. 'belt', 'screw', 'tape', 'info'
    identifier: str
    label: str
    direction: Optional[str] = None
    magnitude_mm: Optional[float] = None
    teeth: Optional[int] = None
    minutes: Optional[float] = None
    degrees: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StageResult:
    """Result of one calibration stage."""

    key: str
    label: str
    description: str
    enabled: bool
    deviation: float
    baseline: Optional[float]
    mesh: np.ndarray
    actions: List[StageAction] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    help_key: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowData:
    """Aggregated calibration workflow information."""

    stages: List[StageResult]
    best_stage: StageResult
    active_thermal_model: Optional[Dict[str, float]] = None

"""Compatibility wrapper for legacy imports."""

from __future__ import annotations

from .engine import compute_workflow  # noqa: F401
from .models import StageAction, StageResult, WorkflowData  # noqa: F401

__all__ = ['StageAction', 'StageResult', 'WorkflowData', 'compute_workflow']

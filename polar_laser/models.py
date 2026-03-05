"""Core data models used by import, processing and export pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Tuple

Point = Tuple[float, float]
ThetaWrapMode = Literal["0_360", "neg180_180"]
LaserMode = Literal["M3", "M4"]
LaserOffMode = Literal["S0", "M5"]


@dataclass(slots=True)
class ImportTransform:
    """User-editable transform applied after SVG parsing into XY mm."""

    scale: float = 1.0
    rotate_deg: float = 0.0
    translate_x_mm: float = 0.0
    translate_y_mm: float = 0.0


@dataclass(slots=True)
class MachineProfile:
    """Machine profile for radial/angular limits and runtime validation."""

    r_min_mm: float = 0.0
    r_max_mm: float = 200.0
    theta_units: str = "deg"
    theta_wrap_mode: ThetaWrapMode = "neg180_180"
    strict_limits: bool = True
    r_steps_per_mm: float = 80.0
    theta_steps_per_deg: float = 10.0


@dataclass(slots=True)
class JobSettings:
    """Job settings that influence motion generation and G-code format."""

    feedrate_mm_min: float = 1200.0
    s_min: int = 0
    s_max: int = 1000
    power_percent: float = 60.0
    laser_mode: LaserMode = "M4"
    travel_laser_off_mode: LaserOffMode = "S0"
    travel_threshold_mm: float = 2.0
    passes: int = 1
    max_segment_len_mm: float = 0.3
    curve_flatten_tol_mm: float = 0.1
    theta_wrap_mode: ThetaWrapMode = "neg180_180"
    shortest_path_theta: bool = True
    park_at_zero: bool = False
    optimize_path_order: bool = True

    def laser_power_s(self) -> int:
        """Map percentage power to machine S range."""
        pct = max(0.0, min(100.0, self.power_percent)) / 100.0
        return int(round(self.s_min + pct * (self.s_max - self.s_min)))


@dataclass(slots=True)
class PolylinePath:
    """Polyline representation of a drawable path in XY millimeters."""

    points: List[Point]


@dataclass(slots=True)
class ProcessedJob:
    """Processed motion in both XY and polar space with validation metadata."""

    xy_paths: List[PolylinePath] = field(default_factory=list)
    polar_paths: List[List[Tuple[float, float]]] = field(default_factory=list)
    out_of_range_segments: List[Tuple[int, int]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_length_mm: float = 0.0
    total_segments: int = 0

"""GRBL G-code export helpers for polar toolpaths."""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .geometry import distance
from .models import JobSettings



def _fmt(value: float) -> str:
    """Format numeric value for compact and stable G-code output."""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def export_gcode(polar_paths: Sequence[Sequence[Tuple[float, float]]], job: JobSettings) -> str:
    """Create GRBL-compatible G-code where X=R(mm) and Y=theta(deg)."""
    lines: List[str] = [
        "; Polar Laser Workspace export",
        "G21",
        "G90",
        "G94",
        job.laser_mode,
        "S0",
    ]

    s_power = job.laser_power_s()

    for _pass in range(job.passes):
        for path in polar_paths:
            if len(path) < 2:
                continue

            r0, t0 = path[0]
            lines.append(f"G0 X{_fmt(r0)} Y{_fmt(t0)}")
            lines.append(f"S{s_power}")

            prev = path[0]
            for r, t in path[1:]:
                jump = distance(prev, (r, t))
                if jump > job.travel_threshold_mm:
                    if job.travel_laser_off_mode == "M5":
                        lines.append("M5")
                    else:
                        lines.append("S0")
                    lines.append(f"G0 X{_fmt(r)} Y{_fmt(t)}")
                    lines.append(job.laser_mode)
                    lines.append(f"S{s_power}")
                lines.append(f"G1 X{_fmt(r)} Y{_fmt(t)} F{_fmt(job.feedrate_mm_min)} S{s_power}")
                prev = (r, t)

            lines.append("M5" if job.travel_laser_off_mode == "M5" else "S0")

    lines.append("M5" if job.travel_laser_off_mode == "M5" else "S0")
    if job.park_at_zero:
        lines.append("G0 X0 Y0")

    return "\n".join(lines) + "\n"

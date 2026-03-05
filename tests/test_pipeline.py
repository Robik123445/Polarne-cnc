"""Tests for core polar conversion and validation scenarios."""

from __future__ import annotations

import math

import pytest

from polar_laser.gcode import export_gcode
from polar_laser.models import ImportTransform, JobSettings, MachineProfile, PolylinePath
from polar_laser.pipeline import process_paths


def test_wrap_shortest_path_prevents_large_jump() -> None:
    """Ensure theta unwrap avoids ~360 degree jumps across wrap border."""
    r = 10.0
    p1 = (r * math.cos(math.radians(179)), r * math.sin(math.radians(179)))
    p2 = (r * math.cos(math.radians(-179)), r * math.sin(math.radians(-179)))
    paths = [PolylinePath([p1, p2])]

    job = JobSettings(shortest_path_theta=True, max_segment_len_mm=100)
    machine = MachineProfile(r_min_mm=0, r_max_mm=100, strict_limits=True)
    out = process_paths(paths, ImportTransform(), 0, 0, machine, job)

    t0 = out.polar_paths[0][0][1]
    t1 = out.polar_paths[0][1][1]
    assert abs(t1 - t0) < 10


def test_circle_theta_is_continuous() -> None:
    """Ensure sampled circle with shortest path has no giant angular discontinuity."""
    pts = []
    for a in range(-170, 191, 20):
        pts.append((50 * math.cos(math.radians(a)), 50 * math.sin(math.radians(a))))
    paths = [PolylinePath(pts)]

    out = process_paths(paths, ImportTransform(), 0, 0, MachineProfile(r_max_mm=200), JobSettings(max_segment_len_mm=100))
    thetas = [t for _, t in out.polar_paths[0]]
    diffs = [abs(b - a) for a, b in zip(thetas, thetas[1:])]
    assert max(diffs) < 60


def test_strict_limits_raise_error() -> None:
    """Strict range check should fail when path exceeds R max."""
    paths = [PolylinePath([(0, 0), (500, 0)])]
    with pytest.raises(ValueError):
        process_paths(paths, ImportTransform(), 0, 0, MachineProfile(r_max_mm=100, strict_limits=True), JobSettings())


def test_non_strict_limits_collect_warning() -> None:
    """Non-strict range check should keep job and record warning metadata."""
    paths = [PolylinePath([(0, 0), (500, 0)])]
    out = process_paths(paths, ImportTransform(), 0, 0, MachineProfile(r_max_mm=100, strict_limits=False), JobSettings())
    assert out.warnings
    assert out.out_of_range_segments


def test_default_gcode_export_is_valid() -> None:
    """Basic export should include required header and motion commands."""
    gcode = export_gcode([[(10, 0), (12, 10), (12, 20)]], JobSettings())
    assert "G21" in gcode
    assert "G90" in gcode
    assert "G1 X12 Y20" in gcode


def test_optimize_path_order_changes_sequence() -> None:
    """Nearest-start sorting should place closer next path earlier."""
    paths = [
        PolylinePath([(0, 0), (1, 0)]),
        PolylinePath([(100, 0), (101, 0)]),
        PolylinePath([(2, 0), (3, 0)]),
    ]
    out = process_paths(paths, ImportTransform(), 0, 0, MachineProfile(r_max_mm=1000), JobSettings(max_segment_len_mm=100))
    starts = [p.points[0] for p in out.xy_paths]
    assert starts[1] == (2, 0)


def test_travel_threshold_uses_xy_metric_when_provided() -> None:
    """Travel split should rely on XY mm threshold when XY paths are available."""
    polar = [[(10, 0), (10.1, 100)]]
    xy = [[(0, 0), (0.1, 0)]]
    gcode = export_gcode(polar, JobSettings(travel_threshold_mm=1), xy_paths=xy)
    assert "G0 X10.1 Y100" not in gcode

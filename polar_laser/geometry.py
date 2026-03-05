"""Geometry and kinematics helpers for XY and polar processing."""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

from .models import Point, ThetaWrapMode


def distance(a: Point, b: Point) -> float:
    """Return Euclidean distance between two 2D points."""
    return math.hypot(b[0] - a[0], b[1] - a[1])


def normalize_theta(theta_deg: float, mode: ThetaWrapMode) -> float:
    """Normalize angle to selected wrap mode."""
    if mode == "0_360":
        value = theta_deg % 360.0
        return 0.0 if abs(value - 360.0) < 1e-9 else value
    value = ((theta_deg + 180.0) % 360.0) - 180.0
    return 180.0 if abs(value + 180.0) < 1e-9 else value


def unwrap_theta(prev: float, current_wrapped: float, mode: ThetaWrapMode) -> float:
    """Choose equivalent theta (+/-360*k) nearest to previous point."""
    base = normalize_theta(current_wrapped, mode)
    candidates = [base + 360.0 * k for k in range(-3, 4)]
    return min(candidates, key=lambda c: abs(c - prev))


def transform_point(point: Point, scale: float, rotate_deg: float, tx: float, ty: float) -> Point:
    """Apply import transform chain: scale -> rotate -> translate."""
    x, y = point
    x *= scale
    y *= scale
    rad = math.radians(rotate_deg)
    xr = x * math.cos(rad) - y * math.sin(rad)
    yr = x * math.sin(rad) + y * math.cos(rad)
    return xr + tx, yr + ty


def segmentize_polyline(points: Sequence[Point], max_len: float) -> List[Point]:
    """Split polyline segments to keep every subsegment shorter than max_len."""
    if len(points) < 2:
        return list(points)

    out: List[Point] = [points[0]]
    for a, b in zip(points, points[1:]):
        seg_len = distance(a, b)
        steps = max(1, math.ceil(seg_len / max_len))
        for step in range(1, steps + 1):
            t = step / steps
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def polyline_length(points: Sequence[Point]) -> float:
    """Compute cumulative polyline length."""
    return sum(distance(a, b) for a, b in zip(points, points[1:]))



def bounding_box(points: Sequence[Point]) -> Tuple[float, float, float, float]:
    """Return min_x, max_x, min_y, max_y for provided points."""
    if not points:
        raise ValueError("Cannot build bounding box of empty point list")
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), max(xs), min(ys), max(ys)

def xy_to_polar(points: Iterable[Point], wrap: ThetaWrapMode, shortest_path: bool) -> List[Tuple[float, float]]:
    """Convert XY points to polar points (R mm, theta deg)."""
    polar: List[Tuple[float, float]] = []
    prev_theta = None
    for x, y in points:
        r = math.hypot(x, y)
        theta = math.degrees(math.atan2(y, x))
        wrapped = normalize_theta(theta, wrap)
        if shortest_path and prev_theta is not None:
            wrapped = unwrap_theta(prev_theta, wrapped, wrap)
        prev_theta = wrapped
        polar.append((r, wrapped))
    return polar

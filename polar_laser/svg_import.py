"""SVG parser and flattener to XY polylines in millimeters."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import List

from .models import PolylinePath

LOGGER = logging.getLogger(__name__)


def _sample_svg_path(path, max_chord_mm: float) -> List[tuple[float, float]]:
    """Sample an SVG path into points using max chord length as density control."""
    total = float(path.length(error=1e-3))
    if total <= 0:
        return []

    samples = max(2, math.ceil(total / max_chord_mm) + 1)
    points: List[tuple[float, float]] = []
    for i in range(samples):
        t = i / (samples - 1)
        p = path.point(t)
        points.append((float(p.x), -float(p.y)))
    return points


def _shape_to_polyline(shape, curve_flatten_tol_mm: float) -> List[tuple[float, float]]:
    """Convert any SVG shape into a flattened polyline honoring transforms."""
    from svgelements import Polygon as SvgPolygon, Polyline as SvgPolyline

    # Svgelements keeps transforms in the object matrix; applying abs() resolves it.
    shape = abs(shape)
    if isinstance(shape, SvgPolyline):
        return [(float(p.x), -float(p.y)) for p in shape]
    if isinstance(shape, SvgPolygon):
        pts = [(float(p.x), -float(p.y)) for p in shape]
        if pts and pts[0] != pts[-1]:
            pts.append(pts[0])
        return pts

    path = shape.as_path()
    if path is None:
        return []
    return _sample_svg_path(path, curve_flatten_tol_mm)


def import_svg_polylines(svg_path: str | Path, curve_flatten_tol_mm: float) -> List[PolylinePath]:
    """Load and flatten supported SVG geometries into list of polylines."""
    from svgelements import SVG, Shape

    svg = SVG.parse(str(svg_path))
    paths: List[PolylinePath] = []

    for element in svg.elements():
        if not isinstance(element, Shape):
            continue
        points = _shape_to_polyline(element, curve_flatten_tol_mm)
        if len(points) >= 2:
            paths.append(PolylinePath(points=points))

    LOGGER.info("Imported %s paths from %s", len(paths), svg_path)
    return paths

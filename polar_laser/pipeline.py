"""End-to-end processing from imported XY paths to validated polar paths."""

from __future__ import annotations

from typing import List

from .geometry import polyline_length, segmentize_polyline, sort_paths_nearest, transform_point, xy_to_polar
from .models import ImportTransform, JobSettings, MachineProfile, PolylinePath, ProcessedJob


def process_paths(
    xy_paths: List[PolylinePath],
    transform: ImportTransform,
    pivot_x_mm: float,
    pivot_y_mm: float,
    machine: MachineProfile,
    job: JobSettings,
) -> ProcessedJob:
    """Transform, segment, convert and validate XY paths for polar motion."""
    processed = ProcessedJob()

    transformed_paths: List[List[tuple[float, float]]] = []
    for path in xy_paths:
        transformed = [
            transform_point(p, transform.scale, transform.rotate_deg, transform.translate_x_mm, transform.translate_y_mm)
            for p in path.points
        ]
        pivot_relative = [(x - pivot_x_mm, y - pivot_y_mm) for x, y in transformed]
        segmented = segmentize_polyline(pivot_relative, max(job.max_segment_len_mm, 1e-6))
        if len(segmented) >= 2:
            transformed_paths.append(segmented)

    if job.optimize_path_order:
        transformed_paths = sort_paths_nearest(transformed_paths)

    for path_idx, segmented in enumerate(transformed_paths):
        polar = xy_to_polar(segmented, job.theta_wrap_mode, job.shortest_path_theta)

        processed.xy_paths.append(PolylinePath(segmented))
        processed.polar_paths.append(polar)
        processed.total_length_mm += polyline_length(segmented)
        processed.total_segments += max(0, len(segmented) - 1)

        for seg_idx, (r, _theta) in enumerate(polar):
            if r < machine.r_min_mm or r > machine.r_max_mm:
                processed.out_of_range_segments.append((path_idx, max(seg_idx - 1, 0)))

    if processed.out_of_range_segments:
        msg = f"Detected {len(processed.out_of_range_segments)} out-of-range segment points"
        processed.warnings.append(msg)
        if machine.strict_limits:
            raise ValueError(msg)

    return processed

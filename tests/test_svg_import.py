"""SVG import tests including transform handling."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("svgelements")

from polar_laser.svg_import import import_svg_polylines


def test_svg_transform_applied(tmp_path: Path) -> None:
    """Ensure SVG transform chain in source file is applied during import."""
    svg = """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 100 100\">
    <path d=\"M 0 0 L 10 0\" transform=\"translate(5,0) rotate(90)\" />
    </svg>"""
    fp = tmp_path / "t.svg"
    fp.write_text(svg, encoding="utf-8")

    paths = import_svg_polylines(fp, 0.1)
    assert len(paths) == 1
    pts = paths[0].points
    # Expected roughly vertical after 90deg rotation.
    assert abs(pts[-1][0] - pts[0][0]) < 1e-3

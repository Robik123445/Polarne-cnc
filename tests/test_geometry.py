"""Tests for geometry helpers used by the polar pipeline."""

from __future__ import annotations

import pytest

from polar_laser.geometry import bounding_box


def test_bounding_box_returns_expected_extents() -> None:
    """Bounding box should produce min/max extents in XY."""
    out = bounding_box([(1, 2), (3, -1), (-4, 5)])
    assert out == (-4, 3, -1, 5)


def test_bounding_box_empty_raises() -> None:
    """Empty input must raise a clear error."""
    with pytest.raises(ValueError):
        bounding_box([])

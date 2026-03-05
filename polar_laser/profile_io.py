"""JSON serialization helpers for machine profile."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import MachineProfile


def save_profile(path: str | Path, profile: MachineProfile) -> None:
    """Save machine profile to JSON file."""
    Path(path).write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")


def load_profile(path: str | Path) -> MachineProfile:
    """Load machine profile from JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return MachineProfile(**data)

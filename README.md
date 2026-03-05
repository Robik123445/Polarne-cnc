# Polar Laser Workspace (PySide6)

Desktop app for converting SVG paths into a polar GRBL toolpath where:
- `X = R (mm)`
- `Y = θ (deg)`

## Current status
This is a strong **MVP+** baseline with practical controls for real workshop testing.
It already includes import, preview, kinematic conversion, validation, and export pipeline.

## Features
- SVG import + flatten (`path`, `line`, `polyline`, `polygon`, shapes through path conversion)
- 2D workspace preview with:
  - grid and axes
  - pivot marker
  - `R_max` machine limit circle
  - out-of-range segments highlighted in red
- Import transform controls:
  - scale / rotate / translate
  - **fit imported width to target mm**
- Pivot controls:
  - manual X/Y
  - bbox-center preset
  - **set pivot by click tool**
- Polar conversion pipeline:
  - segmentation by max segment length
  - `XY -> (R, θ)` conversion
  - theta wrap modes (`neg180_180`, `0_360`)
  - shortest-path theta unwrap
  - optimize path order (nearest-next start)
- GRBL laser export:
  - header (`G21`, `G90`, `G94`, `M3/M4`, `S0`)
  - path motions (`G0`, `G1` with `F`, `S`)
  - travel laser-off policy (`S0` or `M5`)
  - multi-pass support
  - optional park
- Machine profile save/load (`JSON`)
- Debug JSON export (XY + polar + summary)
- Runtime logging to `log.txt`

## Install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python main.py
```

## Tests
```bash
pytest -q
```

## What is still missing for "full production CNC suite"
- color/layer mapping -> per-path feed/power/passes
- serial sender + run-state monitor
- full CAM safety options (lead-in/out, corner power strategy, dwell policy)
- richer UI tooling (dedicated rotate/scale gizmos, selection handles)
- project file format (job + machine + import state)

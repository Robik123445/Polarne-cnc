# Polar Laser Workspace (PySide6)

Desktop MVP app for converting SVG paths into a polar GRBL toolpath where:
- `X = R (mm)`
- `Y = θ (deg)`

## Features
- SVG import (`path`, `line`, `polyline`, `polygon`, `rect`, `circle`, `ellipse` via path conversion)
- 2D workspace preview with pivot and machine radius limits
- Import transform controls (scale, rotate, translate)
- Polar conversion with theta wrap and shortest-path unwrapping
- Segment length control and curve flattening tolerance
- Strict or warning-only range checks
- GRBL laser G-code export (M3/M4 + S power + travel policy)
- JSON machine profile save/load
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

## Notes
- Workspace origin `(0, 0)` is always machine pivot.
- Theta shortest-path should stay ON to avoid long 360° spins.
- This is an MVP architecture, structured for extension.

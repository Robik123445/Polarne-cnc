"""Main PySide6 UI for loading SVG, previewing workspace and exporting G-code."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QAction, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .gcode import export_gcode
from .geometry import bounding_box
from .models import ImportTransform, JobSettings, MachineProfile, PolylinePath
from .pipeline import process_paths
from .profile_io import load_profile, save_profile
from .svg_import import import_svg_polylines

LOGGER = logging.getLogger(__name__)


class WorkspaceView(QGraphicsView):
    """2D workspace view with zooming, panning and click-to-pivot support."""

    scene_clicked = Signal(float, float)

    def __init__(self, scene: QGraphicsScene) -> None:
        """Initialize graphics view interaction defaults."""
        super().__init__(scene)
        self.setRenderHints(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

    def wheelEvent(self, event):
        """Zoom in/out around cursor using mouse wheel."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        """Emit scene click coordinates for pivot tool usage."""
        if event.button() == Qt.LeftButton:
            pos = self.mapToScene(event.position().toPoint())
            self.scene_clicked.emit(float(pos.x()), float(pos.y()))
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """Main application window managing import, processing and export workflows."""

    def __init__(self) -> None:
        """Build full desktop UI with controls and workspace scene."""
        super().__init__()
        self.setWindowTitle("Polar Laser Workspace")

        self.machine = MachineProfile()
        self.job = JobSettings()
        self.transform = ImportTransform()
        self.pivot_x = 0.0
        self.pivot_y = 0.0
        self.xy_paths: List[PolylinePath] = []
        self.processed = None

        self.scene = QGraphicsScene(self)
        self.scene.setSceneRect(-300, -300, 600, 600)
        self.view = WorkspaceView(self.scene)
        self.view.scene_clicked.connect(self.on_scene_clicked)

        central = QSplitter(Qt.Horizontal)
        central.addWidget(self.view)
        central.addWidget(self._build_sidebar())
        central.setStretchFactor(0, 5)
        central.setStretchFactor(1, 2)
        self.setCentralWidget(central)

        self._build_menu()
        self._render_scene()

    def _build_menu(self) -> None:
        """Create top menu actions for import/export and profile operations."""
        file_menu = self.menuBar().addMenu("File")

        act_import = QAction("Import SVG", self)
        act_import.triggered.connect(self.import_svg)
        file_menu.addAction(act_import)

        act_export = QAction("Export G-code", self)
        act_export.triggered.connect(self.export_gcode_file)
        file_menu.addAction(act_export)

        act_export_debug = QAction("Export Debug JSON", self)
        act_export_debug.triggered.connect(self.export_debug_json)
        file_menu.addAction(act_export_debug)

        file_menu.addSeparator()

        act_save_prof = QAction("Save Machine Profile", self)
        act_save_prof.triggered.connect(self.save_machine_profile)
        file_menu.addAction(act_save_prof)

        act_load_prof = QAction("Load Machine Profile", self)
        act_load_prof.triggered.connect(self.load_machine_profile)
        file_menu.addAction(act_load_prof)

    def _build_sidebar(self) -> QWidget:
        """Build right panel with job, machine and transform controls."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        form = QFormLayout()
        self.tool_combo = QComboBox(); self.tool_combo.addItems(["Select/Move", "Set Pivot by Click"])
        self.feed_spin = QDoubleSpinBox(); self.feed_spin.setRange(1, 30000); self.feed_spin.setValue(self.job.feedrate_mm_min)
        self.power_spin = QDoubleSpinBox(); self.power_spin.setRange(0, 100); self.power_spin.setValue(self.job.power_percent)
        self.smin_spin = QSpinBox(); self.smin_spin.setRange(0, 100000); self.smin_spin.setValue(self.job.s_min)
        self.smax_spin = QSpinBox(); self.smax_spin.setRange(1, 100000); self.smax_spin.setValue(self.job.s_max)
        self.mode_combo = QComboBox(); self.mode_combo.addItems(["M4", "M3"])
        self.off_combo = QComboBox(); self.off_combo.addItems(["S0", "M5"])
        self.travel_spin = QDoubleSpinBox(); self.travel_spin.setRange(0, 500); self.travel_spin.setValue(self.job.travel_threshold_mm)
        self.seg_spin = QDoubleSpinBox(); self.seg_spin.setRange(0.01, 10); self.seg_spin.setDecimals(3); self.seg_spin.setValue(self.job.max_segment_len_mm)
        self.flat_spin = QDoubleSpinBox(); self.flat_spin.setRange(0.01, 10); self.flat_spin.setDecimals(3); self.flat_spin.setValue(self.job.curve_flatten_tol_mm)
        self.passes_spin = QSpinBox(); self.passes_spin.setRange(1, 20); self.passes_spin.setValue(self.job.passes)
        self.wrap_combo = QComboBox(); self.wrap_combo.addItems(["neg180_180", "0_360"])
        self.shortest_check = QCheckBox("Shortest path theta"); self.shortest_check.setChecked(True)
        self.optimize_order_check = QCheckBox("Optimize path order"); self.optimize_order_check.setChecked(True)
        self.grid_check = QCheckBox("Show grid"); self.grid_check.setChecked(True)
        self.strict_check = QCheckBox("Strict limits"); self.strict_check.setChecked(True)

        self.scale_spin = QDoubleSpinBox(); self.scale_spin.setRange(0.001, 1000); self.scale_spin.setValue(1.0)
        self.rot_spin = QDoubleSpinBox(); self.rot_spin.setRange(-3600, 3600)
        self.tx_spin = QDoubleSpinBox(); self.tx_spin.setRange(-10000, 10000)
        self.ty_spin = QDoubleSpinBox(); self.ty_spin.setRange(-10000, 10000)
        self.target_width_spin = QDoubleSpinBox(); self.target_width_spin.setRange(1, 100000); self.target_width_spin.setValue(100)

        self.pivotx_spin = QDoubleSpinBox(); self.pivotx_spin.setRange(-10000, 10000)
        self.pivoty_spin = QDoubleSpinBox(); self.pivoty_spin.setRange(-10000, 10000)

        self.rmin_spin = QDoubleSpinBox(); self.rmin_spin.setRange(0, 10000); self.rmin_spin.setValue(self.machine.r_min_mm)
        self.rmax_spin = QDoubleSpinBox(); self.rmax_spin.setRange(0, 10000); self.rmax_spin.setValue(self.machine.r_max_mm)

        form.addRow("Tool", self.tool_combo)
        form.addRow("Feed (mm/min)", self.feed_spin)
        form.addRow("Power (%)", self.power_spin)
        form.addRow("S min", self.smin_spin)
        form.addRow("S max", self.smax_spin)
        form.addRow("Laser mode", self.mode_combo)
        form.addRow("Travel laser off", self.off_combo)
        form.addRow("Travel threshold", self.travel_spin)
        form.addRow("Passes", self.passes_spin)
        form.addRow("Max seg len (mm)", self.seg_spin)
        form.addRow("Flatten tol (mm)", self.flat_spin)
        form.addRow("Theta wrap", self.wrap_combo)
        form.addRow("", self.shortest_check)
        form.addRow("", self.optimize_order_check)
        form.addRow("", self.grid_check)
        form.addRow("", self.strict_check)
        form.addRow("Import scale", self.scale_spin)
        form.addRow("Import rotate (deg)", self.rot_spin)
        form.addRow("Import translate X", self.tx_spin)
        form.addRow("Import translate Y", self.ty_spin)
        form.addRow("Target width (mm)", self.target_width_spin)
        form.addRow("Pivot X", self.pivotx_spin)
        form.addRow("Pivot Y", self.pivoty_spin)
        form.addRow("R min", self.rmin_spin)
        form.addRow("R max", self.rmax_spin)

        layout.addLayout(form)

        btn_apply = QPushButton("Apply + Recalculate")
        btn_apply.clicked.connect(self.recalculate)
        layout.addWidget(btn_apply)

        btn_fit_width = QPushButton("Fit imported width to target")
        btn_fit_width.clicked.connect(self.fit_import_width_to_target)
        layout.addWidget(btn_fit_width)

        btn_center = QPushButton("Pivot = bbox center")
        btn_center.clicked.connect(self.set_pivot_to_bbox_center)
        layout.addWidget(btn_center)

        self.info_label = QLabel("No data loaded")
        layout.addWidget(self.info_label)

        self.gcode_preview = QTextEdit()
        self.gcode_preview.setReadOnly(True)
        layout.addWidget(self.gcode_preview)

        layout.addStretch(1)
        return panel

    def on_scene_clicked(self, x: float, y: float) -> None:
        """Handle scene clicks and apply pivot setting tool when active."""
        if self.tool_combo.currentText() != "Set Pivot by Click":
            return
        self.pivotx_spin.setValue(x)
        self.pivoty_spin.setValue(y)
        self.recalculate()

    def _sync_models(self) -> None:
        """Copy values from widgets into internal settings models."""
        self.job.feedrate_mm_min = self.feed_spin.value()
        self.job.power_percent = self.power_spin.value()
        self.job.s_min = self.smin_spin.value()
        self.job.s_max = self.smax_spin.value()
        self.job.laser_mode = self.mode_combo.currentText()
        self.job.travel_laser_off_mode = self.off_combo.currentText()
        self.job.travel_threshold_mm = self.travel_spin.value()
        self.job.passes = self.passes_spin.value()
        self.job.max_segment_len_mm = self.seg_spin.value()
        self.job.curve_flatten_tol_mm = self.flat_spin.value()
        self.job.theta_wrap_mode = self.wrap_combo.currentText()
        self.job.shortest_path_theta = self.shortest_check.isChecked()
        self.job.optimize_path_order = self.optimize_order_check.isChecked()

        self.transform.scale = self.scale_spin.value()
        self.transform.rotate_deg = self.rot_spin.value()
        self.transform.translate_x_mm = self.tx_spin.value()
        self.transform.translate_y_mm = self.ty_spin.value()

        self.pivot_x = self.pivotx_spin.value()
        self.pivot_y = self.pivoty_spin.value()

        self.machine.r_min_mm = self.rmin_spin.value()
        self.machine.r_max_mm = self.rmax_spin.value()
        self.machine.theta_wrap_mode = self.wrap_combo.currentText()
        self.machine.strict_limits = self.strict_check.isChecked()

    def import_svg(self) -> None:
        """Open file chooser and import SVG path data into XY path list."""
        path, _ = QFileDialog.getOpenFileName(self, "Open SVG", "", "SVG files (*.svg)")
        if not path:
            return
        try:
            self._sync_models()
            self.xy_paths = import_svg_polylines(path, self.job.curve_flatten_tol_mm)
            self.recalculate()
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("SVG import failed")
            QMessageBox.critical(self, "Import error", str(exc))

    def fit_import_width_to_target(self) -> None:
        """Auto-set import scale so imported width matches requested mm width."""
        if not self.xy_paths:
            return
        points = [p for path in self.xy_paths for p in path.points]
        min_x, max_x, _min_y, _max_y = bounding_box(points)
        width = max_x - min_x
        if width <= 1e-9:
            return
        self.scale_spin.setValue(self.target_width_spin.value() / width)
        self.recalculate()

    def recalculate(self) -> None:
        """Run processing pipeline and refresh scene + text previews."""
        if not self.xy_paths:
            self._render_scene()
            return

        self._sync_models()
        try:
            self.processed = process_paths(
                self.xy_paths,
                self.transform,
                self.pivot_x,
                self.pivot_y,
                self.machine,
                self.job,
            )
            gcode = export_gcode(self.processed.polar_paths, self.job, [p.points for p in self.processed.xy_paths])
            self.gcode_preview.setPlainText(gcode[:20000])
            est_time_min = self.processed.total_length_mm / max(self.job.feedrate_mm_min, 1e-6)
            self.info_label.setText(
                f"Length: {self.processed.total_length_mm:.1f} mm | Segments: {self.processed.total_segments} | ETA: {est_time_min:.2f} min"
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Validation / process warning", str(exc))
            self.processed = None

        self._render_scene()

    def _render_scene(self) -> None:
        """Render grid, pivot, machine radius and XY geometry overlay in scene."""
        self.scene.clear()

        if self.grid_check.isChecked():
            pen = QPen(Qt.lightGray)
            pen.setWidthF(0)
            for x in range(-1000, 1001, 10):
                self.scene.addLine(x, -1000, x, 1000, pen)
            for y in range(-1000, 1001, 10):
                self.scene.addLine(-1000, y, 1000, y, pen)

        axis_pen = QPen(Qt.darkGray)
        axis_pen.setWidthF(0)
        self.scene.addLine(-1000, 0, 1000, 0, axis_pen)
        self.scene.addLine(0, -1000, 0, 1000, axis_pen)

        pivot_pen = QPen(Qt.blue)
        pivot_pen.setWidthF(0)
        self.scene.addEllipse(self.pivot_x - 2, self.pivot_y - 2, 4, 4, pivot_pen)

        r_pen = QPen(Qt.darkGreen)
        r_pen.setWidthF(0)
        self.scene.addEllipse(
            self.pivot_x - self.machine.r_max_mm,
            self.pivot_y - self.machine.r_max_mm,
            2 * self.machine.r_max_mm,
            2 * self.machine.r_max_mm,
            r_pen,
        )

        paths = self.processed.xy_paths if self.processed else self.xy_paths
        path_pen = QPen(Qt.black)
        path_pen.setWidthF(0)

        for poly in paths:
            if len(poly.points) < 2:
                continue
            qpath = QPainterPath(QPointF(poly.points[0][0] + self.pivot_x, poly.points[0][1] + self.pivot_y))
            for x, y in poly.points[1:]:
                qpath.lineTo(x + self.pivot_x, y + self.pivot_y)
            item = QGraphicsPathItem(qpath)
            item.setPen(path_pen)
            self.scene.addItem(item)

        if self.processed:
            bad_pen = QPen(Qt.red)
            bad_pen.setWidthF(0)
            for path_idx, seg_idx in self.processed.out_of_range_segments:
                pts = self.processed.xy_paths[path_idx].points
                if seg_idx + 1 >= len(pts):
                    continue
                a = pts[seg_idx]
                b = pts[seg_idx + 1]
                self.scene.addLine(
                    a[0] + self.pivot_x,
                    a[1] + self.pivot_y,
                    b[0] + self.pivot_x,
                    b[1] + self.pivot_y,
                    bad_pen,
                )

    def export_gcode_file(self) -> None:
        """Export current processed polar paths to a G-code file."""
        if not self.processed:
            QMessageBox.information(self, "No job", "Load and process SVG before export.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Save G-code", "job.nc", "G-code (*.nc *.gcode *.txt)")
        if not out_path:
            return

        gcode = export_gcode(self.processed.polar_paths, self.job, [p.points for p in self.processed.xy_paths])
        Path(out_path).write_text(gcode, encoding="utf-8")
        QMessageBox.information(self, "Saved", f"G-code saved to {out_path}")

    def export_debug_json(self) -> None:
        """Export debug JSON containing XY and polar points for diagnostics."""
        if not self.processed:
            QMessageBox.information(self, "No job", "Load and process SVG before debug export.")
            return

        out_path, _ = QFileDialog.getSaveFileName(self, "Save debug JSON", "debug_job.json", "JSON (*.json)")
        if not out_path:
            return

        data = {
            "xy_paths": [path.points for path in self.processed.xy_paths],
            "polar_paths": self.processed.polar_paths,
            "warnings": self.processed.warnings,
            "total_length_mm": self.processed.total_length_mm,
            "total_segments": self.processed.total_segments,
        }
        Path(out_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Saved", f"Debug JSON saved to {out_path}")

    def set_pivot_to_bbox_center(self) -> None:
        """Set pivot to center of current imported geometry bounding box."""
        points = [p for path in self.xy_paths for p in path.points]
        if not points:
            return
        min_x, max_x, min_y, max_y = bounding_box(points)
        self.pivotx_spin.setValue((min_x + max_x) / 2.0)
        self.pivoty_spin.setValue((min_y + max_y) / 2.0)
        self.recalculate()

    def save_machine_profile(self) -> None:
        """Persist machine profile settings to JSON."""
        self._sync_models()
        path, _ = QFileDialog.getSaveFileName(self, "Save machine profile", "machine_profile.json", "JSON (*.json)")
        if path:
            save_profile(path, self.machine)

    def load_machine_profile(self) -> None:
        """Load machine profile JSON and update UI controls."""
        path, _ = QFileDialog.getOpenFileName(self, "Load machine profile", "", "JSON (*.json)")
        if not path:
            return
        self.machine = load_profile(path)
        self.rmin_spin.setValue(self.machine.r_min_mm)
        self.rmax_spin.setValue(self.machine.r_max_mm)
        self.wrap_combo.setCurrentText(self.machine.theta_wrap_mode)
        self.strict_check.setChecked(self.machine.strict_limits)
        self.recalculate()

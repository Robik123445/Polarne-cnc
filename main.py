"""Application entry-point for Polar Laser Workspace."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from polar_laser.ui import MainWindow


def configure_logging() -> None:
    """Configure file logging for diagnostics and troubleshooting."""
    logging.basicConfig(
        filename="log.txt",
        filemode="a",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main() -> int:
    """Start Qt event loop and main window."""
    configure_logging()
    logging.info("Starting Polar Laser Workspace")

    app = QApplication(sys.argv)
    app.setApplicationName("Polar Laser Workspace")

    window = MainWindow()
    window.resize(1400, 900)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
